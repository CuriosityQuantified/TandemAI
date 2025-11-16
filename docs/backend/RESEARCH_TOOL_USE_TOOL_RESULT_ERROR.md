# Research Report: tool_use/tool_result Error in LangGraph Multi-Agent Systems

**Date**: November 9, 2025
**Issue**: BadRequestError 400 - "tool_use without tool_result" in multi-agent delegation
**Context**: Module 2.2 Deep Agent System with Subagent Delegation

---

## Executive Summary

This research identifies the root cause, community solutions, and proven patterns for resolving the "tool_use without tool_result" error in LangGraph multi-agent systems using Anthropic's Claude API. The error occurs when tool call messages are not properly paired with their corresponding result messages, violating Anthropic's strict message sequencing requirements.

**Key Findings:**
1. This is a **widespread issue** affecting 150+ users (GitHub issue #6836)
2. Root cause is **message history management** during delegation
3. **Proven solution pattern** exists using `InjectedToolCallId` and `Command` objects
4. Current implementation in `delegation_tools.py` **does NOT follow** the proven pattern

---

## 1. Root Cause Analysis

### 1.1 Anthropic API Requirement

The Anthropic Claude Messages API has a **strict sequencing rule**:

> "Each `tool_use` block must have a corresponding `tool_result` block in the next message."

**Valid Message Flow:**
```
User: Initial request with tools defined
Assistant: Response with tool_use blocks (stop_reason: tool_use)
User: Response with tool_result blocks (matching tool_use_id)
Assistant: Final response using tool results
```

### 1.2 Violation Patterns

The error occurs when:
- **Tool messages are orphaned**: `tool_use` exists without matching `tool_result`
- **Message history is trimmed incorrectly**: Removes tool_use but keeps tool_result
- **Delegation doesn't return proper ToolMessage**: Subagent results returned as strings instead of ToolMessage objects
- **Interruptions corrupt state**: Human-in-the-loop or checkpointer issues break pairing

### 1.3 GitHub Issue Evidence

**Issue #7796**:
- Status: Duplicate of meta-issue #6836
- Impact: 150+ reports, 63 open issues, 92 closed as duplicates
- Root Causes Identified:
  - Transient network failures
  - Server errors
  - Hook execution failures
  - **Improper message history management**

**Issue #1423 (LangGraphJS)**:
- Title: "Human-in-the-loop interrupts cause 'tool_result without corresponding tool_use' errors"
- Cause: Message state restoration creates invalid sequences

---

## 2. Community Solutions & Proven Patterns

### 2.1 Official LangChain Pattern (RECOMMENDED)

From the official Multi-Agent documentation, here's the **proven pattern** for delegation:

```python
from typing import Annotated
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command

@tool("delegate_to_researcher")
def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Delegate research task to researcher subagent."""

    # Execute subagent
    result = researcher_agent.invoke({
        "messages": [{"role": "user", "content": task}]
    })

    # Return Command with ToolMessage containing tool_call_id
    return Command(update={
        "messages": [
            ToolMessage(
                content=result["messages"][-1].content,
                tool_call_id=tool_call_id  # CRITICAL: Must match the tool_use id
            )
        ]
    })
```

**Key Components:**
1. **InjectedToolCallId**: LangGraph automatically injects the tool_call_id from the tool_use block
2. **ToolMessage**: Properly formatted message with matching tool_call_id
3. **Command object**: Updates state with the ToolMessage for proper history tracking

### 2.2 LangGraph Supervisor Library Pattern

From `langgraph-supervisor-py`:

```python
from langchain_core.tools import tool, BaseTool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.prebuilt import InjectedState

def create_custom_handoff_tool(*, agent_name: str, name: str, description: str) -> BaseTool:
    @tool(name, description=description)
    def handoff_to_agent(
        task_description: Annotated[str, "Task for the agent"],
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        # Create ToolMessage indicating successful handoff
        tool_message = ToolMessage(
            content=f"Successfully transferred to {agent_name}",
            name=name,
            tool_call_id=tool_call_id,
        )

        # Get current messages from state
        messages = state["messages"]

        # Return Command with navigation and state update
        return Command(
            goto=agent_name,
            update={"messages": messages + [tool_message]}
        )

    return handoff_to_agent
```

**Key Features:**
- **InjectedState**: Access to graph state for context
- **Immediate ToolMessage**: Created before delegation, not after
- **Command navigation**: Routes to specific agent nodes

### 2.3 Deep Agents Pattern

From LangChain's Deep Agents library:

**Orchestrator → Sub-Agent Pattern:**
1. Orchestrator delegates task(s) to sub-agent(s) with clean context
2. Sub-agent performs tool call loops independently
3. Sub-agent compiles final answer
4. **Only synthesized answer** returned to Orchestrator via ToolMessage

**Benefits:**
- Context isolation prevents message history pollution
- Clean tool_use/tool_result pairing within each agent
- No cross-contamination of tool messages

---

## 3. Current Implementation Analysis

### 3.1 delegation_tools.py Implementation

**Current Pattern:**
```python
@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    thread_id: Optional[str] = None,
    checkpointer=None
) -> str:  # ❌ Returns string, not Command with ToolMessage
    """Delegate to researcher subagent."""

    # Execute subagent
    result = await researcher.ainvoke(
        {"messages": [HumanMessage(content=task)]},
        config={"configurable": {"thread_id": subagent_thread_id}}
    )

    # ❌ Returns simple string success message
    return "✅ Researcher completed: Task executed successfully"
```

### 3.2 Problems Identified

**CRITICAL ISSUES:**

1. **Missing InjectedToolCallId**
   - No `tool_call_id` parameter in function signature
   - Cannot create ToolMessage with matching tool_call_id

2. **Returns String Instead of ToolMessage**
   - Returns: `"✅ Researcher completed: Task executed successfully"`
   - Should return: `Command(update={"messages": [ToolMessage(content=..., tool_call_id=...)]})`

3. **No Command Object**
   - Doesn't use Command for state updates
   - LangGraph cannot properly track tool call completion

4. **Message History Pollution**
   - When main agent's LLM sees the string return value
   - It tries to call another tool or respond
   - But the tool_use block has no matching ToolMessage in history
   - **Result**: "tool_use without tool_result" error

### 3.3 Why This Causes The Error

**Execution Flow (Current - BROKEN):**

```
1. Main Agent LLM: "I should use delegate_to_researcher"
   → Creates tool_use block with id="tool_abc123"

2. LangGraph: Executes delegate_to_researcher()
   → Returns string: "✅ Researcher completed: Task executed successfully"

3. LangGraph: Adds string to messages as generic result
   → NO ToolMessage with tool_call_id="tool_abc123" created

4. Main Agent LLM: Receives messages for next turn
   → Messages contain: [HumanMessage, AIMessage(tool_use id=tool_abc123), ???]
   → Missing: ToolMessage(tool_call_id=tool_abc123)

5. Anthropic API: Validates message sequence
   ❌ ERROR: "tool_use without tool_result"
```

**Execution Flow (Fixed - CORRECT):**

```
1. Main Agent LLM: "I should use delegate_to_researcher"
   → Creates tool_use block with id="tool_abc123"

2. LangGraph: Injects tool_call_id into function
   → delegate_to_researcher(task="...", tool_call_id="tool_abc123")

3. Function: Executes subagent, returns Command
   → Command(update={"messages": [ToolMessage(content="...", tool_call_id="tool_abc123")]})

4. LangGraph: Updates state with ToolMessage
   → Messages now: [HumanMessage, AIMessage(tool_use id=tool_abc123), ToolMessage(tool_call_id=tool_abc123)]

5. Main Agent LLM: Receives properly sequenced messages
   ✅ SUCCESS: tool_use matched with tool_result
```

---

## 4. Message History Management

### 4.1 trim_messages Best Practices

When managing conversation history to stay within token limits:

**Issue #29637**: "`trim_messages` and `ChatAnthropic` token counter with tools"

**Problem:**
- If you trim the AI message containing tool_use
- But keep the ToolMessage with tool_result
- API error: "tool_result without corresponding tool_use"

**Solution:**
```python
from langchain_core.messages.utils import trim_messages

trimmed = trim_messages(
    messages,
    max_tokens=100000,
    strategy="last",
    start_on="human",      # Always start on human message
    end_on=("human", "tool"),  # End on valid message types
    include_system=True,   # Keep system message
    token_counter=model    # Use model's token counter
)
```

**Key Parameters:**
- `start_on="human"`: Ensures first message is HumanMessage
- `end_on=("human", "tool")`: Ensures last message is valid for continuation
- Preserves tool_use/tool_result pairing by trimming conversation turns (not individual messages)

### 4.2 Message Filtering Rules

**From LangGraph Discussion #1410:**

When filtering messages:
1. **Never break tool pairs**: If keeping tool_result, MUST keep preceding tool_use
2. **Trim by conversation turns**: Remove entire HumanMessage → AIMessage → ToolMessage sequences
3. **Preserve system message**: Always keep at index 0
4. **End on valid types**: Only end on "human" or "tool" messages

---

## 5. Recommended Solutions

### 5.1 Immediate Fix (REQUIRED)

Update all delegation tools in `delegation_tools.py`:

**Before:**
```python
@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    thread_id: Optional[str] = None,
    checkpointer=None
) -> str:
    result = await researcher.ainvoke(...)
    return "✅ Researcher completed: Task executed successfully"
```

**After:**
```python
from typing import Annotated
from langchain_core.tools import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command

@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],  # ✅ Add this
    thread_id: Optional[str] = None,
    checkpointer=None
) -> Command:  # ✅ Change return type
    """Delegate to researcher subagent."""

    # Execute subagent (same as before)
    result = await researcher.ainvoke(
        {"messages": [HumanMessage(content=task)]},
        config={"configurable": {"thread_id": subagent_thread_id}}
    )

    # ✅ Extract final answer from subagent
    final_answer = result["messages"][-1].content

    # ✅ Return Command with ToolMessage
    return Command(update={
        "messages": [
            ToolMessage(
                content=final_answer,
                tool_call_id=tool_call_id  # Matches the tool_use id
            )
        ]
    })
```

### 5.2 Alternative: Simplified Return

If you want to keep success messages for debugging:

```python
@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    thread_id: Optional[str] = None,
    checkpointer=None
) -> Command:
    """Delegate to researcher subagent."""

    try:
        result = await researcher.ainvoke(...)

        # Success: Return ToolMessage with result
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"✅ Researcher completed successfully.\n\nResult:\n{result['messages'][-1].content}",
                    tool_call_id=tool_call_id
                )
            ]
        })

    except Exception as e:
        # Error: Still return ToolMessage (with error content)
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"❌ Researcher failed: {str(e)}",
                    tool_call_id=tool_call_id,
                    status="error"  # Optional: Mark as error
                )
            ]
        })
```

### 5.3 Update All 5 Delegation Tools

Apply the same fix to:
1. `delegate_to_researcher` ✅
2. `delegate_to_data_scientist` ✅
3. `delegate_to_expert_analyst` ✅
4. `delegate_to_writer` ✅
5. `delegate_to_reviewer` ✅

---

## 6. Testing Strategy

### 6.1 Unit Test: Tool Message Format

```python
import pytest
from langchain_core.messages import ToolMessage

async def test_delegation_returns_tool_message():
    """Verify delegation tool returns proper ToolMessage."""

    # Mock tool_call_id
    tool_call_id = "test_abc123"

    # Execute delegation
    result = await delegate_to_researcher(
        task="Test research task",
        tool_call_id=tool_call_id,
        thread_id="test_thread"
    )

    # Verify Command structure
    assert isinstance(result, Command)
    assert "messages" in result.update

    # Verify ToolMessage
    tool_message = result.update["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.tool_call_id == tool_call_id
    assert len(tool_message.content) > 0
```

### 6.2 Integration Test: Full Delegation Flow

```python
async def test_full_delegation_flow():
    """Test complete delegation from supervisor agent to subagent."""

    # Create supervisor agent with delegation tools
    supervisor_agent = create_deep_agent(
        tools=[delegate_to_researcher, delegate_to_data_scientist, ...]
    )

    # Execute task requiring delegation
    result = await supervisor_agent.ainvoke(
        {"messages": [HumanMessage(content="Research AI trends in 2025")]},
        config={"configurable": {"thread_id": "test_main_thread"}}
    )

    # Verify no API errors
    assert "error" not in str(result).lower()

    # Verify message history is valid
    messages = result["messages"]

    # Check for tool_use/tool_result pairing
    for i, msg in enumerate(messages):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            # Found tool_use - next message should be ToolMessage
            assert i + 1 < len(messages), "tool_use without following message"
            next_msg = messages[i + 1]
            assert isinstance(next_msg, ToolMessage), "tool_use not followed by ToolMessage"

            # Verify tool_call_id matches
            for tool_call in msg.tool_calls:
                assert next_msg.tool_call_id == tool_call["id"]
```

### 6.3 Error Scenario Test

```python
async def test_delegation_error_handling():
    """Verify errors still return proper ToolMessage."""

    # Force an error condition
    with patch('subagents.create_researcher_subagent', side_effect=Exception("Test error")):
        result = await delegate_to_researcher(
            task="Test task",
            tool_call_id="test_error_123",
            thread_id="test_thread"
        )

        # Even on error, should return ToolMessage
        assert isinstance(result, Command)
        tool_message = result.update["messages"][0]
        assert isinstance(tool_message, ToolMessage)
        assert tool_message.tool_call_id == "test_error_123"
        assert "failed" in tool_message.content.lower() or "error" in tool_message.content.lower()
```

---

## 7. Additional Considerations

### 7.1 Pydantic Schema Updates

When using Pydantic schemas with `InjectedToolCallId`:

**Include in both schema AND function signature:**

```python
from pydantic import BaseModel, Field

class DelegationInput(BaseModel):
    """Input schema for delegation tools."""
    task: str = Field(description="Task description")
    tool_call_id: Annotated[str, InjectedToolCallId] = Field(default=None)  # ✅ Add here

@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],  # ✅ And here
    thread_id: Optional[str] = None,
    checkpointer=None
) -> Command:
    ...
```

### 7.2 Message History Size Management

If conversation history grows too large:

```python
from langchain_core.messages.utils import trim_messages

def pre_model_hook(state):
    """Trim message history before calling LLM."""
    messages = state["messages"]

    # Trim to last 50 messages, preserving tool pairs
    trimmed = trim_messages(
        messages,
        max_tokens=100000,
        strategy="last",
        start_on="human",
        end_on=("human", "tool"),
        include_system=True
    )

    return {"messages": trimmed}

# Use in create_deep_agent or create_react_agent
agent = create_react_agent(
    model=llm,
    tools=tools,
    checkpointer=checkpointer,
    pre_model_hook=pre_model_hook  # ✅ Add trimming hook
)
```

### 7.3 Debugging Tools

**Check message history for orphaned tool_use blocks:**

```python
def validate_tool_message_pairing(messages):
    """Validate all tool_use blocks have matching tool_result."""
    errors = []

    for i, msg in enumerate(messages):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            # Found tool_use - verify next message is ToolMessage
            if i + 1 >= len(messages):
                errors.append(f"Message {i}: tool_use at end of history (no result)")
                continue

            next_msg = messages[i + 1]
            if not isinstance(next_msg, ToolMessage):
                errors.append(f"Message {i}: tool_use not followed by ToolMessage")
                continue

            # Verify tool_call_id matches
            for tool_call in msg.tool_calls:
                if next_msg.tool_call_id != tool_call["id"]:
                    errors.append(f"Message {i}: tool_call_id mismatch ({tool_call['id']} != {next_msg.tool_call_id})")

    return errors

# Usage
errors = validate_tool_message_pairing(state["messages"])
if errors:
    print("⚠️  Tool message pairing errors:")
    for error in errors:
        print(f"  - {error}")
```

---

## 8. References

### 8.1 GitHub Issues

1. **anthropics/claude-code #6836** - Meta-issue: tool_use/tool_result block mismatch (150+ reports)
2. **anthropics/claude-code #7796** - tool_use ids without tool_result (duplicate of #6836)
3. **langchain-ai/langgraphjs #1423** - Human-in-the-loop interrupts cause tool_result errors
4. **langchain-ai/langchain #29637** - trim_messages and ChatAnthropic token counter with tools
5. **langchain-ai/langgraph #2445** - How to route tools in supervisor multi-agent
6. **langchain-ai/langgraph #4397** - Multiple tool results for single tool call with approval flow

### 8.2 Official Documentation

1. **LangChain Multi-Agent Docs**: https://docs.langchain.com/oss/python/langchain/multi-agent
   - Official delegation pattern with InjectedToolCallId

2. **Claude Tool Use Docs**: https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview
   - Message sequencing requirements
   - tool_use and tool_result pairing rules

3. **LangGraph Message Management**: https://langchain-ai.github.io/langgraph/how-tos/manage-conversation-history/
   - trim_messages best practices
   - Preserving tool message pairs

4. **LangGraph Update State from Tools**: https://langchain-ai.github.io/langgraph/how-tos/update-state-from-tools/
   - Command object usage
   - InjectedToolCallId pattern

### 8.3 Community Resources

1. **LangGraph Supervisor Library**: https://github.com/langchain-ai/langgraph-supervisor-py
   - Reference implementation of handoff tools
   - Custom delegation patterns

2. **LangGraph Swarm Library**: https://github.com/langchain-ai/langgraph-swarm-py
   - Multi-agent coordination patterns
   - InjectedToolCallId with InjectedState

3. **Deep Agents Library**: https://github.com/langchain-ai/deepagents
   - Orchestrator → Sub-Agent pattern
   - Context isolation for clean tool pairing

### 8.4 Code Examples

1. **Basic InjectedToolCallId Example** (January 2025):
   ```
   GitHub: langchain-ai/langgraph/issues/2962
   ```

2. **Handoff Tool Example** (January 2025):
   ```
   GitHub: langchain-ai/langgraph-swarm-py/issues/59
   ```

3. **ReAct Agent with Message Management**:
   ```
   https://langchain-ai.github.io/langgraph/how-tos/create-react-agent-manage-message-history/
   ```

---

## 9. Implementation Checklist

### Phase 1: Update Delegation Tools (CRITICAL)

- [ ] Import `InjectedToolCallId` from `langchain_core.tools`
- [ ] Import `Command` from `langgraph.types`
- [ ] Import `ToolMessage` from `langchain_core.messages`
- [ ] Update `delegate_to_researcher` function signature and return type
- [ ] Update `delegate_to_data_scientist` function signature and return type
- [ ] Update `delegate_to_expert_analyst` function signature and return type
- [ ] Update `delegate_to_writer` function signature and return type
- [ ] Update `delegate_to_reviewer` function signature and return type
- [ ] Update Pydantic schema to include `tool_call_id` (optional)

### Phase 2: Testing

- [ ] Create unit test for ToolMessage format
- [ ] Create integration test for full delegation flow
- [ ] Create error scenario test
- [ ] Add message history validation utility
- [ ] Test with real subagent execution

### Phase 3: Monitoring & Validation

- [ ] Add logging for tool_call_id tracking
- [ ] Implement message history validator in development
- [ ] Monitor for Anthropic API errors in production
- [ ] Create alert for tool_use/tool_result mismatches

### Phase 4: Documentation

- [ ] Update CODE_MAP.md with new delegation pattern
- [ ] Update CALL_GRAPH.md with ToolMessage flow
- [ ] Add troubleshooting guide for tool message errors
- [ ] Document testing procedures

---

## 10. Conclusion

The "tool_use without tool_result" error is a **well-documented issue** in the LangChain/LangGraph community with **proven solutions**. The current implementation in `delegation_tools.py` does not follow the recommended pattern, which is why the error occurs.

**Root Cause:**
- Delegation tools return strings instead of `Command` objects with `ToolMessage`
- Missing `tool_call_id` parameter and `InjectedToolCallId` injection
- LangGraph cannot create proper tool_result messages to match tool_use blocks

**Solution:**
- Update all 5 delegation tools to use `InjectedToolCallId` pattern
- Return `Command(update={"messages": [ToolMessage(content=..., tool_call_id=...)]})`
- This creates proper tool_use → tool_result pairing that satisfies Anthropic's API requirements

**Estimated Implementation Time:**
- Code changes: 2-3 hours (all 5 tools)
- Testing: 2-3 hours (unit + integration)
- Total: 4-6 hours

**Priority:** CRITICAL - This blocks all subagent delegation functionality

---

**Research Completed By:** Claude Code (Sonnet 4.5)
**Research Duration:** Comprehensive multi-source analysis
**Confidence Level:** HIGH - Multiple official sources confirm the pattern
