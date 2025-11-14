# LangChain v1.0 Advanced Usage Patterns

**Research Date:** 2025-10-01
**Documentation Version:** v1-alpha
**Status:** Alpha - Content incomplete and subject to change

> **Note:** These patterns are based on LangChain v1-alpha release. For stable production systems, refer to [LangChain Python v0](https://python.langchain.com/docs/introduction/) or [LangChain JavaScript v0](https://js.langchain.com/docs/introduction/) documentation.

---

## Table of Contents

1. [Long-Term Memory](#long-term-memory)
2. [Context Engineering](#context-engineering)
3. [Structured Output](#structured-output)
4. [Model Context Protocol (MCP)](#model-context-protocol-mcp)
5. [Human-in-the-Loop](#human-in-the-loop)
6. [Multi-Agent Systems](#multi-agent-systems)
7. [Retrieval (RAG)](#retrieval-rag)
8. [Middleware](#middleware)

---

## Long-Term Memory

LangChain agents use [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence#memory-store) to enable long-term memory. This requires knowledge of LangGraph.

### Memory Storage Architecture

LangGraph stores long-term memories as JSON documents in a [store](https://docs.langchain.com/oss/python/langgraph/persistence#memory-store). Each memory is organized under:
- **Namespace**: Custom grouping (similar to a folder) - often includes user/org IDs or labels
- **Key**: Distinct identifier (like a file name)

This hierarchical structure enables cross-namespace searching through content filters.

### Basic Memory Operations

```python
from langgraph.store.memory import InMemoryStore

def embed(texts: list[str]) -> list[list[float]]:
    # Replace with an actual embedding function or LangChain embeddings object
    return [[1.0, 2.0] * len(texts)]

# InMemoryStore saves data to an in-memory dictionary. Use a DB-backed store in production.
store = InMemoryStore(index={"embed": embed, "dims": 2})

user_id = "my-user"
application_context = "chitchat"
namespace = (user_id, application_context)

# Store memory
store.put(
    namespace,
    "a-memory",
    {
        "rules": [
            "User likes short, direct language",
            "User only speaks English & python",
        ],
        "my-key": "my-value",
    },
)

# Get memory by ID
item = store.get(namespace, "a-memory")

# Search for memories within namespace
items = store.search(
    namespace,
    filter={"my-key": "my-value"},
    query="language preferences"
)
```

### Reading Long-Term Memory in Tools

```python
from dataclasses import dataclass
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
from langgraph.config import get_store
from langgraph.runtime import get_runtime
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

# InMemoryStore saves data to an in-memory dictionary. Use a DB-backed store in production.
store = InMemoryStore()

# Write sample data
store.put(
    ("users",),  # Namespace for user data
    "user_123",  # User ID as key
    {
        "name": "John Smith",
        "language": "English",
    }
)

def get_user_info() -> str:
    """Look up user info."""
    # Access the store - same as that provided to `create_agent`
    store = get_runtime().store
    user_id = get_runtime(Context).context.user_id
    # Retrieve data from store - returns StoreValue object
    user_info = store.get(("users",), user_id)
    return str(user_info.value) if user_info else "Unknown user"

agent = create_agent(
    model="anthropic:claude-3-7-sonnet-latest",
    tools=[get_user_info],
    store=store,  # Pass store to agent
    context_schema=Context
)

# Run the agent
agent.invoke(
    {"messages": [{"role": "user", "content": "look up user information"}]},
    context=Context(user_id="user_123")
)
```

### Writing Long-Term Memory from Tools

```python
from typing_extensions import TypedDict
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
from langgraph.config import get_store
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

class UserInfo(TypedDict):
    name: str

def save_user_info(user_info: UserInfo, config: RunnableConfig) -> str:
    """Save user info."""
    store = get_store()
    user_id = config["configurable"].get("user_id")
    # Store data (namespace, key, data)
    store.put(("users",), user_id, user_info)
    return "Successfully saved user info."

agent = create_agent(
    model="anthropic:claude-3-7-sonnet-latest",
    tools=[save_user_info],
    store=store
)

# Run the agent
agent.invoke(
    {"messages": [{"role": "user", "content": "My name is John Smith"}]},
    config={"configurable": {"user_id": "user_123"}}
)

# Access stored data directly
store.get(("users",), "user_123").value
```

---

## Context Engineering

Context engineering is building dynamic systems to provide the right information and tools in the right format so the LLM can accomplish the task. This is the primary factor in making agents reliable.

### Why Agents Fail

When agents fail, it's usually because:
1. **The underlying LLM is not good enough** (less common)
2. **The "right" context was not passed to the LLM** (most common)

### Core Agent Loop

1. Get user input
2. Call LLM, asking it to either respond or call tools
3. If it decides to call tools - execute those tools
4. Repeat steps 2-3 until it decides to finish

### Types of Context

| Context Type | Description | Read/Write |
|--------------|-------------|------------|
| **Instructions** | Base instructions (system prompt) - static or dynamic | Read-only |
| **Tools** | Tool names, descriptions, and arguments available to agent | Read-only |
| **Structured Output** | Response format specification | Read-only |
| **Session Context** | "Short-term memory" - messages and structured conversation info | Read & Write |
| **Long Term Memory** | Information persisting across sessions (extracted preferences) | Read & Write |
| **Runtime Configuration** | Non-modifiable config for agent run (user ID, DB connections) | Read-only |

### Context Engineering Functionality

#### Custom System Prompt

```python
# Use `prompt` parameter to pass function returning string
agent = create_agent(
    model="openai:gpt-4o",
    tools=[...],
    prompt=lambda state: f"You are a helpful assistant for {state['user_name']}"
)
```

**Use cases:**
- Personalize system prompt with session context, long-term memory, or runtime context

#### Explicit Control Over Messages

```python
# Use `prompt` parameter to return list of messages
def custom_messages(state):
    messages = state["messages"]
    # Reinforce instructions by adding system message at end
    messages.append({"role": "system", "content": "Remember to be concise"})
    return messages

agent = create_agent(
    model="openai:gpt-4o",
    tools=[...],
    prompt=custom_messages
)
```

**Use cases:**
- Reinforce instructions without updating state

#### Access Runtime Configuration in Prompt

```python
from langgraph.runtime import get_runtime

def dynamic_prompt(state):
    runtime = get_runtime()
    user_id = runtime.context.get("user_id")
    # Look up user profile and customize prompt
    return f"Assistant for user {user_id}"

agent = create_agent(
    model="openai:gpt-4o",
    tools=[...],
    prompt=dynamic_prompt
)
```

**Use cases:**
- Use user_id to look up profile and customize system prompt

#### Access Session Context in Prompt

```python
def context_aware_prompt(state):
    preferences = state.get("user_preferences", {})
    return f"User preferences: {preferences}"

agent = create_agent(
    model="openai:gpt-4o",
    tools=[...],
    prompt=context_aware_prompt
)
```

**Use cases:**
- Use structured session information in system prompt

#### Access Long-Term Memory in Prompt

```python
from langgraph.config import get_store

def memory_aware_prompt(state):
    store = get_store()
    user_prefs = store.get(("users",), "user_123")
    return f"User preferences: {user_prefs.value}"

agent = create_agent(
    model="openai:gpt-4o",
    tools=[...],
    prompt=memory_aware_prompt
)
```

**Use cases:**
- Look up user preferences from long-term memory for system prompt

#### Update Session Context Before Model Invocation

```python
def pre_model_hook(state):
    # Filter messages if list is getting long
    if len(state["messages"]) > 50:
        state["messages"] = state["messages"][-20:]  # Keep last 20
    return state

agent = create_agent(
    model="openai:gpt-4o",
    tools=[...],
    pre_model_hook=pre_model_hook
)
```

**Use cases:**
- Filter messages if context is getting too large
- Create conversation summary every N messages

#### Access Runtime Configuration in Tools

```python
from langgraph.runtime import get_runtime

def lookup_tool(query: str):
    """Look up information."""
    runtime = get_runtime()
    user_id = runtime.context.get("user_id")
    # Use user_id to look up information
    return f"Results for {user_id}: {query}"

agent = create_agent(
    model="openai:gpt-4o",
    tools=[lookup_tool]
)
```

**Use cases:**
- Use user_id to personalize tool behavior

#### Access Session Context in Tools

```python
from langchain.agents.tool_node import InjectedState
from typing import Annotated

def context_tool(query: str, state: Annotated[AgentState, InjectedState]):
    """Tool with access to session state."""
    messages = state["messages"]
    # Use messages in tool logic
    return f"Processed based on {len(messages)} messages"

agent = create_agent(
    model="openai:gpt-4o",
    tools=[context_tool]
)
```

**Use cases:**
- Pass messages to subagent

#### Update Session Context in Tools

```python
from langgraph.types import Command

def update_tool(value: str):
    """Tool that updates state."""
    return Command(update={"custom_field": value})

agent = create_agent(
    model="openai:gpt-4o",
    tools=[update_tool]
)
```

**Use cases:**
- Use tools to update virtual file system in state

#### Update Tools Before Model Call

```python
def dynamic_tools(state):
    base_model = init_chat_model("openai:gpt-4o")

    # Conditionally attach tools
    if state["requires_special_tool"]:
        return base_model.bind_tools([special_tool])
    return base_model.bind_tools([normal_tool])

agent = create_agent(
    model=dynamic_tools,
    tools=[normal_tool, special_tool]
)
```

**Use cases:**
- Force agent to call certain tool first
- Only give access to tools after calling other tools
- Remove tool access after N iterations

#### Update Model Before Model Call

```python
def dynamic_model(state):
    # Use larger context window model if messages are long
    if len(state["messages"]) > 50:
        return init_chat_model("openai:gpt-4o-128k")
    return init_chat_model("openai:gpt-4o")

agent = create_agent(
    model=dynamic_model,
    tools=[...]
)
```

**Use cases:**
- Use model with longer context window when needed
- Use smarter model if original gets stuck

---

## Structured Output

Structured output allows agents to return data in a specific, predictable format (JSON objects, Pydantic models, or dataclasses).

### Response Format Configuration

```python
def create_agent(
    ...,
    response_format: Union[
        ToolStrategy[StructuredResponseT],
        ProviderStrategy[StructuredResponseT],
        type[StructuredResponseT],
    ]
)
```

**Parameters:**
- `ToolStrategy`: Uses tool calling for structured output
- `ProviderStrategy`: Uses provider-native structured output
- `type[StructuredResponseT]`: Schema type - automatically selects best strategy
- `None`: No structured output

The structured response is returned in the `structured_response` key of the agent's final state.

### Provider Strategy

Provider-native structured output (OpenAI and Grok only). Most reliable when available.

```python
from pydantic import BaseModel, Field
from langchain.agents import create_agent

class ContactInfo(BaseModel):
    """Contact information for a person."""
    name: str = Field(description="The name of the person")
    email: str = Field(description="The email address of the person")
    phone: str = Field(description="The phone number of the person")

agent = create_agent(
    model="openai:gpt-5",
    tools=tools,
    response_format=ContactInfo  # Auto-selects ProviderStrategy
)

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"
    }]
})

result["structured_response"]
# ContactInfo(name='John Doe', email='john@example.com', phone='(555) 123-4567')
```

### Tool Strategy

For models without native structured output. Works with all models supporting tool calling.

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class ProductReview(BaseModel):
    """Analysis of a product review."""
    rating: Optional[int] = Field(description="The rating of the product", ge=1, le=5)
    sentiment: Literal["positive", "negative"] = Field(description="The sentiment of the review")
    key_points: list[str] = Field(description="The key points of the review. Lowercase, 1-3 words each.")

agent = create_agent(
    model="openai:gpt-5",
    tools=tools,
    response_format=ToolStrategy(ProductReview)
)

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"
    }]
})

result["structured_response"]
# ProductReview(rating=5, sentiment='positive', key_points=['fast shipping', 'expensive'])
```

### Custom Tool Message Content

```python
from pydantic import BaseModel, Field
from typing import Literal
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class MeetingAction(BaseModel):
    """Action items extracted from a meeting transcript."""
    task: str = Field(description="The specific task to be completed")
    assignee: str = Field(description="Person responsible for the task")
    priority: Literal["low", "medium", "high"] = Field(description="Priority level")

agent = create_agent(
    model="openai:gpt-5",
    tools=[],
    response_format=ToolStrategy(
        schema=MeetingAction,
        tool_message_content="Action item captured and added to meeting notes!"
    )
)

agent.invoke({
    "messages": [{
        "role": "user",
        "content": "From our meeting: Sarah needs to update the project timeline as soon as possible"
    }]
})
```

### Error Handling Strategies

**Default (True) - Catch all errors:**
```python
ToolStrategy(schema=ProductRating)  # Default: handle_errors=True
```

**Custom error message:**
```python
ToolStrategy(
    schema=ProductRating,
    handle_errors="Please provide a valid rating between 1-5 and include a comment."
)
```

**Handle specific exceptions:**
```python
ToolStrategy(
    schema=ProductRating,
    handle_errors=ValueError  # Only retry on ValueError
)
```

**Handle multiple exception types:**
```python
ToolStrategy(
    schema=ProductRating,
    handle_errors=(ValueError, TypeError)
)
```

**Custom error handler function:**
```python
def custom_error_handler(error: Exception) -> str:
    if isinstance(error, StructuredOutputValidationError):
        return "There was an issue with the format. Try again."
    elif isinstance(error, MultipleStructuredOutputsError):
        return "Multiple structured outputs were returned. Pick the most relevant one."
    else:
        return f"Error: {str(error)}"

ToolStrategy(
    schema=ToolStrategy(Union[ContactInfo, EventDetails]),
    handle_errors=custom_error_handler
)
```

**No error handling:**
```python
ToolStrategy(
    schema=ProductRating,
    handle_errors=False  # All errors raised
)
```

---

## Model Context Protocol (MCP)

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) standardizes how applications provide tools and context to LLMs. LangChain agents can use MCP servers via [`langchain-mcp-adapters`](https://github.com/langchain-ai/langchain-mcp-adapters).

### Installation

```bash
pip install langchain-mcp-adapters
# OR
uv pip install langchain-mcp-adapters
```

### Transport Types

- **stdio**: Client launches server as subprocess, communicates via stdin/stdout. Best for local tools.
- **Streamable HTTP**: Server runs independently, handles HTTP requests. Supports remote connections.
- **Server-Sent Events (SSE)**: Variant of streamable HTTP optimized for real-time streaming.

### Using MCP Tools

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient(
    {
        "math": {
            "transport": "stdio",  # Local subprocess communication
            "command": "python",
            "args": ["/path/to/math_server.py"],  # Absolute path to server
        },
        "weather": {
            "transport": "streamable_http",  # HTTP-based remote server
            "url": "http://localhost:8000/mcp",  # Ensure server is running
        }
    }
)

tools = await client.get_tools()
agent = create_agent(
    "anthropic:claude-3-7-sonnet-latest",
    tools
)

# Use math tools
math_response = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "what's (3 + 5) x 12?"}]}
)

# Use weather tools
weather_response = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "what is the weather in nyc?"}]}
)
```

> **Note:** `MultiServerMCPClient` is **stateless by default**. Each tool invocation creates a fresh MCP `ClientSession`, executes the tool, and cleans up.

### Creating Custom MCP Servers

```bash
pip install mcp
# OR
uv pip install mcp
```

**Math server (stdio transport):**

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**Weather server (streamable HTTP transport):**

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather")

@mcp.tool()
async def get_weather(location: str) -> str:
    """Get weather for location."""
    return "It's always sunny in New York"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### Exposing LangChain Tools via MCP

```python
from langchain_core.tools import tool
from langchain_mcp_adapters.tools import to_fastmcp
from mcp.server.fastmcp import FastMCP

@tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@tool
def get_user_info(user_id: str) -> str:
    """Get information about a user"""
    return f"User {user_id} is active"

# Convert LangChain tools to FastMCP
fastmcp_tools = [to_fastmcp(tool) for tool in (add, get_user_info)]

# Create server using converted tools
mcp = FastMCP("LangChain Tools", tools=fastmcp_tools)
mcp.run(transport="stdio")
```

### Stateful Tool Usage

For servers maintaining context between tool calls:

```python
from langchain_mcp_adapters.tools import load_mcp_tools

client = MultiServerMCPClient({...})
async with client.session("math") as session:
    tools = await load_mcp_tools(session)
```

---

## Human-in-the-Loop

Human-in-the-Loop (HITL) middleware allows human oversight of agent tool calls. When a model proposes an action requiring review, the middleware pauses execution using [interrupts](https://langchain-ai.github.io/langgraph/reference/types/#langgraph.types.interrupt).

### Interrupt Response Types

| Response Type | Description | Example Use Case |
|---------------|-------------|------------------|
| ✅ `accept` | Action approved as-is, executed without changes | Send email draft exactly as written |
| ✏️ `edit` | Tool call executed with modifications | Change recipient before sending email |
| ❌ `respond` | Tool call rejected with explanation | Reject email draft with rewrite instructions |

### Configuring Interrupts

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="openai:gpt-4o",
    tools=[write_file_tool, execute_sql_tool, read_data_tool],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "write_file": True,  # All actions (accept, edit, respond) allowed
                "execute_sql": {"allow_accept": True, "allow_respond": True},  # No editing
                "read_data": False,  # Safe operation, no approval needed
            },
            description_prefix="Tool execution pending approval",
        ),
    ],
    # HITL requires checkpointing. Use persistent checkpointer in production.
    checkpointer=InMemorySaver(),
)
```

> **Important:** You must configure a checkpointer to persist graph state across interrupts. In production, use [AsyncPostgresSaver](https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.postgres.aio.AsyncPostgresSaver).

### Responding to Interrupts

```python
from langgraph.types import Command

# Provide thread ID to associate execution with conversation thread
config = {"configurable": {"thread_id": "some_id"}}

# Run until interrupt
result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Delete old records from the database",
            }
        ]
    },
    config=config
)

# Check interrupt information
print(result['__interrupt__'])
# [
#    Interrupt(
#       value=[
#          {
#             'action': 'execute_sql',
#             'args': {'query': 'DELETE FROM records WHERE created_at < NOW() - INTERVAL \'30 days\';'},
#          }
#       ],
#    )
# ]

# Resume with approval decision
agent.invoke(
    Command(
        resume=[{"type": "accept"}]  # or "edit", "respond"
    ),
    config=config  # Same thread ID to resume
)
```

**Accept response:**
```python
agent.invoke(
    Command(
        resume=[
            {
                "type": "accept",
            }
        ]
    ),
    config=config
)
```

**Edit response:**
```python
agent.invoke(
    Command(
        resume=[
            {
                "type": "edit",
                "args": {"query": "DELETE FROM records WHERE created_at < NOW() - INTERVAL '60 days';"}
            }
        ]
    ),
    config=config
)
```

**Respond (reject) response:**
```python
agent.invoke(
    Command(
        resume=[
            {
                "type": "respond",
                "content": "Cannot delete records. Please archive them instead."
            }
        ]
    ),
    config=config
)
```

> **Warning:** When editing tool arguments, make changes conservatively. Significant modifications may cause the model to re-evaluate its approach.

### Execution Lifecycle

1. Agent invokes model to generate response
2. Middleware inspects response for tool calls
3. If calls require human input, middleware builds `HumanInterrupt` objects and calls [interrupt](https://langchain-ai.github.io/langgraph/reference/types/#langgraph.types.interrupt)
4. Agent waits for human responses
5. Based on responses, middleware executes approved/edited calls, synthesizes ToolMessages for rejected calls, and resumes execution

### Custom HITL Logic

For specialized workflows, build custom HITL logic using [interrupt](https://langchain-ai.github.io/langgraph/reference/types/#langgraph.types.interrupt) primitive and [middleware](https://docs.langchain.com/oss/python/langchain/middleware) abstraction.

---

## Multi-Agent Systems

Multi-agent systems break complex applications into specialized agents that work together. Instead of one agent handling everything, multiple focused agents compose into a coordinated workflow.

### When to Use Multi-Agent

- Single agent has too many tools and makes poor decisions
- Context or memory grows too large for one agent
- Tasks require specialization (planner, researcher, math expert)

### Multi-Agent Patterns

| Pattern | How it works | Control flow | Example use case |
|---------|--------------|--------------|------------------|
| **Tool Calling** | Central agent calls other agents as tools. Tool agents don't talk to user directly. | Centralized: all routing through calling agent | Task orchestration, structured workflows |
| **Handoffs** | Current agent transfers control to another agent. Active agent changes. | Decentralized: agents can change who is active | Multi-domain conversations, specialist takeover |

### Choosing a Pattern

| Question | Tool Calling | Handoffs |
|----------|--------------|----------|
| Need centralized control over workflow? | ✅ Yes | ❌ No |
| Want agents to interact directly with the user? | ❌ No | ✅ Yes |
| Complex, human-like conversation between specialists? | ❌ Limited | ✅ Strong |

> **Note:** You can mix both patterns - use handoffs for agent switching, and have each agent call subagents as tools.

### Tool Calling Pattern

One agent (controller) treats other agents as tools. Controller manages orchestration, tool agents perform tasks and return results.

**Flow:**
1. Controller receives input and decides which tool (subagent) to call
2. Tool agent runs task based on controller's instructions
3. Tool agent returns results to controller
4. Controller decides next step or finishes

**Implementation:**

```python
from langchain.tools import tool
from langchain.agents import create_agent

subagent1 = create_agent(...)

@tool(
    name="subagent1_name",
    description="subagent1_description"
)
def call_subagent1(query: str):
    result = subagent1.invoke({
        "messages": [{"role": "user", "content": query}]
    })
    return result["messages"].text

agent = create_agent(..., tools=[call_subagent1])
```

### Customization Points

1. **Subagent name** - How main agent refers to subagent (influences prompting)
2. **Subagent description** - What main agent "knows" about subagent (shapes decision)
3. **Input to subagent** - Customize how subagent interprets tasks
4. **Output from subagent** - Control how main agent interprets results

### Control Input to Subagent

```python
from typing import Annotated
from langchain.agents import AgentState
from langchain.agents.tool_node import InjectedState

@tool(
    name="subagent1_name",
    description="subagent1_description"
)
def call_subagent1(query: str, state: Annotated[CustomState, InjectedState]):
    # Apply logic to transform messages into suitable input
    subagent_input = some_logic(query, state.messages)
    result = subagent1.invoke({
        "messages": subagent_input,
        "example_state_key": state.example_state_key
    })
    return result["messages"][-1].text
```

### Control Output from Subagent

```python
from typing import Annotated
from langchain.agents import AgentState
from langchain_core.tools import InjectedToolCallId
from langgraph.types import Command

@tool(
    name="subagent1_name",
    description="subagent1_description"
)
def call_subagent1(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    result = subagent1.invoke({
        "messages": [{"role": "user", "content": query}]
    })
    return Command(update={
        "example_state_key": result["example_state_key"],
        "messages": [
            ToolMessage(
                result["messages"][-1].text,
                tool_call_id=tool_call_id
            )
        ]
    })
```

### Handoffs Pattern

Agents directly pass control to each other. The "active" agent changes, and user interacts with whichever agent currently has control.

**Flow:**
1. Current agent decides it needs help from another agent
2. It passes control (and state) to next agent
3. New agent interacts directly with user until it decides to hand off again or finish

> **Note:** Implementation details marked as "Coming soon" in documentation.

---

## Retrieval (RAG)

Retrieval-Augmented Generation addresses LLM limitations:
- **Finite context** - Can't ingest entire corpora at once
- **Static knowledge** - Training data frozen at point in time

Retrieval fetches relevant external knowledge at query time.

### Building a Knowledge Base

A knowledge base is a repository of documents or structured data used during retrieval.

**If you already have a knowledge base** (SQL database, CRM, documentation system):
- Connect it as a tool for an agent (Agentic RAG)
- Query it and supply retrieved content as context to LLM (2-Step RAG)

**If you need a custom knowledge base:**
- Use LangChain's document loaders and vector stores

### Retrieval Pipeline

```
Sources (Google Drive, Slack, Notion, etc.)
    ↓
Document Loaders
    ↓
Documents
    ↓
Split into chunks
    ↓
Turn into embeddings
    ↓
Vector Store
    ↓
User Query → Query embedding → Retriever → LLM uses retrieved info → Answer
```

### Building Blocks

- **Document loaders**: Ingest data from external sources, return standardized `Document` objects
- **Text splitters**: Break large docs into smaller retrievable chunks
- **Embedding models**: Turn text into vectors for similarity search
- **Vector stores**: Specialized databases for storing and searching embeddings
- **Retrievers**: Interface that returns documents given unstructured query

### RAG Architectures

| Architecture | Description | Control | Flexibility | Latency | Example Use Case |
|--------------|-------------|---------|-------------|---------|------------------|
| **Agentic RAG** | LLM-powered agent decides when/how to retrieve during reasoning | ❌ Low | ✅ High | ⏳ Variable | Research assistants with multiple tools |
| **2-Step RAG** | Retrieval always happens before generation | ✅ High | ❌ Low | ⚡ Fast | FAQs, documentation bots |
| **Hybrid** | Combines both approaches with validation steps | ⚖️ Medium | ⚖️ Medium | ⏳ Variable | Domain-specific Q&A with validation |

### Agentic RAG

Agent reasons step-by-step and decides **when** and **how** to retrieve information during interaction. Only requirement: access to tools that can fetch external knowledge.

**Implementation:**

```python
import requests
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent

@tool
def fetch_url(url: str) -> str:
    """Fetch text content from a URL"""
    response = requests.get(url, timeout=10.0)
    response.raise_for_status()
    return response.text

system_prompt = """
Use fetch_url when you need to fetch information from a web-page; quote relevant snippets.
"""

agent = create_react_agent(
    model=init_chat_model("claude-sonnet-4-0"),
    tools=[fetch_url],  # A tool for retrieval
    prompt=system_prompt,
)
```

**Extended Example: Agentic RAG for LangGraph's llms.txt**

```python
import requests
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from markdownify import markdownify

ALLOWED_DOMAINS = ["https://langchain-ai.github.io/"]
LLMS_TXT = 'https://langchain-ai.github.io/langgraph/llms.txt'

@tool
def fetch_documentation(url: str) -> str:
    """Fetch and convert documentation from a URL"""
    if not any(url.startswith(domain) for domain in ALLOWED_DOMAINS):
        return (
            "Error: URL not allowed. "
            f"Must start with one of: {', '.join(ALLOWED_DOMAINS)}"
        )
    response = requests.get(url, timeout=10.0)
    response.raise_for_status()
    return markdownify(response.text)

# Fetch llms.txt content ahead of time
llms_txt_content = requests.get(LLMS_TXT).text

system_prompt = f"""
You are an expert Python developer and technical assistant.
Your primary role is to help users with questions about LangGraph and related tools.

Instructions:

1. If a user asks a question you're unsure about — or one that likely involves API usage,
   behavior, or configuration — you MUST use the `fetch_documentation` tool to consult the relevant docs.
2. When citing documentation, summarize clearly and include relevant context from the content.
3. Do not use any URLs outside of the allowed domain.
4. If a documentation fetch fails, tell the user and proceed with your best expert understanding.

You can access official documentation from the following approved sources:

{llms_txt_content}

You MUST consult the documentation to get up to date documentation
before answering a user's question about LangGraph.

Your answers should be clear, concise, and technically accurate.
"""

tools = [fetch_documentation]

model = init_chat_model("claude-sonnet-4-0", max_tokens=32_000)

agent = create_react_agent(
    model=model,
    tools=tools,
    prompt=system_prompt,
    name="Agentic RAG",
)

response = agent.invoke({
    'messages': [{
        'role': 'user',
        'content': (
            "Write a short example of a langgraph agent using the "
            "prebuilt create react agent. the agent should be able "
            "to look up stock pricing information."
        )
    }]
})

print(response['messages'][-1].content)
```

### 2-Step RAG

Retrieval always executed before generation. Straightforward and predictable.

**Flow:**
```
User Question
    ↓
Retrieve Relevant Documents
    ↓
Generate Answer
    ↓
Return Answer to User
```

**Implementation:** See [RAG Tutorial](https://docs.langchain.com/oss/python/langchain/rag#rag-chains)

### Hybrid RAG

Combines 2-Step and Agentic RAG. Introduces intermediate steps:
- **Query enhancement**: Modify input to improve retrieval quality
- **Retrieval validation**: Evaluate if retrieved documents are relevant/sufficient
- **Answer validation**: Check generated answer for accuracy and completeness

**Flow:**
```
User Question
    ↓
Query Enhancement
    ↓
Retrieve Documents
    ↓
Sufficient Info? → No → Refine Query (loop back)
    ↓ Yes
Generate Answer
    ↓
Answer Quality OK? → No → Try Different Approach? → Yes (loop back)
    ↓ Yes
Return Best Answer
    ↓
Return to User
```

**Use cases:**
- Ambiguous or underspecified queries
- Systems requiring validation/quality control
- Workflows involving multiple sources or iterative refinement

---

## Middleware

Middleware provides tight control over agent internals. Core agent loop involves calling `model`, letting it choose `tools`, and finishing when no more tools called.

### Middleware Types

Each middleware can add three modifiers:
- `before_model`: Runs before model execution. Can update state or jump to different node.
- `modify_model_request`: Runs before model execution to prepare model request. Can only modify request (no state updates, no jumps).
- `after_model`: Runs after model execution, before tools. Can update state or jump to different node.

### Using Middleware in Agent

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware, HumanInTheLoopMiddleware

agent = create_agent(
    ...,
    middleware=[SummarizationMiddleware(), HumanInTheLoopMiddleware()],
    ...
)
```

**Restrictions when using middleware:**
- `model` must be string or `BaseChatModel` (not function)
- `prompt` must be string or None (not function)
- `pre_model_hook` must not be provided (use `AgentMiddleware.before_model`)
- `post_model_hook` must not be provided (use `AgentMiddleware.after_model`)

### Built-in Middleware

#### Summarization Middleware

Automatically manages conversation history by summarizing older messages when token limits approached.

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="openai:gpt-4o",
    tools=[weather_tool, calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="openai:gpt-4o-mini",
            max_tokens_before_summary=4000,  # Trigger at 4000 tokens
            messages_to_keep=20,  # Keep last 20 messages after summary
            summary_prompt="Custom prompt for summarization...",  # Optional
        ),
    ],
)
```

**Configuration:**
- `model`: Language model for generating summaries (required)
- `max_tokens_before_summary`: Token threshold triggering summarization
- `messages_to_keep`: Recent messages to preserve (default: 20)
- `token_counter`: Custom function for counting tokens
- `summary_prompt`: Custom prompt template for summary generation
- `summary_prefix`: Prefix added to system messages with summaries

**Use cases:**
- Long-running conversations exceeding token limits
- Multi-turn dialogues with extensive context

#### Human-in-the-Loop Middleware

See [Human-in-the-Loop section](#human-in-the-loop) for details.

#### Anthropic Prompt Caching Middleware

Enables Anthropic's native prompt caching for optimal API usage.

```python
from langchain_anthropic import ChatAnthropic
from langchain.agents.middleware.prompt_caching import AnthropicPromptCachingMiddleware
from langchain.agents import create_agent

LONG_PROMPT = """
Please be a helpful assistant.

<Lots more context ...>
"""

agent = create_agent(
    model=ChatAnthropic(model="claude-sonnet-4-latest"),
    prompt=LONG_PROMPT,
    middleware=[AnthropicPromptCachingMiddleware(ttl="5m")],
)

# cache store
agent.invoke({"messages": [HumanMessage("Hi, my name is Bob")]})

# cache hit, system prompt is cached
agent.invoke({"messages": [HumanMessage("What's my name?")]})
```

> **Note:** When using prompt caching, you'll likely want to use a checkpointer to store conversation history across invocations.

#### Dynamic System Prompt Middleware

Dynamically set system prompt before each model invocation using `@modify_model_request` decorator.

**Based on user expertise:**

```python
from typing import TypedDict
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware.types import modify_model_request
from langgraph.runtime import Runtime

class Context(TypedDict):
    user_role: str

@modify_model_request
def dynamic_system_prompt(state: AgentState, request: ModelRequest, runtime: Runtime[Context]) -> ModelRequest:
    user_role = runtime.context.get("user_role", "user")
    base_prompt = "You are a helpful assistant."

    if user_role == "expert":
        prompt = f"{base_prompt} Provide detailed technical responses."
    elif user_role == "beginner":
        prompt = f"{base_prompt} Explain concepts simply and avoid jargon."
    else:
        prompt = base_prompt

    request.system_prompt = prompt
    return request

agent = create_agent(
    model="openai:gpt-4o",
    tools=[web_search],
    middleware=[dynamic_system_prompt],
)

# Use with context
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Explain async programming"}]},
    {"context": {"user_role": "expert"}}
)
```

**Based on conversation length:**

```python
from langchain.agents.middleware.types import modify_model_request

@modify_model_request
def simple_prompt(state: AgentState, request: ModelRequest) -> ModelRequest:
    message_count = len(state["messages"])

    if message_count > 10:
        prompt = "You are in an extended conversation. Be more concise."
    else:
        prompt = "You are a helpful assistant."

    request.system_prompt = prompt
    return request

agent = create_agent(
    model="openai:gpt-4o",
    tools=[search_tool],
    middleware=[simple_prompt],
)
```

### Custom Middleware

Subclass `AgentMiddleware` and implement one or more hooks.

#### before_model Hook

```python
from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain_core.messages import AIMessage

class MyMiddleware(AgentMiddleware):
    def before_model(self, state: AgentState) -> dict[str, Any] | None:
        # Terminate early if conversation too long
        if len(state["messages"]) > 50:
            return {
                "messages": [AIMessage("I'm sorry, the conversation has been terminated.")],
                "jump_to": "end"
            }
        return state
```

#### modify_model_request Hook

```python
from langchain.agents.middleware import AgentState, ModelRequest, AgentMiddleware

class MyMiddleware(AgentMiddleware):
    def modify_model_request(self, request: ModelRequest, state: AgentState) -> ModelRequest:
        if len(state["messages"]) > 10:
            request.model = "gpt-5"
        else:
            request.model = "gpt-5-nano"
        return request
```

**ModelRequest properties:**
- `model` (BaseChatModel): The model to use
- `system_prompt` (str): System prompt (prepended to messages)
- `messages` (list): Message list (should not include system prompt)
- `tool_choice` (Any): Tool choice to use
- `tools` (list[BaseTool]): Tools for this model call
- `response_format` (ResponseFormat): Response format for structured output

#### after_model Hook

```python
from langchain.agents.middleware import AgentState, AgentUpdate, AgentMiddleware

class MyMiddleware(AgentMiddleware):
    def after_model(self, state: AgentState) -> dict[str, Any] | None:
        # Custom logic after model execution
        return state
```

### State and Context Extension

Middleware can extend agent state with custom properties:

```python
from langchain.agents.middleware import AgentState, AgentMiddleware

class MyState(AgentState):
    model_call_count: int

class MyMiddleware(AgentMiddleware[MyState]):
    state_schema: MyState

    def before_model(self, state: AgentState) -> dict[str, Any] | None:
        # Terminate if model called too many times
        if state["model_call_count"] > 10:
            return {"jump_to": "end"}
        return state

    def after_model(self, state: AgentState) -> dict[str, Any] | None:
        return {"model_call_count": state["model_call_count"] + 1}
```

### Combining Multiple Middleware

When using multiple middleware, their state and context schemas are merged:

```python
from langchain.agents.middleware import AgentMiddleware
from typing import Any, Dict

class Middleware1State(AgentState):
    prop_1: str
    shared_prop: int

class Middleware2State(AgentState):
    prop_2: bool
    shared_prop: int

class Middleware1(AgentMiddleware):
    def before_model(self, state: Dict[str, Any]) -> Dict[str, Any] | None:
        print(f"Middleware1: prop1={state.get('prop_1')}, sharedProp={state.get('shared_prop')}")
        return None

class Middleware2(AgentMiddleware):
    def before_model(self, state: Dict[str, Any]) -> Dict[str, Any] | None:
        print(f"Middleware2: prop2={state.get('prop_2')}, sharedProp={state.get('shared_prop')}")
        return None

agent = create_agent(
    model="openai:gpt-4o",
    tools=[],
    middleware=[Middleware1(), Middleware2()],
)
```

### Middleware Execution Order

- **before_model**: Run in order passed in. If earlier middleware exits early, following middleware not run.
- **modify_model_request**: Run in order passed in.
- **after_model**: Run in reverse order. If earlier middleware exits early, following middleware not run.

### Agent Jumps

Exit early by adding `jump_to` key to state update:
- `"model"`: Jump to model node
- `"tools"`: Jump to tools node
- `"end"`: Jump to end node

If specified, all subsequent middleware will not run.

```python
from langchain.agents.types import AgentState, AgentUpdate, AgentJump
from langchain.agents.middleware import AgentMiddleware

class MyMiddleware(AgentMiddleware):
    def after_model(self, state: AgentState) -> dict[str, Any]:
        return {
            "messages": ...,
            "jump_to": "model"
        }
```

> **Note:** If you jump to `model` node, all `before_model` middleware will run. It's forbidden to jump to `model` from existing `before_model` middleware.

### Best Practices

1. **Use State for Dynamic Data**: Properties that change during execution
2. **Use Context for Configuration**: Static configuration values
3. **Provide Defaults When Possible**: Use defaults to make properties optional
4. **Document Requirements**: Clearly document state and context requirements

---

## Summary of Key Findings

### Long-Term Memory
- Uses LangGraph persistence with JSON document store
- Organized by namespace (user/org IDs) and keys
- Supports vector similarity search with embeddings
- Accessible in tools via `get_store()` and `get_runtime()`

### Context Engineering
- Primary factor in agent reliability
- Types: Instructions, Tools, Structured Output, Session Context, Long-Term Memory, Runtime Configuration
- Extensive customization points: prompts, message generation, tool access, model selection
- Dynamic context based on state, runtime config, and memory

### Structured Output
- Two strategies: ProviderStrategy (native support) and ToolStrategy (tool calling)
- Supports Pydantic models, dataclasses, TypedDict, JSON Schema
- Built-in error handling with retry mechanisms
- Custom tool message content and error handlers

### Model Context Protocol (MCP)
- Standardizes tool and context provision to LLMs
- Three transport types: stdio, streamable HTTP, SSE
- `MultiServerMCPClient` for multi-server access
- Can expose LangChain tools as MCP servers
- Stateless by default, stateful via sessions

### Human-in-the-Loop
- Three response types: accept, edit, respond
- Configurable per-tool interrupt policies
- Requires checkpointer for state persistence
- Execution lifecycle with interrupt/resume pattern
- Compatible with LangChain UI applications

### Multi-Agent Systems
- Two patterns: Tool Calling (centralized) and Handoffs (decentralized)
- Tool Calling treats agents as tools with customizable input/output
- Handoffs allow direct control transfer between agents
- Context engineering critical for multi-agent coordination
- Patterns can be mixed for complex workflows

### Retrieval (RAG)
- Three architectures: Agentic RAG (flexible), 2-Step RAG (predictable), Hybrid (balanced)
- Building blocks: document loaders, text splitters, embeddings, vector stores, retrievers
- Agentic RAG uses tools for retrieval decisions
- 2-Step RAG always retrieves before generation
- Hybrid RAG adds validation and refinement steps

### Middleware
- Three hook types: before_model, modify_model_request, after_model
- Built-in: Summarization, HITL, Anthropic caching, Dynamic prompts
- Custom middleware via `AgentMiddleware` subclass
- State and context extension for custom properties
- Execution order: before_model (forward), modify_model_request (forward), after_model (reverse)
- Agent jumps for early exit: "model", "tools", "end"

---

## Additional Resources

- [LangChain v1-alpha Documentation](https://docs.langchain.com/oss/python/releases/langchain-v1)
- [LangGraph Persistence Guide](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Model Context Protocol](https://modelcontextprotocol.io/introduction)
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- [LangGraph Human-in-the-Loop](https://docs.langchain.com/oss/python/langgraph/add-human-in-the-loop)

---

**End of Document**
