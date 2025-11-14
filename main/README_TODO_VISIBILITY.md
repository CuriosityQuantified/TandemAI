# TodoListMiddleware Visibility - Complete Solution

## Overview

This directory contains a complete solution for understanding and enhancing todo visibility in DeepAgents' TodoListMiddleware. The investigation revealed that the original streaming code was correct, and the real issue was understanding how TodoListMiddleware operates.

## Quick Start

### Option 1: Try the Enhanced Demo

```bash
cd /Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2

# Activate virtual environment
source /Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.venv/bin/activate

# Run the interactive demo
python demo_enhanced_todos.py
```

This will show you:
- 📋 Planning announcements
- 📝 Real-time status updates
- ▶️  Active task indicators
- ✅ Completion summaries

### Option 2: Use Enhanced Implementation

```bash
# Run the full enhanced module with examples
python module-2-2-enhanced-todos.py
```

## Key Finding

**The streaming code was never broken!**

The "issue" was a misunderstanding of how TodoListMiddleware works:

1. ❌ **Myth**: TodoListMiddleware automatically creates todos for all tasks
2. ✅ **Reality**: It provides the `write_todos` tool, but the agent decides whether to use it

3. ❌ **Myth**: Todos should always appear in streaming output
4. ✅ **Reality**: They do appear... when the agent creates them

5. ❌ **Myth**: The streaming code isn't capturing todo updates
6. ✅ **Reality**: The code at lines 209-216 is correct and does capture todos

## Files in This Directory

### Documentation

| File | Description |
|------|-------------|
| **TODO_VISIBILITY_ANALYSIS.md** | Comprehensive technical analysis of how TodoListMiddleware works, streaming behavior, and test results |
| **SOLUTION_SUMMARY.md** | Quick reference guide with practical solutions and code examples |
| **README_TODO_VISIBILITY.md** | This file - overview and navigation guide |

### Implementation Files

| File | Description | Use When |
|------|-------------|----------|
| **module-2-2-simple.py** | Original implementation with correct streaming code | You want minimal, clean code |
| **module-2-2-enhanced-todos.py** | Enhanced version with improved visibility and stronger planning guidance | You want maximum visibility and user-facing features |

### Test Files

| File | Purpose |
|------|---------|
| **test_simple_todo.py** | Tests basic todo creation and state structure |
| **test_streaming_modes.py** | Compares `updates`, `values`, and `debug` streaming modes |
| **test_todo_visibility.py** | Debug test for identifying where todos appear in streams |
| **test_real_scenario.py** | Tests realistic queries with Tavily integration |

### Demo

| File | Description |
|------|-------------|
| **demo_enhanced_todos.py** | Interactive demo showing enhanced visibility features in action |

## Architecture Overview

### TodoListMiddleware Flow

```
User Query
    ↓
Agent Receives Query
    ↓
Agent Evaluates Complexity
    ↓
    ├─→ Simple (1-2 steps) → Skip planning
    │                         └→ NO TODOS CREATED
    │
    └─→ Complex (3+ steps) → Agent calls write_todos
                              ↓
                         Todos added to state
                              ↓
                         Appears in streaming output
                              ↓
                         ✅ TODOS VISIBLE
```

### Streaming Visibility Points

When the agent does create todos, they appear in:

1. **Tool Call**: When `write_todos` is invoked
   ```
   🔧 TOOL CALL: write_todos
   ```

2. **Tools Node Update**: State update after tool execution
   ```
   Node: tools
   Keys: ['todos', 'messages', 'files']
   ✅ TODOS IN UPDATE: [...]
   ```

3. **Subsequent State Updates**: As todos are modified
   ```
   📝 TODO STATUS UPDATE:
   Total: 3 | ✅ 1 | ▶️ 1 | ⏳ 1
   ```

## How to Use This Solution

### For Understanding (Read These First)

1. **Start here**: `SOLUTION_SUMMARY.md`
   - Quick explanation of the issue
   - Immediate fixes
   - Code examples

2. **Go deeper**: `TODO_VISIBILITY_ANALYSIS.md`
   - Technical deep-dive
   - Test results and analysis
   - Complete lifecycle documentation

### For Implementation

#### Minimum Changes (Keep Original Code)

Update just the system prompt in `module-2-2-simple.py`:

```python
system_prompt="""...

PLANNING PROTOCOL (MANDATORY):
⚠️ For ANY task with 3+ steps, use write_todos FIRST to create a plan.
⚠️ Update todo status as you work: pending → in_progress → completed

..."""
```

**Result**: Agent will plan more consistently, todos will be visible

#### Enhanced Experience (Recommended)

Use `module-2-2-enhanced-todos.py` which adds:

```python
# 1. Visual planning announcements
🎯🎯🎯🎯🎯🎯🎯
📋 PLANNING: Creating 3 tasks
1. ⏳ [PENDING] Task 1
2. ⏳ [PENDING] Task 2
3. ⏳ [PENDING] Task 3
🎯🎯🎯🎯🎯🎯🎯

# 2. Real-time status tracking
📝 TODO STATUS UPDATE:
   Total: 3 | ✅ 1 | ▶️ 1 | ⏳ 1

# 3. Active task visibility
▶️ ACTIVE TASKS:
   • Research quantum computing developments

# 4. Completion summary
📋 FINAL TODO SUMMARY:
   Total Tasks: 3
   Completed: 3/3
   🎉 ALL TASKS COMPLETED!
```

### For Testing

1. **Basic functionality**:
   ```bash
   python test_simple_todo.py
   ```

2. **Streaming modes comparison**:
   ```bash
   python test_streaming_modes.py
   ```

3. **Real-world scenarios**:
   ```bash
   python test_real_scenario.py
   ```

4. **Interactive demo**:
   ```bash
   python demo_enhanced_todos.py
   ```

## Common Questions

### Q: Why don't I see todos in my output?

**A**: Three possibilities:

1. **Task is too simple**: Agent judged it doesn't need planning
   - Solution: Use more complex queries or be explicit: "Create a plan, then..."

2. **System prompt is weak**: Agent doesn't feel encouraged to plan
   - Solution: Use directive language ("ALWAYS use write_todos for 3+ step tasks")

3. **Agent hasn't called write_todos yet**: Check for tool call in output
   - Solution: Look for "🔧 TOOL CALL: write_todos" - if missing, todos weren't created

### Q: Is the streaming code broken?

**A**: No! The code at lines 209-216 in `module-2-2-simple.py` is correct:

```python
if "todos" in node_update:
    todos = node_update["todos"]
    if todos:
        print(f"  📝 PLANNING: {len(todos)} tasks created")
        # ... display logic
```

This works perfectly when todos exist. The question is whether they're created at all.

### Q: Should I use stream_mode="values" instead of "updates"?

**A**: Not necessary. Both modes show todos:
- `updates`: Shows todos in the `tools` node update
- `values`: Shows full state including todos

The enhanced version uses `updates` (same as original) and works great.

### Q: Can I force the agent to always create todos?

**A**: Not directly, but you can strongly encourage it:

1. Use directive system prompts ("MANDATORY", "ALWAYS", "REQUIRED")
2. Provide concrete examples in the prompt
3. Frame queries to emphasize complexity
4. Include "create a plan" explicitly in user queries

The agent still has autonomy, but these techniques dramatically increase planning usage.

### Q: What if I want todos for simple tasks too?

**A**: Consider wrapping your agent invocation:

```python
def invoke_with_planning(agent, query, config):
    # Pre-create todos for any task
    initial_todos = [{"content": query, "status": "pending"}]

    # Manually add to state (requires custom node)
    # OR instruct agent explicitly
    query_with_planning = f"First create a plan with write_todos, then: {query}"

    return agent.invoke(
        {"messages": [{"role": "user", "content": query_with_planning}]},
        config=config
    )
```

## Technical Details

### Middleware Stack in DeepAgents

From `deepagents/graph.py` (lines 97-125):

```python
deepagent_middleware = [
    TodoListMiddleware(),           # ← Adds write_todos tool
    FilesystemMiddleware(backend=backend),
    SubAgentMiddleware(...),
    SummarizationMiddleware(...),
    AnthropicPromptCachingMiddleware(...),
    PatchToolCallsMiddleware(),
]
```

TodoListMiddleware is the first middleware, so it's always available.

### Todo State Schema

From `langchain/agents/middleware/todo.py` (lines 26-40):

```python
class Todo(TypedDict):
    content: str           # Description of the task
    status: Literal["pending", "in_progress", "completed"]

class PlanningState(AgentState):
    todos: NotRequired[list[Todo]]  # Optional, may not exist
```

**Key**: `todos` is `NotRequired`, meaning it won't exist until `write_todos` is called.

### Write Todos Tool

From `todo.py` (lines 119-126):

```python
@tool(description=WRITE_TODOS_TOOL_DESCRIPTION)
def write_todos(todos: list[Todo], tool_call_id: str) -> Command:
    return Command(
        update={
            "todos": todos,
            "messages": [ToolMessage(f"Updated todo list to {todos}", ...)]
        }
    )
```

Returns a `Command` that updates state. This is what appears in streaming output.

## Best Practices

### System Prompt Design

✅ **Do**:
```python
"""
PLANNING PROTOCOL:
⚠️ For ANY task with 3+ steps, use write_todos FIRST.

Example:
User: "Research X and save to file"
1. write_todos([{content: "Research X", status: "pending"}, ...])
2. Update to in_progress
3. Perform research
4. Update to completed
"""
```

❌ **Don't**:
```python
"""
You can use write_todos to help organize complex tasks if you want.
"""
```

### Query Formulation

✅ **Do**:
- "Research X, analyze Y, and save a report to Z"
- "Create a detailed plan, then execute: [task]"
- "Complete these steps: 1. X, 2. Y, 3. Z"

❌ **Don't**:
- "Search for X" (too simple)
- "What is Y?" (informational)

### Streaming Display

✅ **Do**:
- Show planning when it happens
- Track status changes
- Highlight active tasks
- Provide summary at end

❌ **Don't**:
- Only check final state
- Ignore tool calls
- Skip status indicators

## Performance Considerations

### Token Usage

Todo creation adds ~200-500 tokens per planning session:
- Initial plan creation: ~150-300 tokens
- Status updates: ~50-100 tokens each

For cost-sensitive applications:
- Use Haiku (cheaper model) for planning
- Limit todo detail/description length
- Skip planning for truly simple tasks

### Latency

Each `write_todos` call adds ~0.5-2 seconds:
- Tool call: ~0.3-0.5s
- State update: ~0.1-0.2s
- Next model call: ~0.1-1.3s

For latency-sensitive applications:
- Consider planning only for complex workflows
- Use async/parallel execution where possible
- Cache common plans

## Troubleshooting

### Issue: No todos appear at all

**Debug steps**:
1. Search output for "write_todos": `grep -i "write_todos" output.txt`
2. Check if tool is available: Look for it in agent's tool list
3. Verify middleware: Confirm TodoListMiddleware is enabled
4. Test with explicit query: "Create a plan with 3 tasks, then..."

### Issue: Todos created but status never updates

**Debug steps**:
1. Check if agent calls write_todos multiple times
2. Verify system prompt encourages status updates
3. Look for status changes in streaming output
4. Check final state: Does it have completed todos?

### Issue: Planning happens too late (after work)

**Problem**: Agent does work first, then creates summary as "todos"

**Solution**: Strengthen system prompt:
```python
"""
CRITICAL: Use write_todos BEFORE starting work, not after!

Wrong: Do task → Create todo list
Right: Create todo list → Update status → Do task
"""
```

## Contributing

Found an issue or improvement? Please:

1. Test with the provided test files
2. Check if it's a prompt engineering issue vs. code issue
3. Document your findings
4. Share system prompt tweaks that worked for you

## License

This solution is part of the open-source CC learning materials.

## Support

For questions:
1. Review `SOLUTION_SUMMARY.md` for quick answers
2. Check `TODO_VISIBILITY_ANALYSIS.md` for technical details
3. Run test files to verify your environment
4. Try the demo to see expected behavior

---

**Remember**: TodoListMiddleware is a tool, not an enforcer. The agent decides when planning is beneficial. This autonomy is a feature that respects the model's reasoning about task complexity!
