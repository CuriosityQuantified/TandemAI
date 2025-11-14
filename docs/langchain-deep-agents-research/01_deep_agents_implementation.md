# LangChain Deep Agents Implementation Guide for ATLAS

**Research Date:** October 1, 2025
**Target Framework:** LangChain Deep Agents + LangGraph
**Purpose:** Multi-agent orchestration for ATLAS supervisor and sub-agent architecture

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Core Concepts](#core-concepts)
4. [Installation & Setup](#installation--setup)
5. [Implementation Patterns](#implementation-patterns)
6. [ATLAS Integration Strategy](#atlas-integration-strategy)
7. [Code Examples](#code-examples)
8. [State Management & Memory](#state-management--memory)
9. [Best Practices](#best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [References](#references)

---

## Executive Summary

### What Are Deep Agents?

**Deep Agents** are advanced AI agent architectures that overcome the limitations of "shallow" agents (simple tool-calling loops). They implement four key components inspired by systems like Claude Code:

1. **Planning Tool** - Strategic task decomposition and tracking
2. **Sub-Agents** - Specialized agents with context isolation
3. **File System** - Virtual file system for persistent state
4. **Detailed System Prompt** - Sophisticated behavior guidance

### Why Deep Agents for ATLAS?

Deep Agents align perfectly with ATLAS's hierarchical multi-agent architecture:

- **Hierarchical Structure**: Supervisor → Team Supervisors → Worker Agents
- **Task Delegation**: Built-in sub-agent spawning with context quarantine
- **State Management**: Virtual file system + LangGraph checkpointing
- **Planning Capabilities**: Native TODO list and task tracking
- **Memory Persistence**: Cross-session memory with store integrations

### Key Differentiators from Standard Agents

| Feature | Standard Agents | Deep Agents |
|---------|----------------|-------------|
| Task Planning | Limited or none | Built-in TODO list system |
| Sub-Agents | Manual coordination | Native sub-agent spawning |
| State Persistence | External implementation | Virtual file system + checkpointers |
| Context Management | All in main prompt | Context quarantine per sub-agent |
| Memory | Session-only | Cross-session via stores |
| System Prompt | Basic instructions | Claude Code-inspired sophistication |

---

## Architecture Overview

### Deep Agents Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                    DEEP AGENT SYSTEM                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         DETAILED SYSTEM PROMPT                     │    │
│  │  - Agent behavior guidelines                       │    │
│  │  - Tool usage patterns                             │    │
│  │  - Sub-agent delegation rules                      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         PLANNING TOOL (TodoWrite)                  │    │
│  │  - Task decomposition                              │    │
│  │  - Status tracking (pending/in-progress/completed) │    │
│  │  - Dependency management                           │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         VIRTUAL FILE SYSTEM                        │    │
│  │  - ls() - List files/directories                   │    │
│  │  - read_file() - Read file contents                │    │
│  │  - write_file() - Create/overwrite files           │    │
│  │  - edit_file() - Modify existing files             │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         SUB-AGENTS                                 │    │
│  │  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │ Research     │  │ Analysis     │               │    │
│  │  │ Sub-Agent    │  │ Sub-Agent    │               │    │
│  │  │ - Custom     │  │ - Custom     │   ...more     │    │
│  │  │   prompt     │  │   prompt     │               │    │
│  │  │ - Specific   │  │ - Specific   │               │    │
│  │  │   tools      │  │   tools      │               │    │
│  │  │ - Context    │  │ - Context    │               │    │
│  │  │   isolation  │  │   isolation  │               │    │
│  │  └──────────────┘  └──────────────┘               │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### LangGraph State Graph Integration

Deep Agents are built on **LangGraph**, which provides:

- **State Graphs**: Define agent workflows as directed graphs
- **Checkpointing**: Automatic state persistence at every step
- **Memory Stores**: Cross-session memory storage
- **Command System**: Control flow between agents

```
┌─────────────────────────────────────────────────────────────┐
│                    LANGGRAPH LAYER                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  StateGraph (MessagesState)                                 │
│  ├─ supervisor_node (main agent)                            │
│  │   └─ Has access to handoff tools                         │
│  ├─ research_agent_node (sub-agent)                         │
│  │   └─ Returns to supervisor after completion              │
│  ├─ analysis_agent_node (sub-agent)                         │
│  │   └─ Returns to supervisor after completion              │
│  └─ writing_agent_node (sub-agent)                          │
│      └─ Returns to supervisor after completion              │
│                                                              │
│  Checkpointer: PostgresSaver (state persistence)            │
│  Memory Store: RedisStore/MongoDBStore (cross-session)      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Concepts

### 1. Planning Tool (TodoWrite Pattern)

Deep Agents include a built-in planning tool based on the TodoWrite pattern that allows agents to:

- **Decompose complex tasks** into manageable subtasks
- **Track status** (pending → in_progress → completed/failed)
- **Manage dependencies** between tasks
- **Update plans** dynamically based on execution feedback

**Implementation Pattern:**

```python
# The planning tool is automatically included in Deep Agents
# Agents can create and update TODO lists in their context

# Example agent usage (internal to agent):
# 1. User requests: "Write a research report on quantum computing"
# 2. Agent creates TODO:
#    - [ ] Research quantum computing basics (pending)
#    - [ ] Research quantum computing applications (pending)
#    - [ ] Analyze findings (pending)
#    - [ ] Write report outline (pending)
#    - [ ] Write full report (pending)
# 3. Agent updates status as it progresses:
#    - [x] Research quantum computing basics (completed)
#    - [→] Research quantum computing applications (in_progress)
#    - [ ] Analyze findings (pending)
#    - [ ] Write report outline (pending)
#    - [ ] Write full report (pending)
```

### 2. Sub-Agents with Context Quarantine

Sub-agents are specialized agents that:

- **Have their own prompts** tailored to specific tasks
- **Access specific tools** relevant to their domain
- **Operate in isolated context** to prevent interference
- **Can have custom models** (e.g., faster models for simple tasks)
- **Return results** to the parent supervisor agent

**Key Benefits:**
- **Context Isolation**: Prevents sub-agent context from overwhelming main agent
- **Specialization**: Each sub-agent can be optimized for its task
- **Parallel Execution**: Multiple sub-agents can work simultaneously
- **Cost Optimization**: Use cheaper/faster models for routine sub-tasks

**Sub-Agent Structure:**

```python
subagent_config = {
    "name": "research-agent",
    "description": "Used to research in-depth questions",
    "prompt": "You are an expert researcher...",
    "tools": [internet_search, web_scrape],
    "model": "gpt-4o-mini"  # Optional: use faster/cheaper model
}
```

### 3. Virtual File System

Deep Agents include a virtual file system stored in the agent's state, providing:

- **Persistent storage** across conversation turns
- **File operations**: ls, read_file, write_file, edit_file
- **Context offloading**: Store large documents without overwhelming context
- **Artifact management**: Save generated content for later retrieval

**File System Operations:**

```python
# Built-in tools available to all agents:
# - ls() - List files and directories
# - read_file(path) - Read file contents
# - write_file(path, content) - Create or overwrite file
# - edit_file(path, changes) - Modify existing file
```

### 4. Detailed System Prompt

Deep Agents use a sophisticated system prompt inspired by Claude Code that:

- **Guides tool usage** with clear patterns and examples
- **Explains sub-agent delegation** when and how to use sub-agents
- **Provides planning strategies** for complex tasks
- **Establishes communication protocols** between agents

---

## Installation & Setup

### Prerequisites

- **Python**: 3.11 or higher (recommended: 3.12)
- **Package Manager**: `uv` (recommended) or `pip`
- **API Keys**:
  - Anthropic API key (default model: Claude Sonnet 4)
  - Optional: LangSmith API key (for tracing and debugging)

### Installation Steps

#### 1. Install Deep Agents

```bash
# Using uv (recommended for ATLAS)
uv pip install deepagents

# Or using pip
pip install deepagents
```

#### 2. Install LangGraph Checkpointer (for production)

```bash
# PostgreSQL checkpointer (recommended for ATLAS)
uv pip install langgraph-checkpoint-postgres

# Alternative: Redis checkpointer
uv pip install langgraph-checkpoint-redis

# Alternative: MongoDB checkpointer
uv pip install pymongo langgraph-checkpoint-mongodb
```

#### 3. Install Memory Store (for cross-session memory)

```bash
# Redis store (recommended for ATLAS)
uv pip install langgraph-store-redis

# Alternative: MongoDB store
uv pip install langgraph-store-mongodb
```

#### 4. Set Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Optional (for tracing)
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY="your-langsmith-api-key"

# For checkpointers/stores
export POSTGRES_URL="postgresql://user:pass@localhost:5432/atlas_agents"
export REDIS_URL="redis://localhost:6379"
```

### Verification

```python
# Test basic Deep Agent creation
from deepagents import create_deep_agent

def test_tool():
    """A simple test tool"""
    return "Tool executed successfully"

agent = create_deep_agent(
    tools=[test_tool],
    instructions="You are a test agent"
)

# Test invocation
result = agent.invoke({
    "messages": [{"role": "user", "content": "Test the tool"}]
})

print(result)
```

---

## Implementation Patterns

### Pattern 1: Simple Deep Agent (No Sub-Agents)

**Use Case**: Single agent with planning and file system capabilities

```python
from deepagents import create_deep_agent
from langchain_core.tools import tool

@tool
def research_tool(query: str) -> str:
    """Research information about a topic"""
    # Implementation
    return f"Research results for: {query}"

@tool
def analysis_tool(data: str) -> str:
    """Analyze data and provide insights"""
    # Implementation
    return f"Analysis of: {data}"

# Create agent with tools
agent = create_deep_agent(
    tools=[research_tool, analysis_tool],
    instructions="""You are an expert analyst.

    When given a task:
    1. Use the planning tool to break it into steps
    2. Execute research and analysis in sequence
    3. Save results to files using the file system
    4. Provide final summary
    """
)

# Use the agent
response = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze the impact of AI on healthcare"}]
})
```

### Pattern 2: Hierarchical Agent (Supervisor + Sub-Agents)

**Use Case**: ATLAS architecture with supervisor delegating to specialized agents

```python
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic

# Define sub-agent configurations
research_subagent = {
    "name": "research-agent",
    "description": "Conducts in-depth research on topics",
    "prompt": """You are an expert researcher.

    Your responsibilities:
    - Search the web for reliable information
    - Evaluate source credibility
    - Synthesize findings into clear summaries
    - Cite all sources

    Always save your research notes to files.
    """,
    "tools": [internet_search, web_scrape],
    "model": ChatAnthropic(model="claude-sonnet-4-20250514")
}

analysis_subagent = {
    "name": "analysis-agent",
    "description": "Analyzes data and provides insights",
    "prompt": """You are an expert data analyst.

    Your responsibilities:
    - Load data from files
    - Perform quantitative and qualitative analysis
    - Identify patterns and trends
    - Generate visualizations if needed

    Save all analysis results to files.
    """,
    "tools": [code_executor, data_visualizer],
    "model": ChatAnthropic(model="claude-sonnet-4-20250514")
}

writing_subagent = {
    "name": "writing-agent",
    "description": "Creates polished written content",
    "prompt": """You are an expert technical writer.

    Your responsibilities:
    - Read research and analysis from files
    - Structure content logically
    - Write clear, engaging prose
    - Format for the target audience

    Save drafts and final versions to files.
    """,
    "tools": [formatting_tool, style_checker],
    "model": ChatAnthropic(model="claude-sonnet-4-20250514")
}

# Create supervisor agent with sub-agents
supervisor = create_deep_agent(
    tools=[internet_search, code_executor, formatting_tool],
    instructions="""You are the ATLAS Supervisor Agent.

    Your role is to coordinate complex projects by:
    1. Breaking down requests into clear tasks
    2. Delegating to specialized sub-agents:
       - research-agent: For information gathering
       - analysis-agent: For data analysis and insights
       - writing-agent: For content creation
    3. Monitoring progress and ensuring quality
    4. Synthesizing results into final deliverables

    Always:
    - Create a detailed plan using the TODO tool
    - Delegate work to the most appropriate sub-agent
    - Use the file system to pass information between sub-agents
    - Review sub-agent outputs for quality
    - Provide comprehensive final summaries
    """,
    subagents=[research_subagent, analysis_subagent, writing_subagent]
)

# Use the supervisor
response = supervisor.invoke({
    "messages": [{"role": "user", "content": "Create a comprehensive report on AI in healthcare"}]
})
```

### Pattern 3: Async Deep Agent (For Concurrent Operations)

**Use Case**: When using async tools or needing concurrent sub-agent execution

```python
from deepagents import async_create_deep_agent
import asyncio

@tool
async def async_web_search(query: str) -> str:
    """Asynchronously search the web"""
    # Async implementation
    await asyncio.sleep(1)  # Simulate API call
    return f"Search results for: {query}"

@tool
async def async_code_executor(code: str) -> str:
    """Asynchronously execute code"""
    # Async implementation
    await asyncio.sleep(2)  # Simulate execution
    return f"Execution result: {code}"

# Create async agent
async_agent = await async_create_deep_agent(
    tools=[async_web_search, async_code_executor],
    instructions="You are an async agent capable of concurrent operations"
)

# Use the async agent
async def run_agent():
    response = await async_agent.ainvoke({
        "messages": [{"role": "user", "content": "Research and analyze simultaneously"}]
    })
    return response

# Run
result = asyncio.run(run_agent())
```

### Pattern 4: Multi-Agent Supervisor with LangGraph

**Use Case**: Explicit control over agent communication and state management

```python
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic

# Define state
class AgentState(MessagesState):
    next_agent: str
    final_answer: str

# Create specialized agents using create_react_agent
model = ChatAnthropic(model="claude-sonnet-4-20250514")

research_agent = create_react_agent(
    model,
    tools=[internet_search],
    state_modifier="You are a research specialist. Gather comprehensive information."
)

analysis_agent = create_react_agent(
    model,
    tools=[code_executor],
    state_modifier="You are an analysis specialist. Perform deep analysis."
)

writing_agent = create_react_agent(
    model,
    tools=[formatting_tool],
    state_modifier="You are a writing specialist. Create polished content."
)

# Create handoff tools
def create_handoff_tool(agent_name: str):
    """Create a tool to handoff to another agent"""
    @tool(name=f"transfer_to_{agent_name}")
    def handoff_tool() -> str:
        """Handoff task to another agent"""
        return f"Task transferred to {agent_name}"
    return handoff_tool

# Supervisor node
def supervisor_node(state: AgentState):
    """Supervisor decides which agent to call next"""
    messages = state["messages"]

    # Use LLM to decide next agent
    supervisor_prompt = f"""You are a supervisor coordinating specialized agents.

    Available agents:
    - research_agent: For information gathering
    - analysis_agent: For data analysis
    - writing_agent: For content creation
    - FINISH: When task is complete

    Based on the conversation, which agent should act next?
    Current messages: {messages[-3:]}

    Respond with ONLY the agent name or FINISH.
    """

    response = model.invoke(supervisor_prompt)
    next_agent = response.content.strip()

    return {"next_agent": next_agent}

# Build graph
def build_supervisor_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("research_agent", research_agent)
    graph.add_node("analysis_agent", analysis_agent)
    graph.add_node("writing_agent", writing_agent)

    # Add edges
    graph.add_edge(START, "supervisor")

    # Conditional edges from supervisor
    graph.add_conditional_edges(
        "supervisor",
        lambda x: x["next_agent"],
        {
            "research_agent": "research_agent",
            "analysis_agent": "analysis_agent",
            "writing_agent": "writing_agent",
            "FINISH": "__end__"
        }
    )

    # All agents return to supervisor
    graph.add_edge("research_agent", "supervisor")
    graph.add_edge("analysis_agent", "supervisor")
    graph.add_edge("writing_agent", "supervisor")

    return graph.compile()

# Use the graph
supervisor_graph = build_supervisor_graph()
result = supervisor_graph.invoke({
    "messages": [HumanMessage(content="Create a report on quantum computing")]
})
```

---

## ATLAS Integration Strategy

### Recommended Architecture for ATLAS

Based on Deep Agents patterns, here's the recommended architecture:

```
┌───────────────────────────────────────────────────────────────┐
│                    ATLAS SYSTEM                                │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────────────────────────────────────────┐     │
│  │         GLOBAL SUPERVISOR (Deep Agent)              │     │
│  │  - Receives user requests                           │     │
│  │  - Creates project plans (TODO tool)                │     │
│  │  - Delegates to sub-agents                          │     │
│  │  - Monitors progress                                │     │
│  │  - Synthesizes final outputs                        │     │
│  │                                                      │     │
│  │  Sub-agents:                                        │     │
│  │  ├─ research-agent (Firecrawl + web search)        │     │
│  │  ├─ analysis-agent (E2B code execution)            │     │
│  │  ├─ writing-agent (file operations)                │     │
│  │  └─ planning-agent (LLM task decomposition)        │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                                │
│  ┌─────────────────────────────────────────────────────┐     │
│  │         PERSISTENCE LAYER                            │     │
│  │  - PostgreSQL: Checkpointer (thread state)          │     │
│  │  - Redis: Memory store (cross-session)              │     │
│  │  - HelixDB: Knowledge graph (project relationships) │     │
│  │  - Local filesystem: Session outputs                │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                                │
│  ┌─────────────────────────────────────────────────────┐     │
│  │         OBSERVABILITY                                │     │
│  │  - MLflow: Tool call tracking                        │     │
│  │  - AG-UI: Real-time frontend updates                │     │
│  │  - LangSmith: Debugging and tracing (optional)       │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

### Implementation Phases

#### Phase 1: Convert Supervisor to Deep Agent

**Goal**: Replace custom Letta-based supervisor with Deep Agent

**Steps**:

1. **Create Deep Agent supervisor** with existing tools:
```python
from deepagents import create_deep_agent
from backend.src.tools import (
    planning_tool,
    todo_tool,
    file_operations,
    delegation_tools
)

# Define sub-agents for specialized tasks
research_subagent = {
    "name": "research-agent",
    "description": "Conducts web research using Firecrawl",
    "prompt": load_prompt("prompts/research_agent.yaml"),
    "tools": [firecrawl_search, web_scrape],
}

analysis_subagent = {
    "name": "analysis-agent",
    "description": "Executes code and performs analysis using E2B",
    "prompt": load_prompt("prompts/analysis_agent.yaml"),
    "tools": [e2b_execute_code, data_visualize],
}

writing_subagent = {
    "name": "writing-agent",
    "description": "Creates structured documents and reports",
    "prompt": load_prompt("prompts/writing_agent.yaml"),
    "tools": [file_write, file_edit, format_content],
}

# Create supervisor
atlas_supervisor = create_deep_agent(
    tools=[
        planning_tool,
        todo_tool,
        file_operations,
        firecrawl_search,
        e2b_execute_code,
        file_write
    ],
    instructions=load_prompt("prompts/global_supervisor.yaml"),
    subagents=[research_subagent, analysis_subagent, writing_subagent]
)
```

2. **Add PostgreSQL checkpointer** for state persistence:
```python
from langgraph.checkpoint.postgres import PostgresSaver

# Configure checkpointer
checkpointer = PostgresSaver.from_conn_string(
    conn_string=os.environ["POSTGRES_URL"]
)

# Compile agent with checkpointer
atlas_supervisor_with_checkpointing = atlas_supervisor.compile(
    checkpointer=checkpointer
)
```

3. **Add Redis memory store** for cross-session memory:
```python
from langgraph.store.redis import RedisStore

# Configure memory store
memory_store = RedisStore(
    redis_url=os.environ["REDIS_URL"]
)

# Use store in agent
atlas_supervisor_full = atlas_supervisor.compile(
    checkpointer=checkpointer,
    store=memory_store
)
```

#### Phase 2: Integrate with Existing ATLAS Infrastructure

**Goal**: Connect Deep Agent to existing AG-UI, MLflow, and frontend

**Steps**:

1. **Wrap Deep Agent in FastAPI endpoint**:
```python
from fastapi import FastAPI, WebSocket
from backend.src.agui.events import AGUIEventBroadcaster

app = FastAPI()

@app.post("/api/tasks")
async def create_task(request: TaskRequest):
    """Create new task and invoke supervisor"""

    # Create thread for this task
    thread_id = f"task_{request.task_id}"

    # Invoke agent with streaming
    async for chunk in atlas_supervisor_full.astream(
        {"messages": [{"role": "user", "content": request.prompt}]},
        config={"configurable": {"thread_id": thread_id}}
    ):
        # Broadcast updates via AG-UI
        await AGUIEventBroadcaster.broadcast_agent_update(chunk)

        # Log to MLflow
        mlflow_tracker.log_agent_action(chunk)

    return {"status": "completed", "thread_id": thread_id}
```

2. **Integrate with AG-UI real-time updates**:
```python
from backend.src.agui.server import AGUIServer

# Monitor agent state changes
def on_state_update(state):
    """Called when agent state changes"""
    AGUIEventBroadcaster.broadcast_event({
        "type": "agent_status_changed",
        "data": {
            "agent": state["current_agent"],
            "status": state["status"],
            "progress": state["progress"]
        }
    })

# Register callback
atlas_supervisor_full.register_callback(on_state_update)
```

3. **Add MLflow tracking for observability**:
```python
from backend.src.mlflow.enhanced_tracking import EnhancedATLASTracker

# Wrap agent invocations
class MLflowTrackedAgent:
    def __init__(self, agent, tracker):
        self.agent = agent
        self.tracker = tracker

    async def ainvoke(self, input, config):
        with self.tracker.track_agent_execution(
            agent_name="atlas_supervisor",
            task_type="deep_agent_invocation"
        ):
            result = await self.agent.ainvoke(input, config)

            # Log metrics
            self.tracker.log_metrics({
                "messages_exchanged": len(result["messages"]),
                "tools_called": count_tool_calls(result),
                "subagents_invoked": count_subagent_calls(result)
            })

            return result

# Use wrapped agent
tracked_supervisor = MLflowTrackedAgent(
    atlas_supervisor_full,
    enhanced_mlflow_tracker
)
```

#### Phase 3: Optimize Sub-Agent Delegation

**Goal**: Fine-tune sub-agent prompts and tool access

**Steps**:

1. **Refine sub-agent prompts** based on ATLAS requirements
2. **Optimize tool distribution** (which tools each sub-agent needs)
3. **Test parallel sub-agent execution** for performance gains
4. **Implement error handling** for sub-agent failures

#### Phase 4: Add Advanced Features

**Goal**: Leverage Deep Agents advanced capabilities

**Features to implement**:

1. **Human-in-the-loop (HITL)** for approval workflows:
```python
# Configure tools requiring approval
tool_configs = {
    "e2b_execute_code": {"require_approval": True},
    "firecrawl_search": {"require_approval": False}
}

atlas_supervisor_hitl = create_deep_agent(
    tools=[e2b_execute_code, firecrawl_search],
    instructions="...",
    tool_configs=tool_configs  # Enable HITL
)
```

2. **Multi-modal content handling** (images, audio, video)
3. **Cross-session memory** for user preferences
4. **Dynamic sub-agent creation** based on task requirements

---

## Code Examples

### Example 1: Basic Research Agent

```python
from deepagents import create_deep_agent
from langchain_core.tools import tool
from tavily import TavilyClient
import os

# Define research tool
@tool
def internet_search(query: str) -> str:
    """Search the internet for information"""
    tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    results = tavily_client.search(query)
    return str(results)

# Create agent
research_agent = create_deep_agent(
    tools=[internet_search],
    instructions="""You are an expert researcher.

    When given a research request:
    1. Create a plan using the TODO tool
    2. Break down the topic into specific questions
    3. Search for information on each question
    4. Save findings to files using the file system
    5. Synthesize a final summary

    Always cite sources and evaluate credibility.
    """
)

# Use the agent
response = research_agent.invoke({
    "messages": [{"role": "user", "content": "Research the current state of quantum computing"}]
})

print(response["messages"][-1]["content"])
```

### Example 2: Multi-Agent Coordinator

```python
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic

# Define sub-agents
data_collector = {
    "name": "data-collector",
    "description": "Collects data from various sources",
    "prompt": "You specialize in gathering data efficiently.",
    "tools": [web_scraper, api_caller]
}

data_analyzer = {
    "name": "data-analyzer",
    "description": "Analyzes collected data",
    "prompt": "You specialize in statistical analysis.",
    "tools": [code_executor, chart_generator]
}

report_writer = {
    "name": "report-writer",
    "description": "Writes comprehensive reports",
    "prompt": "You specialize in clear, professional writing.",
    "tools": [markdown_formatter, pdf_generator]
}

# Create coordinator
coordinator = create_deep_agent(
    tools=[web_scraper, api_caller, code_executor, markdown_formatter],
    instructions="""You are a project coordinator.

    Workflow:
    1. Analyze the request and create a detailed plan
    2. Delegate data collection to data-collector
    3. Pass collected data to data-analyzer
    4. Provide analysis results to report-writer
    5. Review final report for quality
    6. Deliver to user

    Ensure smooth handoffs between sub-agents using the file system.
    """,
    subagents=[data_collector, data_analyzer, report_writer]
)

# Execute multi-step project
result = coordinator.invoke({
    "messages": [{"role": "user", "content": "Analyze social media trends in healthcare"}]
})
```

### Example 3: ATLAS-Style Supervisor with Session Management

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.postgres import PostgresSaver
from pathlib import Path
import os

# Session management
def create_session_directory(task_id: str) -> Path:
    """Create session-specific directory"""
    session_dir = Path(f"/outputs/session_{task_id}")
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

# File operations bound to session
class SessionFileOperations:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir

    @tool
    def save_output(self, filename: str, content: str) -> str:
        """Save content to session directory"""
        filepath = self.session_dir / filename
        filepath.write_text(content)
        return f"Saved to {filepath}"

    @tool
    def load_file(self, filename: str) -> str:
        """Load file from session directory"""
        filepath = self.session_dir / filename
        return filepath.read_text()

    @tool
    def list_outputs(self) -> list:
        """List all files in session directory"""
        return [f.name for f in self.session_dir.iterdir()]

# Create ATLAS supervisor
def create_atlas_supervisor(task_id: str):
    # Setup session
    session_dir = create_session_directory(task_id)
    file_ops = SessionFileOperations(session_dir)

    # Define sub-agents
    research_sub = {
        "name": "research-agent",
        "description": "Web research specialist",
        "prompt": "You conduct thorough web research.",
        "tools": [firecrawl_search]
    }

    analysis_sub = {
        "name": "analysis-agent",
        "description": "Code execution and analysis specialist",
        "prompt": "You perform data analysis and code execution.",
        "tools": [e2b_execute]
    }

    writing_sub = {
        "name": "writing-agent",
        "description": "Content creation specialist",
        "prompt": "You create polished documents.",
        "tools": [file_ops.save_output]
    }

    # Create supervisor
    supervisor = create_deep_agent(
        tools=[
            file_ops.save_output,
            file_ops.load_file,
            file_ops.list_outputs,
            firecrawl_search,
            e2b_execute
        ],
        instructions=f"""You are the ATLAS Global Supervisor.

        Session: {task_id}
        Output Directory: {session_dir}

        Workflow:
        1. Analyze request and create detailed plan
        2. Delegate to appropriate sub-agents:
           - research-agent: For information gathering
           - analysis-agent: For computations and analysis
           - writing-agent: For document creation
        3. Use file system to pass data between sub-agents
        4. Monitor progress and quality
        5. Deliver final output to user

        All outputs must be saved to the session directory.
        """,
        subagents=[research_sub, analysis_sub, writing_sub]
    )

    # Add checkpointing
    checkpointer = PostgresSaver.from_conn_string(
        os.environ["POSTGRES_URL"]
    )

    return supervisor.compile(checkpointer=checkpointer)

# Use the supervisor
task_id = "12345"
supervisor = create_atlas_supervisor(task_id)

result = supervisor.invoke(
    {"messages": [{"role": "user", "content": "Create a market analysis report"}]},
    config={"configurable": {"thread_id": f"task_{task_id}"}}
)
```

---

## State Management & Memory

### Short-Term Memory (Thread-Scoped)

**Managed by Checkpointers** - Persists conversation state within a single thread

#### Available Checkpointers:

1. **PostgresSaver** (Recommended for production):
```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    conn_string="postgresql://user:pass@localhost:5432/atlas_agents"
)

agent = create_deep_agent(tools=[...], instructions="...")
agent_with_memory = agent.compile(checkpointer=checkpointer)

# Each thread_id maintains separate conversation history
result = agent_with_memory.invoke(
    {"messages": [...]},
    config={"configurable": {"thread_id": "user_123_session_1"}}
)
```

2. **RedisSaver** (Fast, in-memory):
```python
from langgraph.checkpoint.redis import RedisSaver

checkpointer = RedisSaver.from_conn_string(
    conn_string="redis://localhost:6379"
)
```

3. **InMemorySaver** (Development only):
```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()  # Lost on restart!
```

#### What Checkpointers Store:

- **Messages**: Full conversation history
- **Agent State**: Current state variables
- **Tool Outputs**: Results from tool executions
- **Virtual File System**: Contents of agent's file system
- **TODO Lists**: Current plan and task status

### Long-Term Memory (Cross-Thread)

**Managed by Memory Stores** - Persists information across all user sessions

#### Available Memory Stores:

1. **RedisStore** (Recommended for ATLAS):
```python
from langgraph.store.redis import RedisStore

store = RedisStore(
    redis_url="redis://localhost:6379",
    ttl=None  # No expiration
)

# Store user preferences
await store.aput(
    namespace=["users", "user_123"],
    key="preferences",
    value={
        "output_format": "markdown",
        "detail_level": "comprehensive",
        "preferred_models": ["claude-sonnet-4"]
    }
)

# Retrieve later (different session)
preferences = await store.aget(
    namespace=["users", "user_123"],
    key="preferences"
)
```

2. **MongoDBStore** (For complex queries):
```python
from langgraph.store.mongodb import MongoDBStore

store = MongoDBStore(
    connection_string="mongodb://localhost:27017",
    database="atlas_memory"
)
```

#### Memory Store Use Cases:

- **User Preferences**: Output format, verbosity, tone
- **Project History**: Past projects, common patterns
- **Domain Knowledge**: Accumulated facts and insights
- **Agent Learnings**: Successful strategies, common pitfalls

### Hybrid Memory Architecture for ATLAS

**Recommended Setup**:

```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.redis import RedisStore

# Short-term: PostgreSQL (conversation state)
checkpointer = PostgresSaver.from_conn_string(
    os.environ["POSTGRES_URL"]
)

# Long-term: Redis (cross-session knowledge)
store = RedisStore(
    redis_url=os.environ["REDIS_URL"]
)

# Create agent with both
atlas_supervisor = create_deep_agent(
    tools=[...],
    instructions="..."
)

atlas_supervisor_with_memory = atlas_supervisor.compile(
    checkpointer=checkpointer,
    store=store
)

# Usage
result = await atlas_supervisor_with_memory.ainvoke(
    {"messages": [{"role": "user", "content": "Continue my research"}]},
    config={
        "configurable": {
            "thread_id": "user_123_session_5",  # Short-term
            "user_id": "user_123"  # Long-term context
        }
    }
)
```

### Memory Access Patterns

#### 1. Retrieving Previous Conversation

```python
# Get conversation history
history = await checkpointer.aget_tuple(
    config={"configurable": {"thread_id": "user_123_session_4"}}
)

messages = history.checkpoint["channel_values"]["messages"]
```

#### 2. Storing Agent Learnings

```python
# After successful task completion
await store.aput(
    namespace=["projects", project_id],
    key="successful_strategy",
    value={
        "task_type": "market_analysis",
        "approach": "research → analysis → writing",
        "tools_used": ["firecrawl", "e2b", "file_write"],
        "duration_minutes": 15,
        "quality_score": 0.95
    }
)
```

#### 3. Loading User Context

```python
# At start of new session
user_context = await store.aget(
    namespace=["users", user_id],
    key="context"
)

# Include in agent instructions
enhanced_instructions = f"""
{base_instructions}

User Context:
- Previous projects: {user_context["past_projects"]}
- Preferences: {user_context["preferences"]}
- Domain expertise: {user_context["domains"]}
"""
```

---

## Best Practices

### 1. Sub-Agent Design

**DO:**
- ✅ Give each sub-agent a clear, focused responsibility
- ✅ Provide detailed, specific prompts for sub-agents
- ✅ Limit tool access to only what sub-agent needs
- ✅ Use faster/cheaper models for routine sub-tasks
- ✅ Save sub-agent outputs to files for handoffs

**DON'T:**
- ❌ Create overly general sub-agents
- ❌ Share the same prompt across multiple sub-agents
- ❌ Give all sub-agents access to all tools
- ❌ Use expensive models for simple tasks
- ❌ Pass large data in messages (use files instead)

### 2. Planning and Task Management

**DO:**
- ✅ Create detailed plans at start of complex tasks
- ✅ Update TODO status as work progresses
- ✅ Track dependencies between tasks
- ✅ Review plan regularly and adjust as needed
- ✅ Use planning tool to communicate progress to user

**DON'T:**
- ❌ Skip planning for multi-step tasks
- ❌ Forget to update task status
- ❌ Execute dependent tasks out of order
- ❌ Stick to original plan when requirements change
- ❌ Hide planning details from user

### 3. File System Usage

**DO:**
- ✅ Save all intermediate outputs to files
- ✅ Use descriptive filenames with timestamps
- ✅ Organize files in logical directory structure
- ✅ Clean up temporary files after use
- ✅ Use files to pass data between sub-agents

**DON'T:**
- ❌ Keep large data in agent context
- ❌ Use generic filenames like "output.txt"
- ❌ Store all files in root directory
- ❌ Let file system grow unbounded
- ❌ Embed file contents in messages

### 4. Error Handling

**DO:**
- ✅ Validate tool inputs before execution
- ✅ Catch and handle tool execution errors gracefully
- ✅ Provide clear error messages to user
- ✅ Retry failed operations with backoff
- ✅ Log errors for debugging

**DON'T:**
- ❌ Let tool errors crash the entire agent
- ❌ Show raw error traces to users
- ❌ Retry indefinitely without backoff
- ❌ Ignore partial failures
- ❌ Proceed after critical failures

### 5. Performance Optimization

**DO:**
- ✅ Use async agents for concurrent operations
- ✅ Execute independent sub-agents in parallel
- ✅ Cache frequently accessed data in memory store
- ✅ Use cheaper models for simple sub-tasks
- ✅ Stream responses for better UX

**DON'T:**
- ❌ Execute all sub-agents sequentially by default
- ❌ Reload the same data multiple times
- ❌ Use expensive models for all operations
- ❌ Wait until end to return any results
- ❌ Process data synchronously when async is possible

### 6. Observability and Debugging

**DO:**
- ✅ Enable LangSmith tracing in development
- ✅ Log all tool calls and results
- ✅ Track sub-agent invocations
- ✅ Monitor token usage and costs
- ✅ Save failed executions for analysis

**DON'T:**
- ❌ Disable tracing in production
- ❌ Log only errors (lose successful patterns)
- ❌ Ignore sub-agent internal state
- ❌ Overlook cost accumulation
- ❌ Delete failed execution logs

### 7. Testing Strategies

**DO:**
- ✅ Test each sub-agent independently first
- ✅ Mock expensive tools in unit tests
- ✅ Test error handling paths explicitly
- ✅ Validate checkpointing and state recovery
- ✅ Performance test with realistic workloads

**DON'T:**
- ❌ Only test the full supervisor end-to-end
- ❌ Use real API calls in unit tests
- ❌ Only test happy paths
- ❌ Assume state persistence works
- ❌ Test with tiny, unrealistic inputs

---

## Common Pitfalls

### Pitfall 1: Context Window Overflow

**Problem**: Accumulating too much in agent context (messages + file contents)

**Symptoms**:
- Slow response times
- Increased API costs
- Model errors about context length
- Poor agent performance

**Solution**:
```python
# ❌ BAD: Keeping everything in messages
agent.invoke({
    "messages": [
        {"role": "user", "content": "Research AI"},
        {"role": "assistant", "content": "Here are 50 pages of research..."},
        {"role": "user", "content": "Now analyze it"},
        {"role": "assistant", "content": "Here's the analysis..."},
        # Messages keep growing!
    ]
})

# ✅ GOOD: Using file system
agent.invoke({
    "messages": [
        {"role": "user", "content": "Research AI"},
        {"role": "assistant", "content": "Research saved to research_ai.md"},
        {"role": "user", "content": "Now analyze it"},
        {"role": "assistant", "content": "Analysis saved to analysis_ai.md"}
    ]
})
# File contents stored in virtual file system, not messages!
```

### Pitfall 2: Sub-Agent Explosion

**Problem**: Creating too many sub-agents with overlapping responsibilities

**Symptoms**:
- Confusion about which sub-agent to use
- Multiple sub-agents doing similar work
- Increased coordination overhead
- Duplicated outputs

**Solution**:
```python
# ❌ BAD: Too many overlapping sub-agents
subagents = [
    {"name": "web-researcher", ...},
    {"name": "google-searcher", ...},
    {"name": "article-reader", ...},
    {"name": "source-finder", ...},
    # All doing similar research work!
]

# ✅ GOOD: Consolidated with clear responsibilities
subagents = [
    {
        "name": "research-agent",
        "description": "Handles all research tasks",
        "tools": [web_search, web_scrape, article_extract]
    },
    {
        "name": "analysis-agent",
        "description": "Handles all analysis tasks",
        "tools": [code_executor, data_visualizer]
    }
]
```

### Pitfall 3: Synchronous Bottlenecks

**Problem**: Executing independent sub-agents sequentially

**Symptoms**:
- Slow end-to-end execution
- Sub-agents waiting idle
- Poor resource utilization

**Solution**:
```python
# ❌ BAD: Sequential execution
result1 = research_agent.invoke({"messages": [...]})
result2 = analysis_agent.invoke({"messages": [...]})
result3 = writing_agent.invoke({"messages": [...]})

# ✅ GOOD: Parallel execution for independent tasks
from asyncio import gather

results = await gather(
    research_agent.ainvoke({"messages": [...]}),
    analysis_agent.ainvoke({"messages": [...]}),
    writing_agent.ainvoke({"messages": [...]})
)
```

### Pitfall 4: Lost State After Restart

**Problem**: Not using checkpointer, losing conversation on server restart

**Symptoms**:
- Users lose their progress after restarts
- Cannot resume previous conversations
- Must start from scratch each time

**Solution**:
```python
# ❌ BAD: No checkpointer
agent = create_deep_agent(tools=[...], instructions="...")
# State lost on restart!

# ✅ GOOD: PostgreSQL checkpointer
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    os.environ["POSTGRES_URL"]
)

agent = create_deep_agent(
    tools=[...],
    instructions="..."
).compile(checkpointer=checkpointer)
# State persisted across restarts!
```

### Pitfall 5: Ignoring Sub-Agent Errors

**Problem**: Not handling sub-agent failures gracefully

**Symptoms**:
- Entire workflow fails when one sub-agent errors
- No fallback or retry logic
- Cryptic error messages to users

**Solution**:
```python
# ❌ BAD: No error handling
result = sub_agent.invoke({"messages": [...]})
# If fails, entire workflow crashes!

# ✅ GOOD: Graceful error handling
try:
    result = sub_agent.invoke({"messages": [...]})
except Exception as e:
    # Log error
    logger.error(f"Sub-agent failed: {e}")

    # Retry with different approach
    result = fallback_approach()

    # Notify user
    return {
        "messages": [{
            "role": "assistant",
            "content": "Research sub-agent encountered an issue. Used fallback method."
        }]
    }
```

### Pitfall 6: Tool Permission Sprawl

**Problem**: Giving every sub-agent access to every tool

**Symptoms**:
- Sub-agents using wrong tools
- Security concerns (unnecessary permissions)
- Confusing tool selection for agents

**Solution**:
```python
# ❌ BAD: All sub-agents have all tools
all_tools = [web_search, code_exec, file_write, db_query, email_send]

research_sub = {"tools": all_tools}  # Needs only web_search!
analysis_sub = {"tools": all_tools}  # Needs only code_exec!
writing_sub = {"tools": all_tools}  # Needs only file_write!

# ✅ GOOD: Principle of least privilege
research_sub = {
    "name": "research-agent",
    "tools": [web_search, web_scrape]  # Only what it needs
}

analysis_sub = {
    "name": "analysis-agent",
    "tools": [code_executor]  # Only what it needs
}

writing_sub = {
    "name": "writing-agent",
    "tools": [file_write, file_edit]  # Only what it needs
}
```

### Pitfall 7: Monolithic System Prompts

**Problem**: Stuffing all instructions into supervisor prompt

**Symptoms**:
- 10,000+ token system prompts
- Sub-agents don't have clear guidelines
- Difficult to maintain and update
- Poor agent performance

**Solution**:
```python
# ❌ BAD: Everything in supervisor prompt
supervisor_prompt = """
You are a supervisor.

Research instructions:
[5000 tokens of research guidelines]

Analysis instructions:
[5000 tokens of analysis guidelines]

Writing instructions:
[5000 tokens of writing guidelines]
"""

# ✅ GOOD: Distributed prompts
supervisor_prompt = """
You are a supervisor that coordinates specialized sub-agents.
Delegate to the appropriate sub-agent based on task type.
"""

research_sub = {
    "name": "research-agent",
    "prompt": load_prompt("prompts/research_agent.yaml")  # Detailed here
}

analysis_sub = {
    "name": "analysis-agent",
    "prompt": load_prompt("prompts/analysis_agent.yaml")  # Detailed here
}

writing_sub = {
    "name": "writing-agent",
    "prompt": load_prompt("prompts/writing_agent.yaml")  # Detailed here
}
```

---

## References

### Official Documentation

1. **Deep Agents Main Repository**
   - URL: https://github.com/langchain-ai/deepagents
   - Description: Official Python implementation of Deep Agents

2. **Deep Agents Documentation**
   - URL: https://docs.langchain.com/labs/deep-agents/overview
   - Sections:
     - Overview: Core concepts and architecture
     - Quickstart: Basic setup and first agent
     - Configuration Options: Advanced settings
     - Built-in Components: Available tools and utilities

3. **Deep Agents from Scratch (Tutorial)**
   - URL: https://github.com/langchain-ai/deep-agents-from-scratch
   - Description: Step-by-step course on building deep agents with LangGraph

4. **LangGraph Multi-Agent Tutorial**
   - URL: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/
   - Description: Supervisor pattern implementation guide

5. **LangGraph Memory Documentation**
   - URL: https://langchain-ai.github.io/langgraph/concepts/memory/
   - Description: Short-term and long-term memory systems

6. **LangGraph Persistence**
   - URL: https://langchain-ai.github.io/langgraph/concepts/persistence/
   - Description: Checkpointer implementations and state management

### Related Blog Posts

1. **Deep Agents Announcement**
   - URL: https://blog.langchain.com/deep-agents/
   - Date: January 2025
   - Key Topics: Introduction, motivation, key features

2. **LangGraph Multi-Agent Workflows**
   - URL: https://blog.langchain.com/langgraph-multi-agent-workflows/
   - Topics: Multi-agent patterns, coordination strategies

3. **LangGraph Platform GA**
   - URL: https://blog.langchain.com/langgraph-platform-ga/
   - Topics: Production deployment, stateful agents

### Integration Examples

1. **Redis + LangGraph**
   - URL: https://redis.io/blog/langgraph-redis-build-smarter-ai-agents-with-memory-persistence/
   - Topics: Redis checkpointer and memory store

2. **MongoDB + LangGraph**
   - URL: https://www.mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph
   - Topics: MongoDB memory store for long-term agent memory

### Courses

1. **Long-Term Agentic Memory with LangGraph**
   - Platform: DeepLearning.AI
   - URL: https://www.deeplearning.ai/short-courses/long-term-agentic-memory-with-langgraph/
   - Instructor: Harrison Chase (LangChain CEO)
   - Topics: LangMem, memory management, production patterns

### API References

1. **LangChain Agents API**
   - URL: https://python.langchain.com/api_reference/langchain/agents.html

2. **LangGraph API Reference**
   - URL: https://langchain-ai.github.io/langgraph/reference/

### Additional Resources

1. **DataCamp Tutorial**
   - URL: https://www.datacamp.com/tutorial/deep-agents
   - Description: Comprehensive guide with demo project

2. **DeepWiki LangGraph Examples**
   - URL: https://deepwiki.com/langchain-ai/langgraph-101/9-individual-agent-examples
   - Description: Individual agent implementation examples

---

## Appendix: ATLAS-Specific Considerations

### Compatibility with Existing Architecture

| ATLAS Component | Deep Agents Integration | Status |
|----------------|-------------------------|---------|
| Letta Memory | Replace with LangGraph checkpointer + store | ✅ Compatible |
| Firecrawl Tool | Pass as tool to research sub-agent | ✅ Compatible |
| E2B Code Execution | Pass as tool to analysis sub-agent | ✅ Compatible |
| Session Directories | Implement as session-bound file operations | ✅ Compatible |
| AG-UI Events | Broadcast from agent callbacks | ✅ Compatible |
| MLflow Tracking | Wrap agent invocations | ✅ Compatible |
| CopilotKit Frontend | No changes needed | ✅ Compatible |

### Migration Path

**Phase 1: Parallel Implementation** (2-3 days)
- Create Deep Agent supervisor alongside existing Letta agent
- Compare outputs and behavior
- Test with subset of real tasks

**Phase 2: Feature Parity** (3-5 days)
- Add all existing tools to Deep Agent
- Implement session management
- Configure checkpointer and memory store

**Phase 3: Integration** (2-3 days)
- Connect to AG-UI events
- Add MLflow tracking
- Update API endpoints

**Phase 4: Cutover** (1 day)
- Switch primary endpoint to Deep Agent
- Keep Letta agent as fallback
- Monitor for issues

**Phase 5: Cleanup** (1 day)
- Remove Letta agent code
- Update documentation
- Archive old implementation

**Total Estimated Time**: 9-13 days

### Open Questions for ATLAS Team

1. **Model Selection**: Should we use Claude Sonnet 4 for all sub-agents or optimize with cheaper models for simple tasks?

2. **Human-in-the-Loop**: Which tools should require explicit user approval? (e.g., code execution, web scraping)

3. **Memory Scope**: Should we use Redis or MongoDB for long-term memory store? Redis is faster, MongoDB allows complex queries.

4. **Sub-Agent Granularity**: Should we have 3 sub-agents (research, analysis, writing) or more specialized ones (web-research, code-analysis, document-writing, etc.)?

5. **Error Recovery**: What should happen when a sub-agent fails? Retry? Fallback? User notification?

6. **Cost Optimization**: What's the acceptable cost per task? Should we set token budgets for sub-agents?

7. **Observability**: Should we use LangSmith in production for tracing? Or rely only on MLflow?

---

**Document Status**: Research Complete, Ready for Implementation Planning
**Next Steps**: Review with ATLAS team, finalize architecture decisions, begin Phase 1 implementation

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-01 | Claude (Research Agent) | Initial comprehensive research and documentation |
