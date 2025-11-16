# Delegation Architecture

**Module 2.2 Frontend Enhanced - Multi-Agent Delegation System**

Last Updated: November 11, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Components](#architecture-components)
3. [Data Flow](#data-flow)
4. [Implementation Details](#implementation-details)
5. [Recent Fixes](#recent-fixes)
6. [Known Issues](#known-issues)
7. [Testing Guide](#testing-guide)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Module 2.2 Frontend Enhanced application implements a **multi-agent delegation system** where a supervisor agent can delegate specialized tasks to subagent specialists (Researcher, Data Scientist, Expert Analyst, Writer, Reviewer).

### Key Features

- **Hierarchical Task Delegation**: Supervisor delegates tasks to specialized subagents
- **Command.goto Routing**: LangGraph's Command pattern for direct node-to-node routing
- **Thread Hierarchy**: Parent-child thread relationships for conversation tracking
- **Real-time Event Broadcasting**: WebSocket-based subagent visibility for frontend
- **Human-in-the-Loop**: Approval system for file modifications (when auto_approve=false)

### Technology Stack

- **Backend Framework**: FastAPI + LangGraph + LangChain
- **LLM**: Anthropic Claude (claude-3-5-sonnet-20241022)
- **State Management**: PostgreSQL checkpointer for conversation persistence
- **Real-time Communication**: WebSocket for event broadcasting, SSE for LLM streaming
- **Frontend**: Next.js 14 + React + TypeScript

---

## Architecture Components

### 1. Delegation Tools

**Location**: `backend/delegation_tools.py`

The delegation tools allow the supervisor to hand off tasks to specialized subagents:

```python
@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Delegate research tasks to the Researcher subagent."""
    # ... implementation
```

**Available Delegation Tools**:

| Tool | Subagent | Specialization |
|------|----------|----------------|
| `delegate_to_researcher` | Researcher | Web research, information synthesis, citation formatting |
| `delegate_to_data_scientist` | Data Scientist | Statistical analysis, data visualization, trend identification |
| `delegate_to_expert_analyst` | Expert Analyst | Strategic analysis, recommendations, decision support |
| `delegate_to_writer` | Writer | Content creation, summarization, report writing |
| `delegate_to_reviewer` | Reviewer | Quality assurance, fact-checking, review feedback |

**Key Parameters**:
- `task` (str): Complete task description with requirements and output specifications
- `tool_call_id` (Annotated[str, InjectedToolCallId]): Automatically injected by LangGraph for ToolMessage matching

### 2. Unified Graph

**Location**: `backend/langgraph_studio_graphs.py`

The unified graph (`supervisor_agent_unified`) contains all agent nodes:

```python
def create_supervisor_agent_unified() -> CompiledGraph:
    """Create unified graph with supervisor and all subagent nodes."""
    graph = StateGraph(AgentState)

    # Add all nodes
    graph.add_node("supervisor_agent", supervisor_agent_node)
    graph.add_node("researcher_agent", researcher_agent_node)
    graph.add_node("data_scientist_agent", data_scientist_agent_node)
    # ... other subagent nodes

    # Routing via Command.goto (no explicit edges needed)
    graph.set_entry_point("supervisor_agent")

    return graph.compile(checkpointer=checkpointer)
```

**Node Responsibilities**:

- **supervisor_agent_node**: Main orchestrator, decides when to delegate
- **researcher_agent_node**: Executes research tasks (Tavily search, synthesis)
- **data_scientist_agent_node**: Performs data analysis and visualization
- **expert_analyst_agent_node**: Provides strategic insights and recommendations
- **writer_agent_node**: Creates polished content and reports
- **reviewer_agent_node**: Validates quality and accuracy

### 3. Event Broadcasting System

**Location**: `backend/subagents/event_emitter.py`

Broadcasts subagent activity events to the frontend via WebSocket:

```python
async def broadcast_subagent_event(
    thread_id: str,
    event_type: str,
    subagent_type: str,
    data: dict
) -> None:
    """Broadcast subagent event to all connected WebSocket clients."""
    event = {
        "type": event_type,
        "subagent_type": subagent_type,
        "thread_id": thread_id,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    await websocket_manager.broadcast(json.dumps(event))
```

**Event Types**:
- `subagent_started`: When delegation begins
- `subagent_completed`: When subagent finishes successfully
- `subagent_error`: When subagent encounters an error
- `subagent_progress`: For intermediate progress updates

### 4. WebSocket Manager

**Location**: `backend/websocket_manager.py`

Manages WebSocket connections and event broadcasting:

```python
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
```

---

## Data Flow

### Delegation Flow: Supervisor → Researcher

```
┌─────────────────────┐
│   User Query        │
│ "Research X topic"  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────┐
│  supervisor_agent_node          │
│  • Analyzes query               │
│  • Decides to delegate          │
│  • Calls delegate_to_researcher │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  delegate_to_researcher tool            │
│  • Generates subagent_thread_id         │
│  • Broadcasts "subagent_started" event  │
│  • Returns Command(goto="researcher_    │
│    agent", update={...})                │
└──────────┬──────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Command.goto routing                    │
│  • LangGraph routes to researcher_agent  │
│  • Passes state including:               │
│    - parent_thread_id                    │
│    - subagent_thread_id                  │
│    - subagent_type                       │
│    - messages with ToolMessage           │
└──────────┬───────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  researcher_agent_node                  │
│  • Receives task from state             │
│  • Uses Tavily search tool              │
│  • Synthesizes information              │
│  • Formats citations [1] [2] [3]        │
│  • Writes to /workspace/output.md       │
│  • Broadcasts completion event          │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  WebSocket Broadcasting                 │
│  • Events sent to all connected clients │
│  • Frontend SubagentActivityPanel       │
│    displays real-time progress          │
└─────────────────────────────────────────┘
```

### State Management

Each delegation creates a hierarchical thread structure:

```
Parent Thread (main conversation):
  thread_id: "abc123"

  ├─ Subagent Thread (researcher):
  │    subagent_thread_id: "abc123__researcher__xyz789"
  │    parent_thread_id: "abc123"
  │    subagent_type: "researcher"
  │
  ├─ Subagent Thread (data_scientist):
  │    subagent_thread_id: "abc123__data_scientist__def456"
  │    parent_thread_id: "abc123"
  │    subagent_type: "data_scientist"
  │
  └─ ...
```

**Thread ID Generation**:
```python
def generate_subagent_thread_id(parent_thread_id: str, subagent_type: str) -> str:
    """Generate hierarchical thread ID for subagent execution."""
    random_suffix = generate_random_id(8)
    return f"{parent_thread_id}__{subagent_type}__{random_suffix}"
```

---

## Implementation Details

### Critical Implementation Patterns

#### 1. Tool Signature with InjectedToolCallId

**Pattern**:
```python
@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],  # REQUIRED!
) -> Command:
    # ...
```

**Why Required**:
- LangGraph automatically injects `tool_call_id` when the tool is called
- The parameter MUST be in the function signature even if not used directly
- Used in the returned ToolMessage for proper tool_use/tool_result matching

#### 2. Returning Command with ToolMessage

**Pattern**:
```python
return Command(
    goto="researcher_agent",  # Target node name
    update={
        "messages": [
            ToolMessage(
                content=f"✅ Routing to researcher subagent: {task[:100]}...",
                tool_call_id=tool_call_id,  # Use injected ID
                name="delegate_to_researcher"  # Tool name
            )
        ],
        "parent_thread_id": thread_id,
        "subagent_thread_id": subagent_thread_id,
        "subagent_type": "researcher",
    }
)
```

**Why Required**:
- LangGraph validates that every tool call has a corresponding ToolMessage
- The ToolMessage must use the injected `tool_call_id` for matching
- `Command.update` adds the ToolMessage to the state's message history
- Additional state keys (`parent_thread_id`, etc.) can be passed alongside

#### 3. Subagent Node Implementation

**Pattern**:
```python
async def researcher_agent_node(state: AgentState, config: RunnableConfig):
    """Researcher subagent node for executing research tasks."""

    # Extract state
    messages = state.get("messages", [])
    parent_thread_id = state.get("parent_thread_id")
    subagent_thread_id = state.get("subagent_thread_id")

    # Get delegated task from last ToolMessage
    task = extract_task_from_messages(messages)

    # Execute research with researcher-specific tools
    researcher_tools = [tavily_search, write_file, read_file]
    model_with_tools = model.bind_tools(researcher_tools)

    # Stream response and accumulate content
    accumulated_content = ""
    async for chunk in model_with_tools.astream(messages):
        if isinstance(chunk.content, str):
            accumulated_content += chunk.content
        elif isinstance(chunk.content, list):
            # Handle LangChain v1.0+ content blocks
            for block in chunk.content:
                if isinstance(block, str):
                    accumulated_content += block
                elif isinstance(block, dict) and block.get("type") == "text":
                    accumulated_content += block.get("text", "")

    # Broadcast completion event
    await broadcast_subagent_event(
        thread_id=parent_thread_id,
        event_type="subagent_completed",
        subagent_type="researcher",
        data={"result": accumulated_content[:200]}
    )

    return {"messages": [AIMessage(content=accumulated_content)]}
```

---

## Recent Fixes

### Fix 1: TypeError - Missing `tool_call_id` Parameter (Nov 11, 2025)

**Error**:
```
TypeError: delegate_to_researcher() got an unexpected keyword argument 'tool_call_id'
```

**Root Cause**:
- The `DelegationInput` schema declared `tool_call_id: Annotated[str, InjectedToolCallId]`
- LangGraph automatically passes `tool_call_id` when calling the tool
- The function signature was missing the `tool_call_id` parameter

**Fix Applied** (`delegation_tools.py:131-134`):
```python
# Before (BROKEN):
async def delegate_to_researcher(
    task: str,
) -> Command:

# After (FIXED):
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
```

**Status**: ✅ Fixed and tested

---

### Fix 2: ValueError - Missing ToolMessage in Command.update (Nov 11, 2025)

**Error**:
```
ValueError: Expected to have a matching ToolMessage in Command.update for tool
'delegate_to_researcher', got: []. Every tool call (LLM requesting to call a tool)
in the message history MUST have a corresponding ToolMessage.
```

**Root Cause**:
- Previous implementation removed the ToolMessage thinking it wasn't needed
- LangGraph requires every tool call to have a matching ToolMessage
- The ToolMessage provides the tool_use/tool_result pairing

**Fix Applied** (`delegation_tools.py:201-216`):
```python
# Before (BROKEN):
return Command(
    goto="researcher_agent",
    update={
        "parent_thread_id": thread_id,
        "subagent_thread_id": subagent_thread_id,
        "subagent_type": "researcher",
        # No messages array - ERROR!
    }
)

# After (FIXED):
return Command(
    goto="researcher_agent",
    update={
        "messages": [
            ToolMessage(
                content=f"✅ Routing to researcher subagent: {task[:100]}...",
                tool_call_id=tool_call_id,
                name="delegate_to_researcher"
            )
        ],
        "parent_thread_id": thread_id,
        "subagent_thread_id": subagent_thread_id,
        "subagent_type": "researcher",
    }
)
```

**Status**: ✅ Fixed and tested

---

### Fix 3: TypeError in researcher_agent_node - LangChain v1.0+ (Previous Session)

**Error**:
```
TypeError: can only concatenate str (not "list") to str
```

**Root Cause**:
- LangChain v1.0+ changed `chunk.content` from always being `str` to `Union[str, List]`
- Content blocks can now be list of dicts with `{"type": "text", "text": "..."}` format

**Fix Applied** (`langgraph_studio_graphs.py:806-817`):
```python
# Handle both string and list content types (LangChain v1.0+)
if isinstance(chunk.content, str):
    accumulated_content += chunk.content
elif isinstance(chunk.content, list):
    # Extract text from content blocks
    for block in chunk.content:
        if isinstance(block, str):
            accumulated_content += block
        elif isinstance(block, dict) and block.get("type") == "text":
            accumulated_content += block.get("text", "")
```

**Status**: ✅ Fixed and verified still in place

---

## Known Issues

### 1. ACE Framework PlaybookDelta Validation Errors (LOW PRIORITY)

**Error Pattern**:
```
ERROR:ace.middleware:[exec_supervisor_3] Async reflection failed: Fallback extraction failed
```

**Impact**: Non-critical - Does not block delegation functionality

**Root Cause**:
- Osmosis-Structure-0.6B model may produce schema-invalid output
- Fallback to Claude works but logs errors
- PlaybookDelta schema may need more permissive validation

**Status**: ⚠️ Known issue - Does not affect core delegation

**Potential Fixes** (if time permits):
- Update PlaybookDelta Pydantic schema to be more permissive
- Improve Osmosis prompt for better structured output
- Enhance fallback extraction logic to handle edge cases

---

## Testing Guide

### Manual Testing

#### Test 1: Simple Query (No Delegation)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is 2+2?",
    "auto_approve": true,
    "plan_mode": false,
    "session_id": "test-simple"
  }' \
  --no-buffer
```

**Expected Result**:
- ✅ Response: "2 + 2 = **4**"
- ✅ No delegation triggered
- ✅ Stream completes with `"type": "stream_complete"`

---

#### Test 2: Delegation to Researcher

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Delegate to researcher: Find 3 Python frameworks from 2025",
    "auto_approve": true,
    "plan_mode": false,
    "session_id": "test-delegation"
  }' \
  --no-buffer
```

**Expected Result**:
1. ✅ Supervisor calls `delegate_to_researcher` tool
2. ✅ Tool result: "✅ Routing to researcher subagent..."
3. ✅ Researcher agent starts (visible tool calls to `tavily_search`)
4. ✅ No TypeError or ValueError
5. ✅ Research results returned

---

#### Test 3: Frontend WebSocket Events

**Steps**:
1. Open browser to `http://localhost:3000`
2. Open DevTools → Network → WS
3. Submit research query: "Research the latest AI frameworks"
4. Monitor WebSocket messages

**Expected Events**:
```json
{
  "type": "subagent_started",
  "subagent_type": "researcher",
  "thread_id": "...",
  "timestamp": "2025-11-11T...",
  "data": {
    "task": "Research the latest AI frameworks...",
    "subagent_thread_id": "...researcher..."
  }
}
```

```json
{
  "type": "subagent_completed",
  "subagent_type": "researcher",
  "thread_id": "...",
  "timestamp": "2025-11-11T...",
  "data": {
    "success": true,
    "routing": "Command.goto to researcher_agent"
  }
}
```

---

### Automated Testing Script

Create `backend/test_delegation.py`:

```python
#!/usr/bin/env python3
"""Test delegation functionality."""
import requests
import json

def test_delegation():
    """Test researcher delegation."""
    url = "http://localhost:8000/api/chat"
    payload = {
        "message": "Research Python 3.12 features. Give me 3 bullet points.",
        "auto_approve": True,
        "plan_mode": False,
        "session_id": "test-delegation-auto"
    }

    print("🧪 Testing delegation...")
    response = requests.post(url, json=payload, stream=True, timeout=60)

    delegation_triggered = False
    tool_result_received = False

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if '"tool": "delegate_to_researcher"' in line_str:
                delegation_triggered = True
                print("✅ Delegation tool called")

            if '"type": "tool_result"' in line_str and 'Routing to researcher' in line_str:
                tool_result_received = True
                print("✅ Tool result received")

            if '"type": "llm_final_response"' in line_str:
                print("✅ Final response received")

    if delegation_triggered and tool_result_received:
        print("\n✅ ALL TESTS PASSED")
        return True
    else:
        print("\n❌ TESTS FAILED")
        return False

if __name__ == "__main__":
    test_delegation()
```

**Usage**:
```bash
cd backend
python test_delegation.py
```

---

## Troubleshooting

### Issue: "TypeError: delegate_to_researcher() got an unexpected keyword argument 'tool_call_id'"

**Solution**: Ensure the function signature includes the `tool_call_id` parameter:

```python
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],  # Must be present!
) -> Command:
```

---

### Issue: "ValueError: Expected to have a matching ToolMessage"

**Solution**: Ensure the Command.update includes a ToolMessage:

```python
return Command(
    goto="researcher_agent",
    update={
        "messages": [
            ToolMessage(
                content=f"✅ Routing to researcher subagent: {task[:100]}...",
                tool_call_id=tool_call_id,
                name="delegate_to_researcher"
            )
        ],
        # ... other state keys
    }
)
```

---

### Issue: "TypeError: can only concatenate str (not 'list') to str"

**Solution**: Handle both string and list content types in subagent nodes:

```python
if isinstance(chunk.content, str):
    accumulated_content += chunk.content
elif isinstance(chunk.content, list):
    for block in chunk.content:
        if isinstance(block, str):
            accumulated_content += block
        elif isinstance(block, dict) and block.get("type") == "text"):
            accumulated_content += block.get("text", "")
```

---

### Issue: Delegation not triggered by supervisor

**Possible Causes**:
1. Query doesn't clearly indicate need for delegation
2. Supervisor decides to handle task directly

**Solutions**:
- Make query more explicit: "Delegate to researcher: [task]"
- Use complex queries that require specialized expertise
- Check supervisor prompt to ensure delegation is encouraged for appropriate tasks

---

### Issue: WebSocket events not reaching frontend

**Debug Steps**:
1. Check WebSocket connection: DevTools → Network → WS
2. Verify `broadcast_subagent_event()` is called in delegation tool
3. Check WebSocketManager has active connections
4. Verify frontend `usePlanWebSocket` hook is connected

**Check Backend Logs**:
```bash
tail -f backend.log | grep "WebSocket\|broadcast_subagent_event"
```

---

## Summary

### Delegation System Status

✅ **Working**:
- Supervisor → Researcher delegation
- Tool signature with `tool_call_id` parameter
- Command.goto routing with ToolMessage
- Thread hierarchy and state management
- Event broadcasting system
- Frontend WebSocket integration

⚠️ **Known Issues**:
- ACE Framework validation errors (non-critical)
- Playwright MCP automation issues (manual testing available)

### File Changes Log

| File | Lines | Change | Date |
|------|-------|--------|------|
| `delegation_tools.py` | 131-134 | Added `tool_call_id` parameter | 2025-11-11 |
| `delegation_tools.py` | 201-216 | Added ToolMessage to Command.update | 2025-11-11 |
| `langgraph_studio_graphs.py` | 806-817 | Handle LangChain v1.0+ content blocks | Previous session |

---

## References

- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **LangChain v1.0 Migration**: https://python.langchain.com/docs/versions/v0_2/migration_guide/
- **FastAPI WebSockets**: https://fastapi.tiangolo.com/advanced/websockets/
- **Anthropic Claude API**: https://docs.anthropic.com/

---

**End of Delegation Architecture Documentation**
