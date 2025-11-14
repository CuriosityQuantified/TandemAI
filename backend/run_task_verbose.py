"""
Verbose command-line runner for ATLAS Deep Agents supervisor.
Shows detailed input/output for every agent and tool call.

Usage:
    python run_task_verbose.py "Your task here"

This version shows:
- Every message exchange
- Sub-agent delegations
- Tool calls with inputs and outputs
- Planning/todo updates
- File operations
- Full conversation flow
"""

import asyncio
import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Debug mode flag - set ATLAS_DEBUG=true to see all LangGraph events
DEBUG_MODE = os.environ.get("ATLAS_DEBUG", "false").lower() == "true"

# Add ATLAS root to path
atlas_root = Path(__file__).parent.parent
sys.path.insert(0, str(atlas_root))

from backend.src.agents.supervisor_agent import create_supervisor_agent
from langgraph.checkpoint.memory import InMemorySaver


def print_separator(title: str = "", char: str = "="):
    """Print a visual separator."""
    if title:
        print(f"\n{char*3} {title} {char*(57-len(title))}")
    else:
        print(f"\n{char*60}")


def format_tool_input(tool_input: Any) -> str:
    """Format tool input for display."""
    if isinstance(tool_input, dict):
        return json.dumps(tool_input, indent=2)
    return str(tool_input)


def format_message(msg: Any, msg_num: int) -> None:
    """Format and print a message with full details."""
    msg_type = getattr(msg, 'type', 'unknown')
    content = getattr(msg, 'content', '')

    if msg_type == 'human':
        print_separator(f"MESSAGE {msg_num}: USER INPUT", "=")
        print(content)

    elif msg_type == 'ai':
        print_separator(f"MESSAGE {msg_num}: AGENT RESPONSE", "=")

        # Check for tool calls
        tool_calls = getattr(msg, 'tool_calls', [])
        if tool_calls:
            print("\n🔧 TOOL CALLS:")
            for i, tool_call in enumerate(tool_calls, 1):
                tool_name = tool_call.get('name', 'unknown')
                tool_args = tool_call.get('args', {})
                tool_id = tool_call.get('id', 'unknown')

                print(f"\n  [{i}] Tool: {tool_name}")
                print(f"      ID: {tool_id}")
                print(f"      Arguments:")
                for key, value in tool_args.items():
                    # Truncate long values
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    print(f"        - {key}: {value_str}")

        # Show text content if present
        if content:
            print(f"\n💬 Response:")
            print(content)

    elif msg_type == 'tool':
        print_separator(f"MESSAGE {msg_num}: TOOL RESULT", "-")
        tool_name = getattr(msg, 'name', 'unknown_tool')
        tool_call_id = getattr(msg, 'tool_call_id', 'unknown')

        print(f"🔧 Tool: {tool_name}")
        print(f"   Call ID: {tool_call_id}")
        print(f"\n📤 Output:")

        # Parse and format the content
        try:
            if isinstance(content, str):
                # Try to parse as JSON for better formatting
                try:
                    parsed = json.loads(content)
                    print(json.dumps(parsed, indent=2))
                except:
                    # Not JSON, show as-is but truncate if too long
                    if len(content) > 500:
                        print(content[:500])
                        print(f"\n... ({len(content) - 500} more characters)")
                    else:
                        print(content)
            else:
                print(content)
        except Exception as e:
            print(f"[Error formatting output: {e}]")
            print(content)


async def run_task_verbose(task: str):
    """Run a task with verbose logging of all agent interactions."""
    print_separator("ATLAS DEEP AGENTS - VERBOSE MODE", "=")
    print(f"\n🎯 Task: {task}")

    try:
        # Create supervisor agent
        print("\n⏳ Creating supervisor agent...")
        agent = await create_supervisor_agent()

        # Attach checkpointer
        checkpointer = InMemorySaver()
        agent.checkpointer = checkpointer

        # Configure session with INCREASED RECURSION LIMIT for debugging
        config = {
            "configurable": {
                "thread_id": "cli-verbose-session"
            },
            "recursion_limit": 100,  # Increased from default 25 to see full loops
        }

        print("✅ Agent ready")
        print("🔍 Recursion limit: 100 (to capture full execution)")

        # Determine stream mode based on debug flag
        if DEBUG_MODE:
            stream_mode_value = "debug"
            print("🐛 Debug Mode: ENABLED (streaming all LangGraph internal events)")
        else:
            stream_mode_value = "updates"
            print("📨 Stream Mode: updates (complete node updates, sub-agent visibility)")

        print_separator("STREAMING EXECUTION", "=")

        # Stream the execution to see everything in real-time
        message_count = 0
        event_count = 0

        async for event in agent.astream(
            {"messages": [{"role": "user", "content": task}]},
            config=config,
            stream_mode=stream_mode_value  # "updates" for complete node updates
        ):
            event_count += 1

            if DEBUG_MODE:
                # In debug mode, print raw events
                print(f"\n[DEBUG EVENT {event_count}]")
                print(json.dumps(event, indent=2, default=str)[:500])  # Truncate long events
            else:
                # In updates mode, event is a dict with node_name: update_data
                if isinstance(event, dict):
                    for node_name, update_data in event.items():
                        print_separator(f"NODE: {node_name}", "-")

                        # Extract messages from the update
                        if isinstance(update_data, dict) and "messages" in update_data:
                            messages = update_data["messages"]
                            for msg in messages:
                                message_count += 1
                                format_message(msg, message_count)
                        elif isinstance(update_data, list):
                            # Sometimes updates are lists of messages
                            for msg in update_data:
                                message_count += 1
                                format_message(msg, message_count)

            # Show progress every 10 events
            if event_count % 10 == 0:
                print(f"\n[Progress: {event_count} updates, {message_count} messages]")

        print_separator("EXECUTION COMPLETE", "=")

        # Get final state
        final_state = checkpointer.get(config)
        if final_state:
            state_values = final_state.get("channel_values", {})
            files = state_values.get("files", {})

            if files:
                print(f"\n📁 VIRTUAL FILESYSTEM ({len(files)} files):")
                for filename, content in files.items():
                    print(f"\n--- {filename} ---")
                    if len(content) > 500:
                        print(content[:500])
                        print(f"\n... ({len(content) - 500} more characters)")
                    else:
                        print(content)

        print_separator("SUMMARY", "=")
        print(f"✅ Task completed successfully")
        print(f"📊 Total messages exchanged: {message_count}")
        print_separator("", "=")

        return True

    except Exception as e:
        print_separator("ERROR", "=")
        print(f"❌ {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    success = asyncio.run(run_task_verbose(task))
    sys.exit(0 if success else 1)
