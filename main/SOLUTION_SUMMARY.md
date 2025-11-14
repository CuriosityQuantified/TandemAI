# TodoListMiddleware Visibility Solution - Quick Reference

## TL;DR

**Problem**: User reports not seeing todos in streaming output.

**Root Cause**: TodoListMiddleware provides the `write_todos` tool but doesn't automatically create todos. The agent decides whether to use it based on task complexity.

**Original Code Status**: ✅ **CORRECT** - No bug in streaming code.

**Solution**: Enhanced version with better visibility and stronger planning guidance.

## Quick Fix (Minimum Changes)

If you want to keep using the original `module-2-2-simple.py`, just update the system prompt:

```python
system_prompt="""AI research assistant with web search and filesystem capabilities.

Tools:
- tavily_search: Web search for current information
- write_todos: Plan and track tasks
- Filesystem: ls, read_file, write_file, edit_file, glob, grep

PLANNING PROTOCOL:
⚠️ MANDATORY: For ANY task with 3+ steps, use write_todos FIRST before taking action.
⚠️ REQUIRED: Update todo status (pending → in_progress → completed) as you work.

Example workflow:
User: "Research AI and save report to file"

Step 1: write_todos([
  {content: "Research AI using tavily_search", status: "pending"},
  {content: "Save report to /workspace/report.md", status: "pending"}
])

Step 2: write_todos([
  {content: "Research AI using tavily_search", status: "in_progress"},
  {content: "Save report to /workspace/report.md", status: "pending"}
])

Step 3: (perform research with tavily_search)

Step 4: write_todos([
  {content: "Research AI using tavily_search", status: "completed"},
  {content: "Save report to /workspace/report.md", status: "in_progress"}
])

Step 5: (save with write_file)

Step 6: write_todos([
  {content: "Research AI using tavily_search", status: "completed"},
  {content: "Save report to /workspace/report.md", status: "completed"}
])

File writing rules:
- ALL file operations MUST use /workspace/ prefix
- write_file requires BOTH file_path AND content parameters in ONE call
"""
```

**Why This Works**:
- ⚠️ Visual warning symbols grab attention
- "MANDATORY" and "REQUIRED" are directive
- Concrete numbered example shows exact flow
- Agent is more likely to follow explicit protocol

## Enhanced Solution (Recommended)

Use `module-2-2-enhanced-todos.py` which includes:

### 1. Enhanced Display Features

```python
# Shows when planning happens
🎯🎯🎯🎯🎯🎯🎯
📋 PLANNING: Creating 3 tasks
1. ⏳ [PENDING] Research quantum computing
2. ⏳ [PENDING] Analyze key players
3. ⏳ [PENDING] Save report to file
🎯🎯🎯🎯🎯🎯🎯

# Shows status changes in real-time
📝 TODO STATUS UPDATE:
   Total: 3 | ✅ Completed: 1 | ▶️ In Progress: 1 | ⏳ Pending: 1

▶️ ACTIVE TASKS:
   • Analyze key players in quantum industry

# Shows final summary
📋 FINAL TODO SUMMARY:
   Total Tasks: 3
   Completed: 3/3
   🎉 ALL TASKS COMPLETED!
```

### 2. Key Code Changes

**A. Detect write_todos tool calls**:
```python
if tool_name == 'write_todos':
    args = tool_call.get('args', {})
    if 'todos' in args:
        new_todos = args['todos']
        print(f"\n  {'🎯' * 30}")
        print(f"  📋 PLANNING: Creating {len(new_todos)} tasks")
        for i, todo in enumerate(new_todos, 1):
            status_icon = {
                "pending": "⏳",
                "in_progress": "▶️",
                "completed": "✅"
            }.get(todo.get('status'), "❓")
            print(f"  {i}. {status_icon} [{todo.get('status', '').upper()}] {todo.get('content', '')}")
```

**B. Track status changes**:
```python
current_todos = []

# In streaming loop:
if "todos" in node_update:
    todos = node_update["todos"]
    if todos and todos != current_todos:  # Detect changes
        current_todos = todos

        # Count by status
        pending = sum(1 for t in todos if t.get('status') == 'pending')
        in_progress = sum(1 for t in todos if t.get('status') == 'in_progress')
        completed = sum(1 for t in todos if t.get('status') == 'completed')

        print(f"\n  📝 TODO STATUS UPDATE:")
        print(f"     Total: {len(todos)} | ✅ {completed} | ▶️ {in_progress} | ⏳ {pending}")
```

**C. Show active tasks**:
```python
active = [t for t in todos if t.get('status') == 'in_progress']
if active:
    print(f"\n  ▶️ ACTIVE TASKS:")
    for todo in active:
        print(f"     • {todo.get('content', '')[:70]}")
```

**D. Final summary**:
```python
if "todos" in result and result["todos"]:
    todos = result["todos"]
    completed = sum(1 for t in todos if t.get('status') == 'completed')
    print(f"\n📋 FINAL TODO SUMMARY:")
    print(f"   Total Tasks: {len(todos)}")
    print(f"   Completed: {completed}/{len(todos)}")

    if completed == len(todos):
        print(f"   🎉 ALL TASKS COMPLETED!")
```

## Testing Your Implementation

### Test 1: Verify Todos Are Created

```python
from module-2-2-enhanced-todos import run_agent_task

result = run_agent_task(
    "Create a plan with 3 steps: research, analyze, report",
    thread_id="test"
)

# Look for:
# ✅ "📋 PLANNING: Creating 3 tasks"
# ✅ List of 3 todos with status
```

### Test 2: Multi-Step Task

```python
result = run_agent_task(
    """Research quantum computing breakthroughs in 2024,
    analyze their impact, and save a report to /workspace/quantum_2024.md""",
    thread_id="complex"
)

# Look for:
# ✅ Planning announcement
# ✅ Status updates as agent works
# ✅ Active task indicators
# ✅ Final completion summary
```

### Test 3: Simple Task (Should Skip Planning)

```python
result = run_agent_task(
    "What is 2 + 2?",
    thread_id="simple"
)

# Expected: No planning (too simple)
# This is correct behavior!
```

## Debugging Checklist

If todos still aren't appearing:

- [ ] **Check for write_todos calls**: Look for "🔧 TOOL CALL: write_todos" in output
- [ ] **Verify task complexity**: Is it really 3+ steps? Simple tasks won't trigger planning
- [ ] **Check system prompt**: Does it strongly encourage planning?
- [ ] **Try explicit planning**: Add "Create a plan, then..." to query
- [ ] **Verify streaming mode**: Use `stream_mode="updates"` (default in examples)
- [ ] **Check middleware**: Confirm TodoListMiddleware is enabled (it is by default in DeepAgents)

## Common Misconceptions

### ❌ "TodoListMiddleware automatically plans tasks"
**Reality**: It only provides the `write_todos` tool. Agent decides whether to use it.

### ❌ "If todos exist, they should always appear in streaming"
**Reality**: They do appear, but only if the agent creates them in the first place.

### ❌ "The streaming code is broken"
**Reality**: The original code is correct. Todos appear in the `tools` node update.

### ❌ "I need to change streaming mode to see todos"
**Reality**: `stream_mode="updates"` works fine. All modes show todos when they exist.

## Files Reference

| File | Purpose |
|------|---------|
| `module-2-2-simple.py` | Original implementation (code is correct) |
| `module-2-2-enhanced-todos.py` | Enhanced version with better visibility |
| `TODO_VISIBILITY_ANALYSIS.md` | Comprehensive technical analysis |
| `SOLUTION_SUMMARY.md` | This quick reference (you are here) |
| `test_simple_todo.py` | Test basic todo creation |
| `test_streaming_modes.py` | Compare different streaming modes |
| `test_real_scenario.py` | Test with realistic queries |

## When to Use Each File

**Use `module-2-2-simple.py` when**:
- You want minimal code
- You understand todos may not appear for simple tasks
- You're okay with basic display

**Use `module-2-2-enhanced-todos.py` when**:
- You want maximum visibility into planning
- You're building user-facing applications
- You need clear progress indicators
- You want stronger planning encouragement

## Key Takeaway

**The streaming code was never broken.** TodoListMiddleware is working as designed. Whether todos appear depends on whether the agent judges the task complex enough to warrant planning. The enhanced version doesn't change this fundamental behavior - it just makes planning more visible when it does happen and encourages the agent to plan more often through stronger system prompts.

## Next Steps

1. Try running `module-2-2-enhanced-todos.py` with the example queries
2. Experiment with different query complexities
3. Observe which queries trigger planning and which don't
4. Adjust system prompt based on your specific use case
5. Consider adding explicit planning instructions for critical workflows

## Support

If you continue to have issues:

1. **Capture streaming output**: Save full console output to a file
2. **Check for tool calls**: Search for "write_todos" in the output
3. **Review system prompt**: Ensure planning guidance is clear
4. **Test with explicit planning**: Try "First create a plan, then..."
5. **Share results**: Include query, output, and agent configuration

---

**Remember**: TodoListMiddleware empowers agents with planning capabilities, but respects their autonomy in deciding when planning is beneficial. This is a feature, not a bug!
