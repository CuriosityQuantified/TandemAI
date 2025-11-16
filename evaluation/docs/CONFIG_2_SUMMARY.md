# Test Configuration 2: DeepAgent Supervisor with Conditional Routing

## Overview

Config 2 demonstrates a **traditional LangGraph conditional routing pattern** with a DeepAgent supervisor and base ReAct subagent.

### Key Characteristics

- **Supervisor**: DeepAgent with reflection (write_todos) and filesystem memory
- **Subagents**: Base ReAct agents using `langchain.agents.create_agent`
- **Routing**: Conditional edges with routing function (NOT Command.goto)
- **Tools**: Delegation tools return ToolMessage (NOT Command)
- **Model**: Claude Haiku 4.5 for all agents

---

## Graph Architecture

```
START → supervisor (DeepAgent)
         ↓
      delegation_tools (ToolNode)
         ↓ (conditional edge with routing function)
      researcher (ReAct) → END
         OR
      end (END)
```

### Graph Components

1. **supervisor** - DeepAgent node with:
   - FilesystemBackend for context management
   - MemorySaver checkpointer
   - write_todos tool for planning
   - Delegation tools

2. **delegation_tools** - ToolNode containing:
   - `delegate_to_researcher` tool

3. **researcher** - ReAct agent with:
   - Tavily search tool
   - File write/read tools
   - Task-specific system prompt

### Edge Configuration

| Source | Target | Type | Routing |
|--------|--------|------|---------|
| supervisor | delegation_tools | Regular | Direct |
| delegation_tools | researcher/end | Conditional | `route_after_delegation()` |
| researcher | END | Regular | Direct |

---

## Key Implementation Details

### 1. Delegation Tool (Returns String, NOT Command)

```python
@tool("delegate_to_researcher")
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> str:
    """Delegate research task - returns string for ToolMessage."""
    return f"✅ Routing to researcher subagent: {task[:100]}..."
```

**Important**:
- Returns `str` (not `Command`)
- LangGraph automatically wraps in ToolMessage
- `tool_call_id` injected for matching

### 2. Routing Function (Inspects tool_calls)

```python
def route_after_delegation(state: MessagesState) -> Literal["researcher", "end"]:
    """Route based on which delegation tool was called."""
    messages = state["messages"]

    # Find last AIMessage before ToolMessage
    last_ai_message = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            last_ai_message = msg
            break

    if not last_ai_message or not hasattr(last_ai_message, "tool_calls"):
        return "end"

    # Check tool_calls to determine routing
    for tool_call in last_ai_message.tool_calls:
        if tool_call.get("name") == "delegate_to_researcher":
            return "researcher"

    return "end"
```

**Key Points**:
- Inspects `tool_calls` attribute of last AIMessage
- Returns node name as string literal
- Must match one of the conditional edge options

### 3. Conditional Edge Configuration

```python
workflow.add_conditional_edges(
    "delegation_tools",           # Source node
    route_after_delegation,       # Routing function
    {
        "researcher": "researcher",  # Map return value to node
        "end": END                   # Map to END node
    }
)
```

**Conditional Edge Components**:
1. **Source node**: Node whose output triggers routing decision
2. **Routing function**: Function that inspects state and returns string
3. **Mapping dict**: Maps routing function return values to target nodes

---

## Agent Creation

### DeepAgent Supervisor

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

supervisor = create_deep_agent(
    model=llm,                           # ChatAnthropic model
    tools=delegation_tools,              # List of delegation tools
    backend=FilesystemBackend(root_dir=str(workspace_dir)),
    checkpointer=MemorySaver(),
    system_prompt="You are a research supervisor..."
)
```

**Parameters**:
- `model`: Language model (not `llm`)
- `tools`: Tool list
- `backend`: FilesystemBackend with `root_dir` parameter
- `checkpointer`: Memory persistence
- `system_prompt`: Instructions (not `instructions`)

### ReAct Subagent

```python
from langchain.agents import create_agent

researcher = create_agent(
    model=llm,                           # ChatAnthropic model
    tools=tools,                         # List of tools
    system_prompt="You are a research specialist..."
)
```

**Parameters**:
- `model`: Language model (not `llm`)
- `tools`: Tool list
- `system_prompt`: Instructions (not `prompt`)

---

## Routing Flow

### Execution Sequence

1. **User Input** → supervisor receives HumanMessage
2. **Supervisor Decision** → Creates AIMessage with tool_call
3. **ToolNode Execution** → Executes delegation tool, creates ToolMessage
4. **Conditional Routing** → `route_after_delegation()` inspects tool_calls
5. **Researcher Execution** → ReAct agent executes task
6. **Completion** → Returns to END

### Message Flow Example

```python
[
    HumanMessage(content="Research quantum computing..."),
    AIMessage(content="Delegating...", tool_calls=[{
        "name": "delegate_to_researcher",
        "args": {"task": "Research quantum..."},
        "id": "call_123"
    }]),
    ToolMessage(content="✅ Routing to researcher...", tool_call_id="call_123"),
    AIMessage(content="[Researcher's response]"),
    ...
]
```

### Routing Decision Points

1. **After ToolNode**: Routing function inspects last AIMessage
2. **Check tool_calls**: Looks for specific tool names
3. **Return target**: Maps to node name or END
4. **Graph routes**: Transitions to selected node

---

## Key Differences from Config 1

| Aspect | Config 1 (Command) | Config 2 (Conditional) |
|--------|-------------------|------------------------|
| **Tool Return** | Command object | String (wrapped in ToolMessage) |
| **Routing** | Command.goto field | Routing function |
| **Edge Type** | Regular edge | Conditional edge |
| **Routing Logic** | In tool function | In separate routing function |
| **State Inspection** | N/A | Inspects message history |

### Config 1 Pattern (Command.goto)
```python
# Tool returns Command
return Command(
    goto="researcher",
    update={"messages": [ToolMessage(...)]}
)

# Regular edge from delegation_tools
workflow.add_edge("delegation_tools", "researcher")
```

### Config 2 Pattern (Conditional Edge)
```python
# Tool returns string
return "✅ Routing to researcher..."

# Conditional edge with routing function
workflow.add_conditional_edges(
    "delegation_tools",
    route_after_delegation,
    {"researcher": "researcher", "end": END}
)
```

---

## Testing

### Quick Test (Graph Compilation)

```bash
python test_configs/quick_test_config_2.py
```

**Verifies**:
- Graph builds successfully
- All nodes present
- No import/syntax errors

### Full Test (Execution)

```bash
python test_configs/test_config_2_deepagent_supervisor_conditional.py
```

**Verifies**:
- Supervisor receives task
- Delegation tool called
- Routing function executes
- Researcher receives delegated task
- File output created

---

## Debugging Tips

### 1. Routing Function Not Called

**Symptom**: Graph doesn't route to researcher

**Checks**:
- Is conditional edge added correctly?
- Does routing function return valid option?
- Print debug statements in routing function

### 2. Tool Call Not Found

**Symptom**: Routing function can't find tool_calls

**Checks**:
- Is last message AIMessage?
- Does message have tool_calls attribute?
- Print message types and attributes

### 3. Wrong Node Reached

**Symptom**: Routes to END instead of researcher

**Checks**:
- Print routing function return value
- Verify mapping dict keys match return values
- Check tool_call name matching

---

## Common Errors and Solutions

### Error: `FilesystemBackend() got unexpected keyword argument 'workspace_dir'`

**Solution**: Use `root_dir` parameter:
```python
backend = FilesystemBackend(root_dir=str(workspace_dir))
```

### Error: `create_deep_agent() got unexpected keyword argument 'instructions'`

**Solution**: Use `system_prompt` parameter:
```python
create_deep_agent(model=llm, system_prompt="...", ...)
```

### Error: `create_agent() got unexpected keyword argument 'prompt'`

**Solution**: Use `system_prompt` parameter:
```python
create_agent(model=llm, system_prompt="...", ...)
```

---

## Use Cases

### When to Use Config 2 Pattern

✅ **Good for**:
- Complex routing logic based on state
- Multiple possible routing destinations
- Routing decisions need full message history
- Traditional LangGraph patterns preferred

❌ **Not ideal for**:
- Simple direct routing (use Command.goto)
- Routing decision known at tool execution time
- Minimizing routing complexity

---

## Performance Considerations

### Routing Function Efficiency

- **Fast**: Simple tool_call name check
- **Message iteration**: O(n) where n = message count
- **State access**: Full message history available

### Comparison to Command.goto

**Conditional Routing**:
- ➕ More flexible routing logic
- ➕ Can inspect entire conversation history
- ➖ Extra function call overhead
- ➖ Routing logic separate from tool

**Command.goto**:
- ➕ Routing decision in tool itself
- ➕ Simpler mental model
- ➖ Less flexible for complex decisions
- ➖ Cannot inspect full state

---

## Documentation References

### LangGraph Conditional Edges
- [Conditional Edges Guide](https://langchain-ai.github.io/langgraph/how-tos/branching/)
- [Graph API Reference](https://docs.langchain.com/oss/python/langgraph/graph-api)

### DeepAgents
- [DeepAgents Overview](https://docs.langchain.com/oss/python/deepagents/overview)
- [FilesystemBackend API](https://reference.langchain.com/python/deepagents/)

### LangChain Agents
- [create_agent Function](https://python.langchain.com/api_reference/langchain/agents.html)
- [Agent Migration Guide](https://blog.langchain.com/langchain-langgraph-1dot0/)

---

## Summary

Config 2 demonstrates **traditional conditional routing** in LangGraph:

1. **Tools return strings** wrapped in ToolMessage
2. **Routing function inspects** message history
3. **Conditional edge maps** return values to nodes
4. **DeepAgent supervisor** with reflection capabilities
5. **ReAct subagents** for task execution

This pattern provides **maximum flexibility** for routing decisions while following **established LangGraph conventions**.

---

**Created**: November 12, 2025
**Pattern**: Conditional Edge Routing
**Status**: ✅ Compiled Successfully
**Model**: Claude Haiku 4.5
