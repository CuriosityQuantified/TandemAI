# LangChain Deep Agents Implementation Guide

**Document Version:** 1.0
**Last Updated:** October 1, 2025
**Author:** Research Documentation
**Repository:** https://github.com/langchain-ai/deepagents

---

## Table of Contents

1. [Overview](#overview)
2. [What Are Deep Agents?](#what-are-deep-agents)
3. [Key Features](#key-features)
4. [Installation](#installation)
5. [Architecture Components](#architecture-components)
6. [Quick Start](#quick-start)
7. [Configuration Options](#configuration-options)
8. [Built-in Components](#built-in-components)
9. [Advanced Usage](#advanced-usage)
10. [Code Examples](#code-examples)
11. [Dependencies](#dependencies)
12. [Best Practices](#best-practices)

---

## Overview

**Deep Agents** is a Python package (also available in JavaScript/TypeScript) that implements sophisticated agent architectures inspired by applications like "Deep Research", "Manus", and "Claude Code". Unlike simple LLM tool-calling loops, Deep Agents can plan and execute complex, multi-step tasks through a combination of planning tools, sub-agents, virtual file systems, and detailed prompts.

**License:** MIT
**GitHub Stars:** 4k+
**Primary Implementation:** Python (with JavaScript/TypeScript port available)

---

## What Are Deep Agents?

### The Problem with "Shallow" Agents

Using an LLM to call tools in a loop is the simplest form of an agent. However, this architecture yields agents that are "shallow" and fail to plan and act over longer, more complex tasks.

### The Deep Agent Solution

Deep Agents solve this limitation by implementing four key components:

1. **Planning Tool** - Enables task decomposition and long-term planning
2. **Sub-agents** - Specialized agents for specific tasks with context isolation
3. **Virtual File System** - Persistent state management across tool calls
4. **Detailed System Prompt** - Proven patterns from Claude Code for effective agent behavior

---

## Key Features

### Core Capabilities

- **Planning Tool**: Built-in planning capabilities to break down complex tasks and enable long-term planning
- **Persistent State**: Memory between tool calls beyond conversation history
- **Sub-agents**: Specialized agents for specific tasks with context quarantine
- **Virtual File System**: Mock file system for persistent state without conflicts
- **Detailed System Prompt**: Prompts heavily inspired by Claude Code that leverage proven patterns
- **Human-in-the-Loop**: Built-in support for tool approval workflows
- **MCP Integration**: Compatible with Model Context Protocol tools via LangChain MCP adapters
- **Async Support**: Full async/await support for asynchronous tools

### Supported Platforms

- **Python**: `pip install deepagents`
- **JavaScript/TypeScript**: `npm install deepagents` or `yarn add deepagents`

---

## Installation

### Python Installation

```bash
pip install deepagents
```

### JavaScript/TypeScript Installation

```bash
# Using npm
npm install deepagents

# Using yarn
yarn add deepagents
```

### Prerequisites

For the examples in this guide, you may need:

```bash
pip install tavily-python  # For web search functionality
pip install langchain langchain-openai  # For custom models
pip install langchain-mcp-adapters  # For MCP tool integration
```

---

## Architecture Components

### 1. System Prompt

Deep Agents includes a sophisticated system prompt heavily inspired by Claude Code's architecture. This prompt provides:

- Detailed instructions for using the planning tool
- Guidelines for file system operations
- Sub-agent coordination patterns
- Task decomposition strategies

**Note:** The system prompt is [built into the library](https://github.com/langchain-ai/deepagents/blob/master/src/deepagents/prompts.py) and combines with your custom instructions.

### 2. Planning Tool

Based on Claude Code's `TodoWrite` functionality:

- Simple interface for plan creation
- Does not execute actions - serves as a planning aid
- Keeps plans in context to maintain agent focus
- Helps with long-term task tracking

### 3. Virtual File System

Four built-in tools that mock a file system using LangGraph's state:

- `ls` - List files and directories
- `read_file` - Read file contents
- `write_file` - Write new files
- `edit_file` - Modify existing files

**Key Benefits:**
- No actual file system access required
- Multiple agents can run without conflicts
- Files persist in LangGraph state
- Simple one-level directory structure

### 4. Sub-agents

Built-in capability for specialized sub-agents:

- **Context Quarantine**: Prevents main agent context pollution
- **Custom Instructions**: Tailored prompts for specific tasks
- **Tool Access Control**: Different tool sets per sub-agent
- **General-Purpose Agent**: Always available with main agent's tools and instructions

---

## Quick Start

### Basic Research Agent (Python)

```python
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

# Initialize search client
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Define search tool
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

# Define instructions
research_instructions = """You are an expert researcher. Your job is to conduct thorough research, and then write a polished report.

You have access to a few tools.

## `internet_search`

Use this to run an internet search for a given query. You can specify the number of results, the topic, and whether raw content should be included.
"""

# Create agent
agent = create_deep_agent(
    tools=[internet_search],
    instructions=research_instructions,
)

# Invoke agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "what is langgraph?"}]
})
```

### Basic Research Agent (JavaScript)

```javascript
import { TavilyClient } from 'tavily';
import { createDeepAgent } from 'deepagents';

const tavilyClient = new TavilyClient(process.env.TAVILY_API_KEY);

function internetSearch(query) {
    return tavilyClient.search(query);
}

const researchInstructions = `You are an expert researcher.
Your job is to conduct thorough research, and then write a polished report.

You have access to tools for internet search and file operations.
`;

const agent = createDeepAgent({
    tools: [internetSearch],
    instructions: researchInstructions
});

const result = await agent.invoke({
    messages: [{ role: "user", content: "what is langgraph?" }]
});
```

---

## Configuration Options

### Required Parameters

#### 1. `tools` (Required)

List of functions or LangChain `@tool` objects that the agent and sub-agents can access.

```python
tools = [internet_search, custom_tool_1, custom_tool_2]
```

#### 2. `instructions` (Required)

Custom instructions that supplement the built-in system prompt.

```python
instructions = """You are an expert researcher.
Your job is to conduct thorough research and write polished reports.
"""
```

### Optional Parameters

#### 3. `subagents` (Optional)

Define specialized sub-agents for specific tasks.

**SubAgent Schema:**

```python
class SubAgent(TypedDict):
    name: str                              # Subagent name
    description: str                       # Description shown to main agent
    prompt: str                           # Subagent's prompt
    tools: NotRequired[list[str]]         # Optional: defaults to all tools
    model: NotRequired[Union[LanguageModelLike, dict[str, Any]]]  # Optional: custom model
    middleware: NotRequired[list[AgentMiddleware]]  # Optional: additional middleware
```

**CustomSubAgent Schema:**

```python
class CustomSubAgent(TypedDict):
    name: str                  # Subagent name
    description: str           # Description shown to main agent
    graph: Runnable           # Pre-built LangGraph graph
```

**Example - SubAgent:**

```python
research_subagent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions",
    "prompt": "You are a dedicated researcher. Conduct thorough research and reply with detailed answers.",
    "tools": ["internet_search"]  # Optional: specific tools only
}

subagents = [research_subagent]
agent = create_deep_agent(
    tools=tools,
    instructions=instructions,
    subagents=subagents
)
```

**Example - CustomSubAgent:**

```python
from langchain.agents import create_agent

# Create custom agent graph
custom_graph = create_agent(
    model=your_model,
    tools=specialized_tools,
    prompt="You are a specialized agent for data analysis..."
)

# Use as custom subagent
custom_subagent = {
    "name": "data-analyzer",
    "description": "Specialized agent for complex data analysis tasks",
    "graph": custom_graph
}

subagents = [custom_subagent]
agent = create_deep_agent(
    tools=tools,
    instructions=instructions,
    subagents=subagents
)
```

#### 4. `model` (Optional)

Default model: `"claude-sonnet-4-20250514"`

**Custom Model Example (Python only):**

```python
from langchain_openai import ChatOpenAI

custom_model = ChatOpenAI(model="gpt-4")
agent = create_deep_agent(
    tools=tools,
    instructions=instructions,
    model=custom_model
)
```

**Ollama Example:**

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    model="ollama:gpt-oss:20b",
)
agent = create_deep_agent(
    tools=tools,
    instructions=instructions,
    model=model
)
```

**Per-Subagent Model Override:**

```python
critique_subagent = {
    "name": "critique-agent",
    "description": "Critique the final report",
    "prompt": "You are a tough editor.",
    "model": {
        "model": "anthropic:claude-3-5-haiku-20241022",
        "temperature": 0,
        "max_tokens": 8192
    }
}

agent = create_deep_agent(
    tools=[internet_search],
    instructions="You are an expert researcher...",
    model="claude-sonnet-4-20250514",  # Default for main agent
    subagents=[critique_subagent],
)
```

#### 5. `middleware` (Optional)

Add custom AgentMiddleware for extending functionality:

- State schema extensions
- Additional tools
- Pre/post model hooks

See [LangChain Middleware documentation](https://docs.langchain.com/oss/python/langchain/middleware) for details.

#### 6. `tool_configs` (Optional)

Configure Human-in-the-Loop interactions for specific tools.

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_deep_agent(
    tools=[your_tools],
    instructions="Your instructions here",
    tool_configs={
        # Fine-grained control
        "tool_1": {
            "allow_respond": True,
            "allow_edit": True,
            "allow_accept": True,
        },
        # Boolean shortcut (enables all options)
        "tool_2": True,
    }
)

checkpointer = InMemorySaver()
agent.checkpointer = checkpointer
```

---

## Built-in Components

### Default Built-in Tools

Every Deep Agent comes with five built-in tools:

1. **`write_todos`** - Tool for writing todos/plans
2. **`write_file`** - Write to virtual filesystem
3. **`read_file`** - Read from virtual filesystem
4. **`ls`** - List files in virtual filesystem
5. **`edit_file`** - Edit files in virtual filesystem

### File System Usage

**Passing Files to Agent:**

```python
agent = create_deep_agent(...)

result = agent.invoke({
    "messages": [...],
    "files": {"foo.txt": "file content", "data.json": "{}"}
})

# Access files after execution
updated_files = result["files"]
```

### Context Quarantine with Sub-agents

Sub-agents provide "context quarantine" to prevent polluting the main agent's context:

- Main agent's context remains clean
- Sub-agents work in isolated context
- Results are returned to main agent
- Useful for complex multi-step research

---

## Advanced Usage

### Human-in-the-Loop Workflows

Deep Agents supports three HITL patterns:

#### 1. Approve

Execute the tool call as proposed:

```python
config = {"configurable": {"thread_id": "1"}}

# Initial call
for s in agent.stream({"messages": [{"role": "user", "content": message}]}, config=config):
    print(s)

# Approve tool execution
for s in agent.stream(Command(resume=[{"type": "accept"}]), config=config):
    print(s)
```

#### 2. Edit

Modify tool call before execution:

```python
config = {"configurable": {"thread_id": "1"}}

# Initial call
for s in agent.stream({"messages": [{"role": "user", "content": message}]}, config=config):
    print(s)

# Edit and execute
for s in agent.stream(
    Command(resume=[{
        "type": "edit",
        "args": {
            "action": "tool_name",
            "args": {"param1": "value1", "param2": "value2"}
        }
    }]),
    config=config
):
    print(s)
```

#### 3. Respond

Reject tool call with feedback:

```python
config = {"configurable": {"thread_id": "1"}}

# Initial call
for s in agent.stream({"messages": [{"role": "user", "content": message}]}, config=config):
    print(s)

# Respond with feedback
for s in agent.stream(
    Command(resume=[{
        "type": "response",
        "args": "Please use a different approach because..."
    }]),
    config=config
):
    print(s)
```

**Requirements:**
- Checkpointer must be attached (automatic in LangGraph Platform)
- Tool must be configured in `tool_configs`

### Async Operations

For async tools, use the async version:

```python
from deepagents import async_create_deep_agent

async def async_search(query: str):
    # Async search implementation
    ...

agent = async_create_deep_agent(
    tools=[async_search],
    instructions=instructions
)

# Stream results
async for chunk in agent.astream(
    {"messages": [{"role": "user", "content": "what is langgraph?"}]},
    stream_mode="values"
):
    if "messages" in chunk:
        chunk["messages"][-1].pretty_print()
```

### MCP (Model Context Protocol) Integration

Deep Agents can use MCP tools via the LangChain MCP Adapters library:

```python
# pip install langchain-mcp-adapters

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from deepagents import async_create_deep_agent

async def main():
    # Collect MCP tools
    mcp_client = MultiServerMCPClient(...)
    mcp_tools = await mcp_client.get_tools()

    # Create agent with MCP tools
    agent = async_create_deep_agent(
        tools=mcp_tools,
        instructions="Your instructions here"
    )

    # Stream the agent
    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": "what is langgraph?"}]},
        stream_mode="values"
    ):
        if "messages" in chunk:
            chunk["messages"][-1].pretty_print()

asyncio.run(main())
```

**Note:** MCP tools are async, so you must use `async_create_deep_agent`.

---

## Code Examples

### Complete Research Agent with Sub-agents

```python
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

# Initialize Tavily client
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Internet search tool
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

# Sub-agent: Research specialist
sub_research_prompt = """You are a dedicated researcher. Your job is to conduct research based on the users questions.

Conduct thorough research and then reply to the user with a detailed answer to their question.

Only your FINAL answer will be passed on to the user."""

research_sub_agent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions.",
    "prompt": sub_research_prompt,
    "tools": [internet_search],
}

# Sub-agent: Editor/Critic
sub_critique_prompt = """You are a dedicated editor. You are being tasked to critique a report.

You can find the report at `final_report.md`.

You can find the question/topic for this report at `question.txt`."""

critique_sub_agent = {
    "name": "critique-agent",
    "description": "Used to critique the final report.",
    "prompt": sub_critique_prompt,
}

# Main agent instructions
research_instructions = """You are an expert researcher. Your job is to conduct thorough research, and then write a polished report."""

# Create the agent
agent = create_deep_agent(
    tools=[internet_search],
    instructions=research_instructions,
    subagents=[critique_sub_agent, research_sub_agent],
)

# Use the agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "Research the latest developments in quantum computing"}]
})
```

### Streaming Agent Output

```python
agent = create_deep_agent(...)

# Stream with detailed output
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Research quantum computing"}]},
    stream_mode="values"
):
    if "messages" in chunk:
        chunk["messages"][-1].pretty_print()
```

### Working with Files

```python
agent = create_deep_agent(...)

# Pass initial files
result = agent.invoke({
    "messages": [{"role": "user", "content": "Summarize the data"}],
    "files": {
        "data.csv": "col1,col2\n1,2\n3,4",
        "instructions.txt": "Focus on trends"
    }
})

# Access updated files
for filename, content in result["files"].items():
    print(f"{filename}: {len(content)} bytes")
```

---

## Dependencies

### Python Dependencies

**Core Requirements:**
```
deepagents>=0.1.0
langchain>=0.3.0
langgraph>=0.2.0
```

**Optional Dependencies:**
```
tavily-python  # For web search
langchain-openai  # For OpenAI models
langchain-anthropic  # For Anthropic models
langchain-mcp-adapters  # For MCP integration
langgraph.checkpoint.memory  # For HITL checkpointing
```

### JavaScript Dependencies

```json
{
  "dependencies": {
    "deepagents": "^0.1.0",
    "@langchain/core": "^0.3.0",
    "@langchain/langgraph": "^0.2.0"
  }
}
```

---

## Best Practices

### 1. Instruction Design

**Do:**
- Be specific about the agent's role and responsibilities
- Describe available tools and when to use them
- Provide examples of desired outputs
- Set clear success criteria

**Don't:**
- Leave instructions vague or overly generic
- Assume the agent knows implicit requirements
- Combine too many unrelated responsibilities

### 2. Tool Organization

**Do:**
- Group related functionality into single tools
- Provide clear, descriptive tool names
- Include detailed docstrings for each tool
- Use type hints for tool parameters

**Don't:**
- Create overlapping tool functionality
- Use ambiguous tool names
- Provide tools without clear documentation

### 3. Sub-agent Strategy

**When to use sub-agents:**
- Tasks requiring specialized instructions
- Operations that need context isolation
- Multi-step workflows with distinct phases
- When main context is getting too large

**Sub-agent design:**
- Give each sub-agent a clear, focused purpose
- Limit sub-agent tool access to only what's needed
- Write instructions specific to the sub-agent's role
- Consider using different models for different sub-agents

### 4. File System Usage

**Best practices:**
- Use descriptive filenames
- Organize related content in separate files
- Read files before editing them
- Use the planning tool to track file operations

### 5. Human-in-the-Loop Configuration

**Recommendations:**
- Enable HITL for destructive operations
- Enable HITL for high-cost operations
- Allow all three interaction types (accept, edit, respond)
- Provide clear feedback in "respond" messages
- Always attach a checkpointer when using HITL

### 6. Model Selection

**Considerations:**
- Use powerful models (GPT-4, Claude Sonnet) for main agent
- Consider faster/cheaper models for simple sub-agents
- Use deterministic models (temperature=0) for critique agents
- Match model capabilities to task complexity

### 7. Testing and Debugging

**Strategies:**
- Start with simple tasks before complex ones
- Use streaming to observe agent reasoning
- Check file state after each run
- Monitor tool call patterns
- Test edge cases and failure modes

---

## Acknowledgements

This project was primarily inspired by **Claude Code** and represents an attempt to understand what makes Claude Code effective and extend those patterns in a general-purpose way.

**Key Inspirations:**
- Claude Code's TodoWrite planning tool
- Claude Code's system prompt architecture
- Context quarantine patterns from "Deep Research"
- Multi-agent orchestration from "Manus"

---

## Additional Resources

- **GitHub Repository:** https://github.com/langchain-ai/deepagents
- **LangChain Documentation:** https://docs.langchain.com/labs/deep-agents/overview
- **LangChain Academy Course:** [Deep Agents with LangGraph](https://academy.langchain.com/courses/deep-agents-with-langgraph/)
- **LangChain Middleware:** https://docs.langchain.com/oss/python/langchain/middleware
- **LangGraph Documentation:** https://docs.langchain.com/langgraph
- **MCP Adapters:** https://github.com/langchain-ai/langchain-mcp-adapters

---

## Roadmap

The Deep Agents project has the following items on its roadmap:

- [ ] Allow users to customize full system prompt
- [ ] Code cleanliness improvements (type hinting, docstrings, formatting)
- [ ] More robust virtual filesystem with subdirectories
- [ ] Example of a deep coding agent built on this framework
- [ ] Benchmark the research agent example
- [ ] Additional middleware components for common patterns
- [ ] Enhanced file system capabilities
- [ ] More sophisticated planning tools

---

**End of Document**
