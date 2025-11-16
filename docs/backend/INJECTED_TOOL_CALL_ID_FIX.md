# InjectedToolCallId Fix - Quick Implementation Guide

## The Problem

```bash
TypeError: delegate_to_researcher() missing 1 required positional argument: 'tool_call_id'
```

## The Solution (One Line Change)

Add `tool_call_id` to your `DelegationInput` schema:

```python
class DelegationInput(BaseModel):
    """Unified input schema for all delegation tools."""

    task: str = Field(...)

    # ✅ ADD THIS LINE:
    tool_call_id: Annotated[str, InjectedToolCallId] = Field(default=None)
```

## Why This Works

1. **With args_schema**: LangChain validates inputs against the Pydantic model
2. **Without field in schema**: Validator doesn't know to inject `tool_call_id`
3. **With field in schema**: Validator recognizes it as injected and passes it to function
4. **InjectedToolCallId annotation**: Tells framework to inject at runtime (not from LLM)
5. **default=None**: Makes it optional in schema (framework overrides with real value)

## What Gets Fixed

This single change fixes **all 5 delegation tools** because they all use `DelegationInput`:

- ✅ `delegate_to_researcher`
- ✅ `delegate_to_data_scientist`
- ✅ `delegate_to_expert_analyst`
- ✅ `delegate_to_writer`
- ✅ `delegate_to_reviewer`

## Complete Updated Schema

```python
class DelegationInput(BaseModel):
    """
    Unified input schema for all delegation tools.

    The task field should contain a complete, well-crafted prompt for the subagent
    following prompt engineering best practices.

    Note: tool_call_id is injected at runtime by LangGraph and is not visible
    to the LLM in the tool schema.
    """

    task: str = Field(
        ...,
        description=(
            "Complete task description for the subagent. This should be a well-crafted prompt that includes:\n"
            "- Clear objective and context\n"
            "- All necessary requirements and constraints\n"
            "- Output file location (e.g., '/workspace/report.md')\n"
            "- Expected format and structure\n"
            "- Any relevant examples or references\n"
            "\n"
            "Example: 'Research the latest trends in quantum computing for 2025. Focus on practical business "
            "applications, not theoretical physics. Search for sources from Q4 2024 onwards. Create a structured "
            "report with: (1) Executive Summary, (2) Key Trends (3-5 bullet points each), (3) Business Impact "
            "Analysis, (4) Sources (numbered citations). Save to /workspace/quantum_trends_2025.md'"
        )
    )

    # ✅ CRITICAL: Add tool_call_id to schema for injection to work
    tool_call_id: Annotated[str, InjectedToolCallId] = Field(
        default=None,
        description="Tool call ID injected by LangGraph at runtime (not visible to LLM)"
    )
```

## Implementation Steps

1. Open `delegation_tools.py`
2. Find the `DelegationInput` class (lines 40-65)
3. Add the `tool_call_id` field after the `task` field
4. Save the file
5. Test by running the agent with delegation

## No Other Changes Needed

Your function signatures are already correct:

```python
@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],  # ✅ Already correct
    thread_id: Optional[str] = None,
    checkpointer=None
) -> Command:
    # Implementation...
```

Keep them as-is!

## Testing

After the fix, test with:

```bash
cd backend
python test_delegation_tools.py
```

Or run the full agent and try delegating a task:

```bash
python main.py
# In UI: "Research the latest AI trends"
```

## References

- **Full Research Report**: `INJECTED_TOOL_CALL_ID_RESEARCH.md`
- **Stack Overflow**: Q79746960 (accepted answer)
- **GitHub Issue**: langchain-ai/langchain#31688
- **LangChain Docs**: https://docs.langchain.com/oss/python/langchain/tools

---

**TL;DR**: Add `tool_call_id: Annotated[str, InjectedToolCallId] = Field(default=None)` to `DelegationInput` schema. That's it.
