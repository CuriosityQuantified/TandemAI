# InjectedToolCallId Flow Diagram

## The Problem Flow (BEFORE FIX)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. LLM Generates Tool Call                                       │
│    { "name": "delegate_to_researcher", "task": "Research AI" }   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. ToolNode Validates Against Schema                             │
│    DelegationInput.model_validate({"task": "Research AI"})      │
│                                                                   │
│    Schema fields: ❌ tool_call_id NOT in schema                 │
│    Result: {"task": "Research AI"}  ← Missing tool_call_id!     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. ToolNode Calls Function                                       │
│    await delegate_to_researcher(**validated_args)                │
│                                                                   │
│    Tries: delegate_to_researcher(task="Research AI")             │
│    Function signature expects: (task, tool_call_id, ...)        │
│                                                                   │
│    ❌ ERROR: missing required argument 'tool_call_id'           │
└─────────────────────────────────────────────────────────────────┘
```

## The Solution Flow (AFTER FIX)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. LLM Generates Tool Call                                       │
│    { "name": "delegate_to_researcher", "task": "Research AI" }   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. ToolNode Validates Against Schema                             │
│    DelegationInput.model_validate({"task": "Research AI"})      │
│                                                                   │
│    Schema fields:                                                │
│    - task: "Research AI" (from LLM)                             │
│    - tool_call_id: None (default, not from LLM)                 │
│                                                                   │
│    ✅ InjectedToolCallId annotation detected!                   │
│    Framework injects: tool_call_id = "call_abc123"              │
│                                                                   │
│    Result: {"task": "Research AI", "tool_call_id": "call_abc123"}│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. ToolNode Calls Function                                       │
│    await delegate_to_researcher(**validated_args)                │
│                                                                   │
│    Calls: delegate_to_researcher(                                │
│        task="Research AI",                                       │
│        tool_call_id="call_abc123"  ← ✅ Injected by framework!  │
│    )                                                             │
│                                                                   │
│    ✅ SUCCESS: Function receives all required arguments          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Function Returns Command with ToolMessage                     │
│    return Command(update={                                       │
│        "messages": [                                             │
│            ToolMessage(                                          │
│                content="Routing to researcher...",               │
│                tool_call_id="call_abc123"  ← ✅ Matches!         │
│            )                                                     │
│        ]                                                         │
│    })                                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. LangGraph Matches tool_use with tool_result                  │
│    tool_use message (id: call_abc123)                           │
│      ↕ matched with                                             │
│    tool_result message (id: call_abc123)                        │
│                                                                   │
│    ✅ Proper message pairing for conversation flow               │
└─────────────────────────────────────────────────────────────────┘
```

## Key Concepts Visualized

### Schema Validation Pipeline

```
LLM Output           Schema Validation              Function Call
    │                       │                             │
    ▼                       ▼                             ▼
┌────────┐           ┌──────────┐              ┌──────────────────┐
│{"task":│  ────────▶│Pydantic  │  ──────────▶ │delegate_to_      │
│"..."}  │           │validate()│              │researcher(...)   │
└────────┘           └──────────┘              └──────────────────┘
                           │
                           │ ✅ WITH tool_call_id in schema:
                           │    Recognizes InjectedToolCallId
                           │    Injects framework value
                           │
                           │ ❌ WITHOUT tool_call_id in schema:
                           │    Doesn't know to inject
                           │    Function call fails
```

### InjectedToolCallId Annotation Behavior

```
┌────────────────────────────────────────────────────────────────┐
│ InjectedToolCallId Annotation Effects                          │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. ❌ NOT Sent to LLM in Tool Schema                           │
│    LLM sees:  { "task": "string" }                            │
│    LLM does NOT see: { "task": "string", "tool_call_id": "..." }│
│                                                                 │
│ 2. ✅ Recognized by Pydantic Validator                         │
│    Validator knows this is a special injected field           │
│                                                                 │
│ 3. ✅ Injected by Framework at Runtime                         │
│    Framework provides: tool_call_id = "call_abc123"           │
│                                                                 │
│ 4. ✅ Overrides Any LLM-Generated Values                       │
│    If LLM accidentally provides tool_call_id, framework        │
│    overrides it with correct value (fixed in 1.0+)            │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Tool Call ID Lifecycle

```
┌────────┐  1. Generate  ┌─────────────┐  2. Associate  ┌──────────┐
│        │  ──────────▶  │             │  ────────────▶ │          │
│ LLM    │               │ ToolNode    │                │ Function │
│        │  ◀──────────  │             │  ◀────────────│          │
└────────┘  6. Receive   └─────────────┘  5. Return    └──────────┘
             Response          │ ▲                           │
                               │ │                           │
                      3. Inject │ │ 4. Use                   │
                               ▼ │                           ▼
                         ┌──────────────┐           ┌──────────────┐
                         │ tool_call_id │           │ ToolMessage  │
                         │ "call_abc123"│───────────│ with same ID │
                         └──────────────┘           └──────────────┘

Flow:
1. LLM generates tool call (framework assigns ID: "call_abc123")
2. ToolNode associates that ID with the tool invocation
3. Framework injects tool_call_id into function parameters
4. Function uses tool_call_id in ToolMessage
5. Function returns ToolMessage(tool_call_id="call_abc123")
6. LLM receives properly matched tool_use/tool_result pair
```

## Code Comparison

### BEFORE (Broken)

```python
class DelegationInput(BaseModel):
    task: str = Field(...)
    # ❌ Missing: tool_call_id

@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],  # ❌ Not in schema
    ...
) -> Command:
    ...

# RESULT: TypeError - missing required argument
```

### AFTER (Fixed)

```python
class DelegationInput(BaseModel):
    task: str = Field(...)
    tool_call_id: Annotated[str, InjectedToolCallId] = Field(default=None)  # ✅ Added

@tool("delegate_to_researcher", args_schema=DelegationInput)
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId],  # ✅ Now works
    ...
) -> Command:
    ...

# RESULT: ✅ Works perfectly
```

## Why default=None?

```
┌────────────────────────────────────────────────────────────────┐
│ Schema Validation Process                                       │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│ WITHOUT default=None:                                          │
│   tool_call_id: Annotated[str, InjectedToolCallId] = Field(...)│
│   ↓                                                             │
│   Pydantic: "tool_call_id is required!"                        │
│   LLM didn't provide it → ❌ Validation Error                  │
│                                                                 │
│ WITH default=None:                                             │
│   tool_call_id: Annotated[str, InjectedToolCallId] = Field(default=None)│
│   ↓                                                             │
│   Pydantic: "tool_call_id not provided, using None"            │
│   Framework: "InjectedToolCallId detected, overriding with real value"│
│   ↓                                                             │
│   ✅ Validation succeeds, injection happens                    │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

## LLM Schema Visibility

```
┌──────────────────────────────────────────────────────────────────┐
│ What the LLM Sees (Tool Schema)                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│ {                                                                 │
│   "name": "delegate_to_researcher",                              │
│   "description": "Delegate research task...",                    │
│   "parameters": {                                                │
│     "type": "object",                                            │
│     "properties": {                                              │
│       "task": {                                                  │
│         "type": "string",                                        │
│         "description": "Complete task description..."            │
│       }                                                          │
│       // ✅ NOTE: tool_call_id is NOT here!                     │
│       // InjectedToolCallId prevents it from being sent to LLM  │
│     },                                                           │
│     "required": ["task"]  // ✅ Only task is required           │
│   }                                                              │
│ }                                                                 │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

## Summary Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                  INJECTED PARAMETER PATTERN                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. SCHEMA: Declare with InjectedToolCallId + default=None     │
│     ↓                                                            │
│  2. VALIDATION: Pydantic recognizes as injected field           │
│     ↓                                                            │
│  3. INJECTION: Framework provides real value at runtime         │
│     ↓                                                            │
│  4. FUNCTION: Receives injected value as parameter              │
│     ↓                                                            │
│  5. USAGE: Use in ToolMessage for proper message pairing        │
│                                                                  │
│  ✅ Result: Clean tool_use/tool_result pairing in conversation │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## References

- **Implementation Guide**: `INJECTED_TOOL_CALL_ID_FIX.md`
- **Full Research Report**: `INJECTED_TOOL_CALL_ID_RESEARCH.md`
- **Stack Overflow**: Q79746960
- **GitHub Issue**: langchain-ai/langchain#31688
