#!/usr/bin/env python
"""
Demo: Enhanced Todo Visibility in Action

This script demonstrates the enhanced todo visibility features by running
a complex task that will trigger planning and status updates.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langchain_anthropic import ChatAnthropic
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# ============================================================================
# SETUP
# ============================================================================

print("\n" + "=" * 80)
print("🎬 DEMO: Enhanced Todo Visibility with TodoListMiddleware")
print("=" * 80)
print("\nThis demo will show:")
print("  1. 📋 Planning announcement when todos are created")
print("  2. 📝 Real-time status updates as tasks progress")
print("  3. ▶️  Active task tracking during execution")
print("  4. ✅ Completion summary at the end")
print("=" * 80)

input("\n👉 Press ENTER to start the demo...")

model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7,
)

workspace_dir = "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/agent_workspace"
os.makedirs(workspace_dir, exist_ok=True)

def create_hybrid_backend(rt):
    return CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/workspace/": FilesystemBackend(root_dir=workspace_dir, virtual_mode=True),
        }
    )

tavily_search = TavilySearch(
    max_results=5,
    api_key=os.getenv("TAVILY_API_KEY"),
)

agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    backend=create_hybrid_backend,
    checkpointer=MemorySaver(),
    system_prompt="""AI research assistant with web search and filesystem capabilities.

PLANNING PROTOCOL (MANDATORY):
⚠️ For ANY task with 3+ steps, use write_todos FIRST to create a plan.
⚠️ Update todo status as you work: pending → in_progress → completed

Tools:
- tavily_search: Web search for current information
- write_todos: ALWAYS use this for multi-step tasks
- write_file: Save content (MUST use /workspace/ prefix)

Workflow Example:
1. Complex task arrives
2. Call write_todos to create plan
3. For each task:
   - Update to in_progress
   - Perform work
   - Update to completed
4. Provide summary

CRITICAL: Use write_todos at the START, not after work is done!
"""
)

# ============================================================================
# ENHANCED STREAMING FUNCTION
# ============================================================================

def run_with_enhanced_visibility(query: str, thread_id: str = "demo"):
    """Execute with enhanced todo visibility."""

    print("\n" + "🎯" * 40)
    print(f"QUERY: {query}")
    print("🎯" * 40)

    config = {"configurable": {"thread_id": thread_id}}
    print("\n🚀 Executing with enhanced todo visibility...\n")
    print("─" * 80)

    step_count = 0
    current_todos = []

    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
        stream_mode="updates"
    ):
        step_count += 1

        for node_name, node_update in chunk.items():
            if node_name in ("__start__", "__end__") or not node_update:
                continue

            print(f"\n📍 Node: {node_name}")

            # Process messages
            if "messages" in node_update:
                for msg in node_update["messages"]:
                    # Tool calls
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            tool_name = tool_call.get('name', 'unknown')

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
                                        icon = {"pending": "⏳", "in_progress": "▶️", "completed": "✅"}.get(status, "❓")
                                        print(f"  {i}. {icon} [{status.upper()}] {content}")
                                    print(f"  {'🎯' * 30}\n")
                            else:
                                # Show other tool calls
                                print(f"  🔧 TOOL CALL: {tool_name}")
                                args = tool_call.get('args', {})
                                if args and tool_name != 'write_todos':
                                    arg_items = list(args.items())[:2]
                                    arg_str = ", ".join(f"{k}={str(v)[:40]}" for k, v in arg_items)
                                    print(f"     Args: {arg_str}...")

                    # Tool results (skip write_todos confirmations)
                    elif hasattr(msg, "tool_call_id") and hasattr(msg, "content"):
                        content = str(msg.content)
                        if "Updated todo list" not in content:
                            preview = content[:120]
                            print(f"  📊 TOOL RESULT: {preview}...")

            # Todo status updates
            if "todos" in node_update:
                todos = node_update["todos"]
                if todos and todos != current_todos:
                    current_todos = todos

                    # Status counts
                    pending = sum(1 for t in todos if t.get('status') == 'pending')
                    in_progress = sum(1 for t in todos if t.get('status') == 'in_progress')
                    completed = sum(1 for t in todos if t.get('status') == 'completed')

                    print(f"\n  📝 TODO STATUS UPDATE:")
                    print(f"     Total: {len(todos)} | ✅ {completed} | ▶️ {in_progress} | ⏳ {pending}")

                    # Show active tasks
                    active = [t for t in todos if t.get('status') == 'in_progress']
                    if active:
                        print(f"\n  ▶️  ACTIVE TASKS:")
                        for todo in active:
                            print(f"     • {todo.get('content', '')[:65]}")

    print("\n" + "─" * 80)
    print(f"✅ Completed in {step_count} stream events\n")

    # Final state
    result = agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config=config
    )

    # Final summary
    if "todos" in result and result["todos"]:
        todos = result["todos"]
        completed = sum(1 for t in todos if t.get('status') == 'completed')

        print("=" * 80)
        print("📋 FINAL TODO SUMMARY")
        print("=" * 80)
        print(f"Total Tasks: {len(todos)}")
        print(f"Completed: {completed}/{len(todos)}")

        if completed == len(todos):
            print("\n🎉 ALL TASKS COMPLETED!")
        else:
            print(f"\n⚠️  {len(todos) - completed} task(s) incomplete")

        print("\nTask Breakdown:")
        for i, todo in enumerate(todos, 1):
            status = todo.get('status', 'unknown')
            content = todo.get('content', '')
            icon = {"pending": "⏳", "in_progress": "▶️", "completed": "✅"}.get(status, "❓")
            print(f"  {i}. {icon} [{status.upper()}] {content}")

        print("=" * 80)

    return result


# ============================================================================
# DEMO SCENARIOS
# ============================================================================

def main():
    print("\n" + "🔬" * 40)
    print("SCENARIO 1: Multi-Step Research Task")
    print("🔬" * 40)
    print("\nThis task has 3+ steps and should trigger planning:")
    print("  1. Research topic")
    print("  2. Analyze findings")
    print("  3. Save report")

    input("\n👉 Press ENTER to run Scenario 1...")

    run_with_enhanced_visibility(
        """Research the latest developments in quantum computing from 2024,
        analyze the key breakthroughs, and save a comprehensive report
        to /workspace/quantum_2024_report.md""",
        thread_id="demo-1"
    )

    print("\n" + "🔬" * 40)
    print("SCENARIO 2: Complex Analysis Task")
    print("🔬" * 40)
    print("\nThis task requires multiple research steps and synthesis:")

    input("\n👉 Press ENTER to run Scenario 2...")

    run_with_enhanced_visibility(
        """Create a detailed analysis of AI safety research. Your report should include:
        1. Current state of AI safety research
        2. Major organizations and researchers in the field
        3. Key challenges and proposed solutions
        4. Future outlook
        Save to /workspace/ai_safety_analysis.md""",
        thread_id="demo-2"
    )

    print("\n\n" + "=" * 80)
    print("🎬 DEMO COMPLETE!")
    print("=" * 80)
    print("\n📝 What you should have seen:")
    print("  ✅ Planning announcements (🎯🎯🎯)")
    print("  ✅ Todo status updates (📝 TODO STATUS UPDATE)")
    print("  ✅ Active task indicators (▶️ ACTIVE TASKS)")
    print("  ✅ Final summaries (📋 FINAL TODO SUMMARY)")
    print("\n💡 Key Insight:")
    print("  TodoListMiddleware provides planning capabilities, but the agent")
    print("  decides when to use them. The enhanced version makes planning")
    print("  more visible and encourages more consistent use through stronger")
    print("  system prompts.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
