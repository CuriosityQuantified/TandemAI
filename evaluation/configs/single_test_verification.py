"""
Single Test Verification Script
Tests if TASK COMPLETION VERIFICATION section fixes the execution bug
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from test_config_1_deepagent_supervisor_command import create_graph

async def run_single_test():
    """Run a single test to verify the fix"""

    print("=" * 80)
    print("SINGLE TEST VERIFICATION - V3 with TASK COMPLETION VERIFICATION")
    print("=" * 80)
    print()
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Create graph
    print("Building graph...")
    graph = create_graph()
    print("✓ Graph built\n")

    # Simple test prompt
    test_prompt = "What is quantum entanglement?"
    print(f"Test Prompt: {test_prompt}")
    print("=" * 80)
    print()

    # Run test
    config = {"configurable": {"thread_id": "single_test_verification"}}
    message_count = 0
    tool_call_count = 0
    progress_updates = 0
    search_count = 0

    print("EXECUTION LOG:")
    print("-" * 80)

    async for event in graph.astream(
        {"messages": [{"role": "user", "content": test_prompt}]},
        config=config,
        stream_mode="values"
    ):
        messages = event.get("messages", [])
        if messages:
            last_msg = messages[-1]
            message_count = len(messages)

            # Count tool calls
            if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                tool_call_count += len(last_msg.tool_calls)
                for tc in last_msg.tool_calls:
                    print(f"\n🔧 Tool Call: {tc['name']}")
                    if tc['name'] == 'tavily_search':
                        search_count += 1
                        print(f"   Search query: {tc['args'].get('query', 'N/A')[:60]}...")
                    elif tc['name'] == 'update_plan_progress':
                        progress_updates += 1
                        step_idx = tc['args'].get('step_index', 'N/A')
                        print(f"   ✅ Step {step_idx} completed")
                    elif tc['name'] == 'create_research_plan':
                        num_steps = tc['args'].get('num_steps', 'N/A')
                        print(f"   📋 Creating plan with {num_steps} steps")
                    elif tc['name'] == 'read_current_plan':
                        print(f"   📖 Reading current plan")

            # Count tool results
            if hasattr(last_msg, 'content') and isinstance(last_msg.content, str):
                if len(last_msg.content) > 200:
                    print(f"\n💬 Message {message_count} (AI): {last_msg.content[:200]}...")
                elif len(last_msg.content) > 0:
                    print(f"\n💬 Message {message_count} (AI): {last_msg.content}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("METRICS:")
    print(f"  Total Messages: {message_count}")
    print(f"  Tool Calls: {tool_call_count}")
    print(f"  Searches: {search_count}")
    print(f"  Progress Updates: {progress_updates}")
    print()

    # Analysis
    print("ANALYSIS:")
    if progress_updates >= 3:
        print("  ✅ SUCCESS - Agent executed multiple plan steps (progress_updates >= 3)")
        print(f"     This indicates TASK COMPLETION VERIFICATION section is working!")
    elif progress_updates >= 1:
        print("  ⚠️  PARTIAL - Agent executed some steps but may not have completed all")
        print(f"     This is an improvement but not full success")
    else:
        print("  ❌ FAILURE - Agent did not execute plan steps (progress_updates = 0)")
        print(f"     This indicates the bug persists")
    print()

    return {
        "messages": message_count,
        "tool_calls": tool_call_count,
        "searches": search_count,
        "progress_updates": progress_updates
    }

if __name__ == "__main__":
    asyncio.run(run_single_test())
