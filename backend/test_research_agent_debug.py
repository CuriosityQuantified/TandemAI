"""
Debug test for research agent recursion issue.

This test runs the research agent with verbose logging to identify
exactly what happens in each of the 25 recursion steps.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure verbose logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("anthropic").setLevel(logging.WARNING)

# Enable LangGraph debug logging
import os
os.environ["LANGCHAIN_TRACING_V2"] = "false"  # Disable LangSmith
os.environ["LANGCHAIN_VERBOSE"] = "true"

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


async def test_research_agent_with_streaming():
    """Test research agent with step-by-step streaming."""
    print("\n" + "=" * 70)
    print("RESEARCH AGENT DEBUG TEST")
    print("=" * 70)

    # Create supervisor agent
    # Set PYTHONPATH to find backend module
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from backend.src.agents.supervisor_agent import create_supervisor_agent

    print("\n📋 Creating supervisor agent...")
    supervisor = await create_supervisor_agent()

    # Simple research task
    task = "Search for the latest news about Claude AI from Anthropic. Save findings to /workspace/claude_news.txt"

    print(f"\n🎯 Task: {task}")
    print(f"\n⏳ Streaming execution (watch for tool calls and reasoning)...")
    print("=" * 70)

    step_count = 0
    tool_calls = []
    all_steps = []  # Store all steps for detailed analysis

    try:
        # Use simple stream mode to see values
        async for chunk in supervisor.astream(
            {"messages": [{"role": "user", "content": task}]},
            stream_mode="values"  # Show state values
        ):
            step_count += 1
            step_info = {"step": step_count, "tools": [], "message_type": None, "content_preview": None}

            print(f"\n{'='*70}")
            print(f"STEP {step_count}")
            print('='*70)

            # Extract tool calls from messages
            messages = chunk.get("messages", [])
            if messages:
                last_msg = messages[-1]

                # Check for tool calls
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    for tc in last_msg.tool_calls:
                        tool_name = tc.get("name", "unknown")
                        tool_args = tc.get("args", {})
                        tool_calls.append(tool_name)
                        step_info["tools"].append({"name": tool_name, "args": tool_args})
                        print(f"🔧 TOOL CALL: {tool_name}")
                        # Show tool arguments (truncated if long)
                        args_str = str(tool_args)
                        if len(args_str) > 200:
                            args_str = args_str[:200] + "..."
                        print(f"   Args: {args_str}")

                # Show content and message type
                step_info["message_type"] = type(last_msg).__name__
                print(f"💬 MESSAGE TYPE: {type(last_msg).__name__}")

                if hasattr(last_msg, "content") and last_msg.content:
                    content = str(last_msg.content)
                    content_preview = content[:300] if len(content) > 300 else content
                    step_info["content_preview"] = content_preview
                    print(f"📝 CONTENT PREVIEW:")
                    print(f"{content_preview}")

            all_steps.append(step_info)

            # Safety limit
            if step_count >= 30:
                print(f"\n⚠️  Reached safety limit of 30 steps")
                break

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Total steps: {step_count}")
    print(f"Total tool calls: {len(tool_calls)}")
    if tool_calls:
        print(f"\nTools called (in order): {', '.join(tool_calls)}")

    print("\n" + "=" * 70)
    print("DETAILED STEP-BY-STEP BREAKDOWN")
    print("=" * 70)
    for step_info in all_steps:
        step_num = step_info["step"]
        tools = step_info["tools"]
        msg_type = step_info["message_type"]

        print(f"\n{step_num}. {msg_type}")
        if tools:
            for tool in tools:
                print(f"   → Tool: {tool['name']}")
        elif step_info["content_preview"]:
            preview = step_info["content_preview"]
            if len(preview) > 100:
                preview = preview[:100] + "..."
            print(f"   → Content: {preview}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(test_research_agent_with_streaming())
