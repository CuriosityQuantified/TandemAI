"""
MODULE 2.2: Deep Agents with Enhanced Todo Visibility
=====================================================

This version improves todo visibility in streaming output by:
1. Showing todo creation when write_todos is called
2. Displaying todos in state updates
3. Tracking todo status changes
4. Showing active todos during execution
5. Providing todo summary at completion

Based on: module-2-2-simple.py with enhanced streaming
"""

import os
from dotenv import load_dotenv

# DeepAgents imports
from deepagents import create_deep_agent
from deepagents.backends import (
    CompositeBackend,
    StateBackend,
    FilesystemBackend
)

# LangChain imports
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver

# Production tool imports
from langchain_tavily import TavilySearch

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7,
)

print("\n" + "=" * 80)
print("MODULE 2.2: Enhanced Todo Visibility in DeepAgent Streaming")
print("=" * 80)
print(f"🤖 Model: Claude Haiku 4.5")
print(f"🔧 Tool: Tavily (web search)")
print(f"📋 Feature: TodoListMiddleware with enhanced streaming visibility")
print("=" * 80)

# ============================================================================
# PRODUCTION TOOLS
# ============================================================================

tavily_search = TavilySearch(
    max_results=5,
    api_key=os.getenv("TAVILY_API_KEY"),
)

print("\n🔧 Production Tool Initialized:")
print("  ✅ Tavily Search - Web search with up-to-date information")

# ============================================================================
# STORAGE BACKEND
# ============================================================================

workspace_dir = "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/agent_workspace"
os.makedirs(workspace_dir, exist_ok=True)

def create_hybrid_backend(rt):
    """Hybrid storage: ephemeral + filesystem."""
    return CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/workspace/": FilesystemBackend(root_dir=workspace_dir, virtual_mode=True),
        }
    )

print("\n💾 Hybrid Backend: /workspace/ → Filesystem, Default → Ephemeral")

# ============================================================================
# DEEP AGENT CREATION
# ============================================================================

print("\n🤖 Creating DeepAgent with TodoListMiddleware...")

production_tools = [tavily_search]

agent = create_deep_agent(
    model=model,
    tools=production_tools,
    backend=create_hybrid_backend,
    checkpointer=MemorySaver(),
    system_prompt="""AI research assistant with web search and filesystem capabilities.

Tools:
- tavily_search: Web search for current information
- write_todos: Plan and track multi-step tasks (USE THIS for complex tasks!)
- Filesystem: ls, read_file, write_file, edit_file, glob, grep

CRITICAL Instructions:

1. PLANNING: For ANY task with 3+ steps, ALWAYS use write_todos FIRST to create a plan
2. TODO UPDATES: Update todos as you work - mark tasks in_progress and completed
3. FILE WRITING: write_file requires BOTH file_path AND content in ONE call
4. FILE PATHS: ALL file operations MUST use /workspace/ prefix

Workflow:
1. Complex task? → Use write_todos to create plan
2. Start task → Update todo status to in_progress
3. Complete task → Update todo status to completed
4. Research → Use tavily_search
5. Save results → Use write_file with /workspace/ prefix

Example:
Query: "Research AI and save report"
1. Call write_todos([{content: "Research AI", status: "pending"}, {content: "Save report", status: "pending"}])
2. Update first todo to in_progress
3. Use tavily_search for research
4. Update first todo to completed, second to in_progress
5. Use write_file to save
6. Update second todo to completed
"""
)

print("✅ DeepAgent Ready with enhanced todo tracking\n")

# ============================================================================
# ENHANCED EXECUTION FUNCTION WITH TODO VISIBILITY
# ============================================================================

def run_agent_task(query: str, thread_id: str = "demo"):
    """Execute agent task with enhanced todo visibility."""

    print("\n" + "🎯" * 40)
    print(f"USER QUERY: {query}")
    print("🎯" * 40)

    config = {"configurable": {"thread_id": thread_id}}

    print("\n🚀 Streaming DeepAgent execution...\n")
    print("─" * 80)

    step_count = 0
    current_todos = []
    todos_created = False

    # Stream with updates mode for real-time visibility
    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
        stream_mode="updates"
    ):
        step_count += 1

        # chunk is a dict with node name as key
        for node_name, node_update in chunk.items():
            if node_name == "__start__" or node_name == "__end__":
                continue

            # Skip if update is None or empty
            if not node_update:
                continue

            print(f"\n📍 Node: {node_name}")

            # Check for messages in the update
            if "messages" in node_update:
                messages = node_update["messages"]
                for msg in messages:
                    # Check for AI message with tool calls
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            tool_name = tool_call.get('name', 'unknown')
                            print(f"  🔧 TOOL CALL: {tool_name}")

                            # Special handling for write_todos
                            if tool_name == 'write_todos':
                                args = tool_call.get('args', {})
                                if 'todos' in args:
                                    new_todos = args['todos']
                                    print(f"\n  {'🎯' * 30}")
                                    print(f"  📋 PLANNING: Creating {len(new_todos)} tasks")
                                    print(f"  {'🎯' * 30}")
                                    for i, todo in enumerate(new_todos, 1):
                                        status = todo.get('status', 'pending')
                                        content = todo.get('content', '')
                                        status_icon = "⏳" if status == "pending" else "▶️" if status == "in_progress" else "✅"
                                        print(f"  {i}. {status_icon} [{status.upper()}] {content}")
                                    print(f"  {'🎯' * 30}\n")
                                    todos_created = True

                            # Show abbreviated args for other tools
                            elif tool_name != 'write_todos':
                                args = tool_call.get('args', {})
                                if args:
                                    arg_items = list(args.items())[:2]
                                    arg_str = ", ".join(f"{k}={str(v)[:50]}" for k, v in arg_items)
                                    print(f"     Args: {arg_str}...")

                    # Check for tool message (results)
                    elif hasattr(msg, "tool_call_id") and hasattr(msg, "content"):
                        content = str(msg.content)
                        # Don't show full content for write_todos (redundant)
                        if "Updated todo list" not in content:
                            preview = content[:150] if len(content) > 150 else content
                            print(f"  📊 TOOL RESULT:")
                            print(f"     {preview}{'...' if len(content) > 150 else ''}")

            # Check for todos in state update (shows status changes)
            if "todos" in node_update:
                todos = node_update["todos"]
                if todos:
                    # Compare with previous todos to detect changes
                    if todos != current_todos:
                        current_todos = todos

                        # Count statuses
                        pending = sum(1 for t in todos if t.get('status') == 'pending')
                        in_progress = sum(1 for t in todos if t.get('status') == 'in_progress')
                        completed = sum(1 for t in todos if t.get('status') == 'completed')

                        print(f"\n  📝 TODO STATUS UPDATE:")
                        print(f"     Total: {len(todos)} | ✅ Completed: {completed} | ▶️ In Progress: {in_progress} | ⏳ Pending: {pending}")

                        # Show active (in_progress) todos
                        active = [t for t in todos if t.get('status') == 'in_progress']
                        if active:
                            print(f"\n  ▶️  ACTIVE TASKS:")
                            for todo in active:
                                content = todo.get('content', '')
                                print(f"     • {content[:70]}")

    print("\n" + "─" * 80)
    print(f"✅ Completed in {step_count} stream events\n")

    # Get final state
    result = agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config=config
    )

    # Display final result
    if result and "messages" in result:
        final_message = result["messages"][-1]
        print("=" * 80)
        print("📊 FINAL RESULT")
        print("=" * 80)
        print(final_message.content if hasattr(final_message, "content") else str(final_message))
        print("=" * 80)

    # Display final todo summary
    if "todos" in result and result["todos"]:
        todos = result["todos"]
        completed_count = sum(1 for t in todos if t.get('status') == 'completed')
        print(f"\n📋 FINAL TODO SUMMARY:")
        print(f"   Total Tasks: {len(todos)}")
        print(f"   Completed: {completed_count}/{len(todos)}")

        if completed_count == len(todos):
            print(f"   🎉 ALL TASKS COMPLETED!")
        else:
            incomplete = [t for t in todos if t.get('status') != 'completed']
            print(f"\n   ⚠️  Incomplete Tasks:")
            for todo in incomplete:
                status = todo.get('status', 'unknown')
                content = todo.get('content', '')
                print(f"      [{status}] {content}")

    return result


# ============================================================================
# EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("\n\n" + "🔬" * 40)
    print("EXAMPLE 1: Simple Web Search (No Planning)")
    print("🔬" * 40)

    result1 = run_agent_task(
        "Search for the latest updates on LangChain v1.0 and summarize the key features",
        thread_id="simple-search"
    )

    print("\n\n" + "🔬" * 40)
    print("EXAMPLE 2: Research and Save (Should Trigger Planning)")
    print("🔬" * 40)

    result2 = run_agent_task(
        "Research DeepAgents v0.2 using web search and save a summary to /workspace/deepagents_summary.md",
        thread_id="research-with-save"
    )

    print("\n\n" + "🔬" * 40)
    print("EXAMPLE 3: Complex Multi-Step Task (Should Definitely Plan)")
    print("🔬" * 40)

    result3 = run_agent_task(
        """Research the benefits of agentic AI systems, create a comparison with traditional AI,
        and save a detailed report to /workspace/agentic_ai_report.md. Include sections on:
        1. Key benefits of agentic systems
        2. Comparison with traditional approaches
        3. Real-world applications
        4. Future trends""",
        thread_id="complex-planning"
    )

# ============================================================================
# SUMMARY
# ============================================================================

if __name__ == "__main__":
    print("\n\n" + "=" * 80)
    print("MODULE 2.2 SUMMARY - ENHANCED TODO VISIBILITY")
    print("=" * 80)

    summary = """
✅ Key Enhancements:

1. **Planning Visibility**
   - Shows when write_todos is called
   - Displays all planned tasks with status
   - Uses visual indicators (⏳ pending, ▶️ in_progress, ✅ completed)

2. **Real-Time Todo Updates**
   - Tracks todo status changes during execution
   - Shows active tasks being worked on
   - Provides running count of task completion

3. **Final Todo Summary**
   - Complete task breakdown at end
   - Highlights incomplete tasks
   - Celebrates completion when all done

4. **Better Tool Call Display**
   - Abbreviated arguments for readability
   - Special formatting for write_todos
   - Filters redundant todo confirmation messages

📊 Todo State Tracking:

Todos are tracked through multiple streaming events:
- **Tool Call**: When agent calls write_todos (shows intention)
- **Tools Node**: When todos are added to state (shows creation)
- **Status Updates**: When agent updates todo status (shows progress)

🔍 Debugging Tips:

If todos still aren't visible:
1. Check if agent is actually calling write_todos (look for TOOL CALL: write_todos)
2. Verify system prompt encourages planning for complex tasks
3. Ensure task is complex enough (3+ steps) to trigger planning
4. Try explicitly asking agent to "create a plan" in the query

💡 Why Todos May Not Appear:

TodoListMiddleware doesn't force todo creation - it just provides the tool.
The agent decides whether to use write_todos based on:
- Task complexity
- System prompt guidance
- Model's reasoning about whether planning is beneficial

For tasks the agent deems simple (1-2 steps), it may skip planning.
"""

    print(summary)
    print("=" * 80)

    print("\n✨ Module 2.2 Complete with Enhanced Todo Visibility! ✨\n")
