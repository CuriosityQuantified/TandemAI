# LangChain v1.0 Core Components Implementation Guide

**Research Date:** October 1, 2025
**Status:** Alpha Release (v1-alpha)
**Documentation Source:** https://docs.langchain.com/oss/python/

---

## Table of Contents

1. [Version 1.0 Overview](#version-10-overview)
2. [Installation](#installation)
3. [Quickstart](#quickstart)
4. [Philosophy](#philosophy)
5. [Agents](#agents)
6. [Models](#models)
7. [Messages](#messages)
8. [Tools](#tools)
9. [Short-Term Memory](#short-term-memory)
10. [Streaming](#streaming)

---

## Version 1.0 Overview

### Alpha Release Status

LangChain v1.0 is currently in **alpha** release. The following packages support 1.0 alpha:

- `langchain`
- `langchain-core`
- `langchain-anthropic`
- `langchain-aws`
- `langchain-openai`

Broader support will be rolled out during the alpha period.

### New Features

#### Message Content Blocks

A new `.content_blocks` property on message objects provides:
- Fully typed view of message content
- Standardizes modern LLM features across providers
- Supports reasoning, citations, server-side tool calls
- No breaking changes to existing message content
- See [Messages documentation](https://docs.langchain.com/oss/python/langchain/messages#content) for details

#### Prebuilt LangGraph Chains and Agents

- Surface area of `langchain` package reduced to focus on popular and essential abstractions
- New `langchain-legacy` package available for backward compatibility
- See [agents docs](https://docs.langchain.com/oss/python/langchain/agents)
- See [release notes](https://github.com/langchain-ai/langchain/releases/tag/langchain%3D%3D1.0.0a1)

### Breaking Changes

#### Dropped Python 3.9 Support

Python 3.9 reaches end of life in October 2025. All LangChain packages now require **Python 3.10 or higher**.

#### Legacy Code Moved to `langchain-legacy`

The new `langchain` package features reduced surface area focusing on:
- Standard interfaces for LangChain components (`init_chat_model`, `init_embeddings`)
- Pre-built chains and agents backed by the `langgraph` runtime

Existing functionality outside this focus moved to `langchain-legacy` package:
- Indexing API
- Exports of `langchain-community` features

**Migration:**

```python
# Before
from langchain import ...

# After
from langchain_legacy import ...
```

#### Updated Return Type for Chat Models

Return type signature fixed from `BaseMessage` to `AIMessage`:

```python
# Before
Runnable[LanguageModelInput, BaseMessage]:

# After
Runnable[LanguageModelInput, AIMessage]:
```

Custom chat models implementing `bind_tools` should update their return signature.

#### Default Message Format for OpenAI Responses API

`langchain-openai` now defaults to storing response items in message `content`:
- Previous behavior required `output_version="responses/v1"` when instantiating `ChatOpenAI`
- Change resolves `BadRequestError` in multi-turn contexts

**To restore previous behavior:**

```python
import os
os.environ["LC_OUTPUT_VERSION"] = "v0"

# or

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="...", output_version="v0")
```

#### Default `max_tokens` in `langchain-anthropic`

The `max_tokens` parameter in `ChatAnthropic` now defaults to higher values (varies by model) instead of previous default of `1024`.

#### Removal of Deprecated Objects

Methods, functions, and objects already deprecated and slated for removal in 1.0 have been deleted.

### Deprecations

#### `.text()` is Now a Property

```python
# Before
text = response.text()  # Method call

# After
text = response.text    # Property access
```

Existing usage patterns (`.text()`) will continue to function but emit a warning.

---

## Installation

### Core LangChain Package

Install the core LangChain package with the `--pre` flag for alpha releases:

```bash
# Using pip
pip install --pre -U langchain

# Using uv (recommended)
uv pip install --pre -U langchain
```

### Provider Integrations

LangChain integrations live in independent provider packages to avoid bloat:

```bash
# Using pip
pip install -U langchain-openai      # OpenAI integration
pip install -U langchain-anthropic   # Anthropic integration

# Using uv (recommended)
uv pip install -U langchain-openai
uv pip install -U langchain-anthropic
```

See the [Integrations tab](https://docs.langchain.com/oss/python/integrations/providers) for full list of available integrations.

---

## Quickstart

### Build a Basic Agent

Create a simple agent with:
- Language model (Claude 3.7 Sonnet)
- Simple tool (weather function)
- Basic prompt
- Message invocation

```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="anthropic:claude-3-7-sonnet-latest",
    tools=[get_weather],
    prompt="You are a helpful assistant",
)

# Run the agent
agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
)
```

### Build a Real-World Agent

Production-ready weather forecasting agent demonstrating:

1. **Detailed system prompts**
2. **Real-world tools**
3. **Model configuration**
4. **Structured output**
5. **Conversational memory**

#### 1. Define the System Prompt

```python
system_prompt = """You are an expert weather forecaster, who speaks in puns.

You have access to two tools:

- get_weather_for_location: use this to get the weather for a specific location
- get_user_location: use this to get the user's location

If a user asks you for the weather, make sure you know the location. If you can tell from the question that they mean whereever they are, use the get_user_location tool to find their location."""
```

#### 2. Create Tools

Tools with runtime configuration support:

```python
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

def get_weather_for_location(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

USER_LOCATION = {
    "1": "Florida",
    "2": "SF"
}

@tool
def get_user_location(config: RunnableConfig) -> str:
    """Retrieve user information based on user ID."""
    user_id = config["context"].get("user_id")
    return USER_LOCATION[user_id]
```

#### 3. Configure Your Model

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    "anthropic:claude-3-7-sonnet-latest",
    temperature=0
)
```

#### 4. Define Response Format

Structured outputs using Python's `DataClass`:

```python
from dataclasses import dataclass

@dataclass
class WeatherResponse:
    conditions: str
    punny_response: str
```

#### 5. Add Memory

Enable conversation history:

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
```

#### 6. Bring It All Together

```python
agent = create_agent(
    model=model,
    prompt=system_prompt,
    tools=[get_user_location, get_weather_for_location],
    response_format=WeatherResponse,
    checkpointer=checkpointer
)

config = {"configurable": {"thread_id": "1"}}
context = {"user_id": "1"}
response = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather outside?"}]},
    config=config,
    context=context
)

response['structured_response']

response = agent.invoke(
    {"messages": [{"role": "user", "content": "thank you!"}]},
    config=config,
    context=context
)

response['structured_response']
```

---

## Philosophy

### Core Beliefs

LangChain is driven by these principles:

1. **LLMs are great, powerful new technology**
2. **LLMs are better when combined with external data and computation**
3. **LLMs will transform future applications to be more agentic**
4. **It is still very early in that transformation**
5. **Building reliable production agents remains challenging**

### Core Focuses

#### 1. Model Flexibility

Enable developers to build with the best model at any time:
- Different providers expose different APIs, parameters, and message formats
- Standardizing model inputs and outputs is core focus
- Easy model switching avoids vendor lock-in

#### 2. Complex Flow Orchestration

Models should orchestrate complex flows beyond simple calling:
- Interact with external data and computation
- LangChain makes it easy to define tools for LLMs
- Help with parsing and accessing unstructured data

### Historical Evolution

#### October 24, 2022: LangChain Launched
- Month before ChatGPT
- Two main components:
  - LLM abstractions
  - "Chains" (predetermined computation steps for common use cases like RAG)
- Name from "Language" models and "Chains"

#### December 2022: General Purpose Agents Added
- Based on [ReAct paper](https://arxiv.org/abs/2210.03629) (Reasoning and Acting)
- Used LLMs to generate JSON representing tool calls
- Parsed JSON to determine tool execution

#### January 2023: OpenAI Chat Completion API
- Models evolved from string-in/string-out to message-based
- LangChain updated to work with message lists
- Other providers followed suit

#### January 2023: LangChain JavaScript Version
- LLMs and agents will change application development
- JavaScript is the language of application developers

#### February 2023: LangChain Inc. Formed
- Goal: "make intelligent agents ubiquitous"
- Recognized need for components beyond LangChain library

#### Spring 2023: OpenAI Function Calling
- API explicitly generates tool call payloads
- Other providers followed
- LangChain updated to prefer this over JSON parsing

#### Summer 2023: LangSmith Released
- Closed source platform for observability and evals
- Addresses reliability challenge in agent building
- LangChain integrates seamlessly with LangSmith

#### January 2024: LangChain 0.1 Released
- First non-0.0.x release
- Industry matured from prototypes to production
- Increased focus on stability

#### February 2024: LangGraph Released
- Open-source orchestration library
- Provides low-level control over agent flow
- Features: streaming, durable execution, short-term memory, human-in-the-loop

#### Summer 2024: 700+ Integrations
- Integrations split from core package
- Standalone packages for core integrations
- `langchain-community` for long tail

#### Fall 2024: LangGraph Becomes Preferred
- For any AI application beyond single LLM call
- Provides low-level flexibility for reliability
- Most chains/agents deprecated in LangChain with migration guides
- One high-level abstraction remains: agent abstraction built on LangGraph

#### Spring 2025: Multimodal Model APIs
- Models accept files, images, videos, and more
- `langchain-core` message format updated for multimodal inputs
- Standard way to specify diverse input types

---

## Agents

### Overview

Agents combine language models with tools to create systems that can:
- Reason about tasks
- Decide which tools to use
- Iteratively work towards solutions

`create_agent()` provides production-ready ReAct (Reasoning + Acting) implementation based on [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629).

### ReAct Pattern

Interleaving of `thought` → `action` → `observation` steps:
- Model writes reasoning (`thought`)
- Picks a tool (`action`)
- Sees tool result (`observation`)
- Repeats process

Benefits:
- Reduces hallucinations
- Makes decision process auditable
- Tests hypotheses with tools
- Updates plan based on feedback

Loop continues until:
- Model emits final answer
- Max-iterations limit reached

### Graph-Based Runtime

`create_agent()` builds a **graph**-based agent runtime using [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview):

- **Nodes**: Steps like model node, tools node, pre/post hooks
- **Edges**: Connections defining information flow
- Agent moves through graph executing nodes

Learn more: [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)

### Core Components

#### Model

The reasoning engine supporting static and dynamic selection.

##### Static Model

Configured once at creation, remains unchanged:

```python
from langchain.agents import create_agent

# From model identifier string
agent = create_agent(
    "openai:gpt-5",
    tools=tools
)
```

Model identifier format: `provider:model` (e.g., `"openai:gpt-5"`)
- Supports automatic inference: `"gpt-5"` inferred as `"openai:gpt-5"`

**With direct model configuration:**

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-5",
    temperature=0.1,
    max_tokens=1000,
    timeout=30
)
agent = create_agent(model, tools=tools)
```

Use model instances for:
- Specific parameter control (temperature, max_tokens, timeout)
- API keys, base URLs configuration
- Provider-specific settings

See [API reference](https://docs.langchain.com/oss/python/integrations/providers/all_providers) for available parameters.

##### Dynamic Model

Selected at runtime based on state and context:
- Enables sophisticated routing logic
- Cost optimization
- Must return `BaseChatModel` with `.bind_tools(tools)` called

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent, AgentState
from langgraph.runtime import Runtime

def select_model(state: AgentState, runtime: Runtime) -> ChatOpenAI:
    """Choose model based on conversation complexity."""
    messages = state["messages"]
    message_count = len(messages)

    if message_count < 10:
        return ChatOpenAI(model="gpt-4.1-mini").bind_tools(tools)
    else:
        return ChatOpenAI(model="gpt-5").bind_tools(tools)

agent = create_agent(select_model, tools=tools)
```

See [Models documentation](https://docs.langchain.com/oss/python/langchain/models) for details.

#### Tools

Tools give agents ability to take actions. Agents facilitate:
- Multiple tool calls in sequence from single prompt
- Parallel tool calls when appropriate
- Dynamic tool selection based on results
- Tool retry logic and error handling
- State persistence across tool calls

##### Pass a List of Tools

Simplest setup - creates `ToolNode` under the hood:

```python
from langchain_core.tools import tool
from langchain.agents import create_agent

@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

@tool
def calculate(expression: str) -> str:
    """Perform calculations."""
    return str(eval(expression))

agent = create_agent(model, tools=[search, calculate])
```

Empty tool list creates single LLM node without tool calling.

##### Pass a Configured ToolNode

Customize tool node behavior (e.g., error handling):

```python
from langchain.agents import ToolNode

tool_node = ToolNode(
    tools=[search, calculate],
    handle_tool_errors="Please check your input and try again."
)
agent = create_agent(model, tools=tool_node)
result = agent.invoke({"messages": [...]})
```

On error, agent returns `ToolMessage` with custom error message:

```python
# result["messages"]
[
    ...
    ToolMessage(content="Please check your input and try again.", tool_call_id="..."),
    ...
]
```

See [ToolNode documentation](https://docs.langchain.com/oss/python/langchain/tools#toolnode) for details.

##### Tool Use in ReAct Loop

Example workflow:

**Prompt:** "Identify the current most popular wireless headphones and verify availability."

```
================================ Human Message =================================
Find the most popular wireless headphones right now and check if they're in stock
```

**Reasoning:** "Popularity is time-sensitive, I need to use the provided search tool."
**Acting:** Call `search_products("wireless headphones")`

```
================================== Ai Message ==================================
Tool Calls:
  search_products (call_abc123)
 Call ID: call_abc123
  Args:
    query: wireless headphones
```

```
================================= Tool Message =================================
Found 5 products matching "wireless headphones". Top 5 results: WH-1000XM5, ...
```

**Reasoning:** "I need to confirm availability for the top-ranked item."
**Acting:** Call `check_inventory("WH-1000XM5")`

```
================================== Ai Message ==================================
Tool Calls:
  check_inventory (call_def456)
 Call ID: call_def456
  Args:
    product_id: WH-1000XM5
```

```
================================= Tool Message =================================
Product WH-1000XM5: 10 units in stock
```

**Reasoning:** "I have the most popular model and stock status."
**Acting:** Produce final answer

```
================================== Ai Message ==================================
I found wireless headphones (model WH-1000XM5) with 10 units in stock...
```

See [Tools documentation](https://docs.langchain.com/oss/python/langchain/tools).

#### Prompt

Shape agent behavior with system prompt. The `prompt` parameter accepts:
- String
- SystemMessage
- Callable

```python
# String
agent = create_agent(
    model,
    tools,
    prompt="You are a helpful assistant. Be concise and accurate."
)

# SystemMessage
from langchain_core.messages import SystemMessage
agent = create_agent(
    model,
    tools,
    prompt=SystemMessage(content="You are a helpful assistant.")
)

# Callable
def get_prompt(state):
    return SystemMessage(content="You are a helpful assistant.")

agent = create_agent(model, tools, prompt=get_prompt)
```

When no `prompt` is provided, agent infers task from messages directly.

##### Dynamic Prompts with Middleware

Use `modify_model_request` decorator for runtime-based prompts:

```python
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware.types import modify_model_request
from langgraph.runtime import Runtime
from typing import TypedDict

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
    tools=tools,
    middleware=[dynamic_system_prompt],
)

# System prompt set dynamically based on context
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Explain machine learning"}]},
    {"context": {"user_role": "expert"}}
)
```

See [Messages](https://docs.langchain.com/oss/python/langchain/messages) and [Middleware](https://docs.langchain.com/oss/python/langchain/middleware) documentation.

### Advanced Configuration

#### Structured Output

Return output in specific format using `response_format`:

```python
from pydantic import BaseModel
from langchain.agents import create_agent

class ContactInfo(BaseModel):
    name: str
    email: str
    phone: str

agent = create_agent(
    model,
    tools=[search_tool],
    response_format=ContactInfo
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
})

result["structured_response"]
# ContactInfo(name='John Doe', email='john@example.com', phone='(555) 123-4567')
```

See [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output).

#### Memory

Agents maintain conversation history automatically. Configure custom state schema for additional information:

```python
from typing import TypedDict
from typing_extensions import Annotated
from langgraph.graph.message import add_messages
from langchain.agents import create_agent, AgentState

class CustomAgentState(AgentState):
    messages: Annotated[list, add_messages]
    user_preferences: dict

agent = create_agent(
    model,
    tools=tools,
    state_schema=CustomAgentState
)

# Track additional state beyond messages
result = agent.invoke({
    "messages": [{"role": "user", "content": "I prefer technical explanations"}],
    "user_preferences": {"style": "technical", "verbosity": "detailed"},
})
```

See [Memory](https://docs.langchain.com/oss/python/concepts/memory) and [Long-term memory](https://docs.langchain.com/oss/python/langchain/long-term-memory).

#### Pre-Model Hook

Optional node processing state before model call. Use cases:
- Message trimming
- Summarization
- Context injection

Must return state update:

```python
{
    # Will UPDATE the `messages` in the state
    "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), ...],
    # Any other state keys that need to be propagated
    ...
}
```

Example trimming messages:

```python
from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langchain.agents import create_agent

def trim_messages(state):
    """Keep only the last few messages to fit context window."""
    messages = state["messages"]

    if len(messages) <= 3:
        return {"messages": messages}

    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages = [first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

agent = create_agent(
    model,
    tools=tools,
    pre_model_hook=trim_messages
)
```

**Important:** When returning `messages` in pre-model hook, OVERWRITE the key:

```python
{
    "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *new_messages]
    ...
}
```

#### Post-Model Hook

Optional node processing model response before tool execution. Use cases:
- Validation
- Guardrails
- Post-processing

Example filtering confidential information:

```python
from langchain_core.messages import AIMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

def validate_response(state):
    """Check model response for policy violations."""
    messages = state["messages"]
    last_message = messages[-1]

    if "confidential" in last_message.content.lower():
        return {
            "messages": [
                RemoveMessage(id=REMOVE_ALL_MESSAGES),
                *messages[:-1],
                AIMessage(content="I cannot share confidential information.")
            ]
        }

    return {}

agent = create_agent(
    model,
    tools=tools,
    post_model_hook=validate_response
)
```

#### Streaming

Show intermediate progress during multi-step execution:

```python
for chunk in agent.stream({
    "messages": [{"role": "user", "content": "Search for AI news and summarize the findings"}]
}, stream_mode="values"):
    # Each chunk contains the full state at that point
    latest_message = chunk["messages"][-1]
    if latest_message.content:
        print(f"Agent: {latest_message.content}")
    elif latest_message.tool_calls:
        print(f"Calling tools: {[tc['name'] for tc in latest_message.tool_calls]}")
```

See [Streaming](https://docs.langchain.com/oss/python/langchain/streaming) for details.

### Prebuilt Agents (from v1.0 Release Notes)

#### ReAct Agent Migration

**`create_react_agent` moved from `langgraph.prebuilts` to `langchain.agents`** with enhancements:

##### Enhanced Structured Output

Improved coercion to structured data types:

```python
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

class Weather(BaseModel):
    temperature: float
    condition: str

def weather_tool(city: str) -> str:
    """Get the weather for a city."""
    return f"it's sunny and 70 degrees in {city}"

agent = create_agent(
    "openai:gpt-4o-mini",
    tools=[weather_tool],
    response_format=Weather
)
result = agent.invoke({"messages": [HumanMessage("What's the weather in SF?")]})
print(repr(result["structured_response"]))
#> Weather(temperature=70.0, condition='sunny')
```

##### Structural Improvements

- **Main loop integration**: Structured output generated in main loop (no additional LLM call)
- **Tool/output choice**: Models can choose between calling tools, generating structured output, or both
- **Cost reduction**: Eliminates extra expense from additional LLM calls

##### Advanced Configuration

Two strategies for structured output:

1. **Artificial tool calling** (default)
   - LangChain generates tools matching response format schema
   - Model calls these tools, LangChain coerces args to desired format
   - Configure with `ToolStrategy` hint

2. **Provider implementations**
   - Uses native structured output support when available
   - Configure with `ProviderStrategy` hint

**Prompted output** no longer supported via `response_format` argument.

##### Error Handling

**Structured output errors:**
- Control via `handle_errors` arg to `ToolStrategy`
- **Parsing errors**: Model generates data not matching desired structure
- **Multiple tool calls**: Model generates 2+ tool calls for structured output schemas

**Tool calling errors:**
- **Invocation failure**: Agent returns artificial `ToolMessage` asking model to retry (unchanged)
- **Execution failure**: Agent raises `ToolException` by default (prevents infinite loops)
- Configure via `handle_tool_errors` arg to `ToolNode`

##### Breaking Changes

**Pre-bound models:**
`create_agent` no longer supports pre-bound models with tools or configuration:

```python
# No longer supported
model_with_tools = ChatOpenAI().bind_tools([some_tool])
agent = create_agent(model_with_tools, tools=[])

# Use instead
agent = create_agent("openai:gpt-4o-mini", tools=[some_tool])
```

Dynamic model functions can return pre-bound models if structured output is NOT used.

**Import changes:**

```python
# Before
from langgraph.prebuilts import create_agent, ToolNode, AgentState

# After
from langchain.agents import create_agent, ToolNode, AgentState
```

---

## Models

**Note:** The Models documentation page was rate-limited during scraping. This section will be completed when access is restored.

---

## Messages

**Note:** The Messages documentation page was rate-limited during scraping. This section will be completed when access is restored.

---

## Tools

**Note:** The Tools documentation page was rate-limited during scraping. This section will be completed when access is restored.

---

## Short-Term Memory

**Note:** The Short-Term Memory documentation page was rate-limited during scraping. This section will be completed when access is restored.

---

## Streaming

**Note:** The Streaming documentation page was rate-limited during scraping. This section will be completed when access is restored.

---

## Reporting Issues

Please report any issues discovered with 1.0 on [GitHub](https://github.com/langchain-ai/langchain/issues) using the [`'v1'` label](https://github.com/langchain-ai/langchain/issues?q=state%3Aopen%20label%3Av1).

## See Also

- [Versioning](https://docs.langchain.com/oss/python/versioning) - Understanding version numbers
- [Release policy](https://docs.langchain.com/oss/python/release-policy) - Detailed release policies

---

**Document Status:** Partial - Awaiting rate limit reset to complete Models, Messages, Tools, Short-Term Memory, and Streaming sections.
