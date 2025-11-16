# Research Summary: tool_use/tool_result Error Fix

**Date**: November 9, 2025
**Status**: Research Complete - Ready for Implementation
**Priority**: CRITICAL - Blocks subagent delegation

---

## TL;DR - The Fix

Your delegation tools return **strings** when they should return **ToolMessage objects** wrapped in **Command**.

**Current (BROKEN):**
```python
@tool("delegate_to_researcher")
async def delegate_to_researcher(task: str, thread_id: str, checkpointer) -> str:
    result = await researcher.ainvoke(...)
    return "✅ Researcher completed"  # ❌ Wrong!
```

**Fixed (CORRECT):**
```python
from typing import Annotated
from langchain_core.tools import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command

@tool("delegate_to_researcher")
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],  # ✅ Add this
    thread_id: str,
    checkpointer
) -> Command:  # ✅ Change return type
    result = await researcher.ainvoke(...)

    # ✅ Return Command with ToolMessage
    return Command(update={
        "messages": [
            ToolMessage(
                content=result["messages"][-1].content,
                tool_call_id=tool_call_id  # ✅ Critical: matches tool_use id
            )
        ]
    })
```

---

## Why This Error Happens

### Anthropic's Strict Rule

> "Each `tool_use` block must have a corresponding `tool_result` block in the next message."

### What's Happening Now

1. Main agent decides to delegate: Creates `tool_use` block with id="abc123"
2. Your delegation tool executes and returns: `"✅ Researcher completed"`
3. LangGraph adds the string to messages (NOT as a ToolMessage)
4. Main agent's next turn sees: `tool_use` with id="abc123" but NO matching `ToolMessage`
5. Anthropic API: ❌ **"tool_use without tool_result"**

### What Should Happen

1. Main agent decides to delegate: Creates `tool_use` block with id="abc123"
2. LangGraph injects `tool_call_id="abc123"` into your function
3. Your delegation tool returns: `Command(update={"messages": [ToolMessage(content="...", tool_call_id="abc123")]})`
4. LangGraph adds `ToolMessage` to state with matching id
5. Main agent's next turn sees: `tool_use` id="abc123" followed by `ToolMessage` tool_call_id="abc123"
6. Anthropic API: ✅ **Valid sequence - success!**

---

## Evidence from Research

### GitHub Issues Found

**Issue #6836 (Meta-Issue):**
- 150+ reports of this exact problem
- 63 open issues, 92 closed as duplicates
- Status: Known widespread issue in LangGraph + Anthropic integration

**Issue #7796:**
- User reported: "tool_use ids were found without tool_result blocks immediately after"
- Marked as duplicate of #6836
- Regression after recent LangChain update

**Issue #1423 (LangGraphJS):**
- Same issue in JavaScript version
- Root cause: Message state restoration breaks tool_use/tool_result pairing

### Official Solutions from LangChain Team

**From Multi-Agent Documentation:**
```python
@tool("call_subagent")
def call_subagent(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    result = subagent.invoke({"messages": [{"role": "user", "content": query}]})
    return Command(update={
        "messages": [
            ToolMessage(
                content=result["messages"][-1].content,
                tool_call_id=tool_call_id
            )
        ]
    })
```

**From LangGraph Supervisor Library:**
```python
def create_custom_handoff_tool(agent_name: str) -> BaseTool:
    @tool
    def handoff_to_agent(
        task_description: str,
        tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        tool_message = ToolMessage(
            content=f"Successfully transferred to {agent_name}",
            tool_call_id=tool_call_id,
        )
        return Command(update={"messages": [tool_message]})

    return handoff_to_agent
```

**Pattern is consistent across all official examples:**
1. Use `InjectedToolCallId` annotation
2. Return `Command` object
3. Include `ToolMessage` with matching `tool_call_id`

---

## Files Requiring Updates

All 5 delegation tools in `/backend/delegation_tools.py`:

1. `delegate_to_researcher` (line 122)
2. `delegate_to_data_scientist` (line 223)
3. `delegate_to_expert_analyst` (line 325)
4. `delegate_to_writer` (line 425)
5. `delegate_to_reviewer` (line 526)

**Pattern for each:**
- Add import: `from langchain_core.tools import InjectedToolCallId`
- Add import: `from langgraph.types import Command`
- Add parameter: `tool_call_id: Annotated[str, InjectedToolCallId]`
- Change return type: `-> str` becomes `-> Command`
- Change return statement: String becomes `Command(update={"messages": [ToolMessage(...)]})`

---

## Implementation Steps

### Step 1: Update Imports (delegation_tools.py, top of file)

```python
from typing import Annotated  # ✅ Already imported
from langchain_core.tools import tool, InjectedToolCallId  # ✅ Add InjectedToolCallId
from langchain_core.messages import HumanMessage, ToolMessage  # ✅ Add ToolMessage
from langgraph.types import Command  # ✅ Add this import
```

### Step 2: Update Each Function (Template)

```python
@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],  # ✅ ADD THIS LINE
    thread_id: Optional[str] = None,
    checkpointer=None
) -> Command:  # ✅ CHANGE RETURN TYPE (was -> str)
    """Delegate to researcher subagent."""

    try:
        # Generate hierarchical thread ID
        subagent_thread_id = generate_subagent_thread_id(thread_id, "researcher")
        print(f"[...] Generated researcher thread ID: {subagent_thread_id}")

        # Broadcast start event
        await broadcast_subagent_event(...)

        # Create researcher subagent
        from module_2_2_simple import get_workspace_dir
        workspace_dir = str(get_workspace_dir())
        researcher = create_researcher_subagent(
            checkpointer=checkpointer,
            workspace_dir=workspace_dir
        )

        # Execute researcher subagent
        result = await researcher.ainvoke(
            {"messages": [HumanMessage(content=task)]},
            config={"configurable": {"thread_id": subagent_thread_id}}
        )

        # Broadcast completion event
        await broadcast_subagent_event(...)

        # ✅ REPLACE THIS SECTION
        # OLD: return "✅ Researcher completed: Task executed successfully"

        # NEW: Extract final answer and return Command with ToolMessage
        final_answer = result["messages"][-1].content

        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"✅ Researcher completed successfully.\n\nResult:\n{final_answer}",
                    tool_call_id=tool_call_id
                )
            ]
        })

    except Exception as e:
        # Broadcast error event
        await broadcast_subagent_event(...)

        # ✅ REPLACE THIS SECTION
        # OLD: return f"❌ Researcher failed: {str(e)}"

        # NEW: Return error as ToolMessage (still need proper message format)
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"❌ Researcher failed: {str(e)}",
                    tool_call_id=tool_call_id,
                    status="error"
                )
            ]
        })
```

### Step 3: Apply to All 5 Functions

Repeat the pattern for:
- `delegate_to_data_scientist`
- `delegate_to_expert_analyst`
- `delegate_to_writer`
- `delegate_to_reviewer`

---

## Testing Plan

### Unit Test

```python
async def test_delegation_returns_tool_message():
    """Verify delegation returns proper ToolMessage."""
    result = await delegate_to_researcher(
        task="Test task",
        tool_call_id="test_123",
        thread_id="test_thread"
    )

    # Verify Command object
    assert isinstance(result, Command)
    assert "messages" in result.update

    # Verify ToolMessage with matching tool_call_id
    tool_msg = result.update["messages"][0]
    assert isinstance(tool_msg, ToolMessage)
    assert tool_msg.tool_call_id == "test_123"
```

### Integration Test

```bash
# Start backend
cd backend
python main.py

# Test delegation via API
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Research AI trends and delegate to the researcher subagent",
    "thread_id": "test_delegation_flow"
  }'

# Check logs for:
# ✅ No "BadRequestError: 400" errors
# ✅ No "tool_use without tool_result" messages
# ✅ Successful delegation and completion
```

---

## Expected Outcome

### Before Fix

```
[ERROR] anthropic.BadRequestError: 400
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "messages.4.content.1: unexpected `tool_use` block found without corresponding `tool_result` block"
  }
}
```

### After Fix

```
[INFO] Main agent invoking tool: delegate_to_researcher
[INFO] LangGraph injecting tool_call_id: toolu_01ABC123
[INFO] Delegation: Generated researcher thread ID: thread-main-123/subagent-researcher-xyz789
[INFO] Delegation: Broadcasting researcher start event...
[INFO] Delegation: Creating researcher subagent...
[INFO] Delegation: Invoking researcher subagent...
[INFO] Delegation: Researcher subagent invocation complete
[INFO] Delegation: Broadcasting researcher completion event...
[INFO] LangGraph: Added ToolMessage with tool_call_id=toolu_01ABC123
[INFO] Main agent: Received tool result, continuing execution...
✅ SUCCESS: Research completed successfully
```

---

## Additional Resources

### Full Research Report

See `/backend/RESEARCH_TOOL_USE_TOOL_RESULT_ERROR.md` for:
- Comprehensive root cause analysis
- All GitHub issues (150+ reports)
- Official LangChain documentation links
- Community solutions and patterns
- Message history management best practices
- Debugging tools and validation utilities

### Reference Implementations

1. **LangGraph Supervisor**: https://github.com/langchain-ai/langgraph-supervisor-py
2. **LangGraph Swarm**: https://github.com/langchain-ai/langgraph-swarm-py
3. **LangChain Multi-Agent Docs**: https://docs.langchain.com/oss/python/langchain/multi-agent

---

## Timeline

**Estimated Implementation Time:**
- Code updates (5 functions): 2-3 hours
- Testing (unit + integration): 2-3 hours
- Documentation updates: 1 hour
- **Total: 5-7 hours**

**Priority:** CRITICAL - Blocks all subagent delegation

---

## Next Steps

1. Review this summary and the full research report
2. Confirm approach with team (if applicable)
3. Implement changes to all 5 delegation tools
4. Test with unit tests
5. Test with full integration (backend + frontend)
6. Update CODE_MAP.md and CALL_GRAPH.md documentation
7. Deploy and monitor for errors

---

**Questions or Concerns?**

If you have questions about:
- The technical approach
- Implementation details
- Testing strategy
- Risk assessment

Please ask before proceeding with implementation.

---

**Research Completed:** November 9, 2025
**Confidence Level:** HIGH (Multiple official sources confirm pattern)
**Ready for Implementation:** YES
