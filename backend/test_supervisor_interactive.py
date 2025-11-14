"""
Interactive command-line test for the new Deep Agents supervisor.

This script lets you test the supervisor agent directly from the command line
before integrating it into the API/frontend.

Usage:
    python test_supervisor_interactive.py
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Add ATLAS root to path for absolute imports
atlas_root = Path(__file__).parent.parent
sys.path.insert(0, str(atlas_root))

from backend.src.agents.supervisor_agent import invoke_supervisor
from langgraph.checkpoint.memory import InMemorySaver


async def test_simple_task():
    """Test with a simple task that doesn't require API keys."""
    print("\n" + "="*60)
    print("Test 1: Simple File Operation (No API keys needed)")
    print("="*60)

    task = "Create a file called 'test.txt' with the content 'Hello ATLAS!'"
    print(f"Task: {task}\n")

    try:
        checkpointer = InMemorySaver()
        result = await invoke_supervisor(
            message=task,
            session_id="test-session-1",
            checkpointer=checkpointer
        )

        print("\n✅ Task completed!")
        print(f"Messages: {len(result.get('messages', []))} messages")

        # Show virtual filesystem
        files = result.get('files', {})
        if files:
            print(f"\n📁 Files created ({len(files)}):")
            for filename, content in files.items():
                print(f"  - {filename}: {content[:50]}...")

        # Show last agent message
        messages = result.get('messages', [])
        if messages:
            last_msg = messages[-1]
            content = getattr(last_msg, 'content', str(last_msg))
            print(f"\n💬 Agent response:\n{content}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_research_task():
    """Test research agent delegation (requires TAVILY_API_KEY)."""
    print("\n" + "="*60)
    print("Test 2: Research Task (Requires TAVILY_API_KEY)")
    print("="*60)

    task = "Research the top 3 benefits of using LangGraph for multi-agent systems and save findings to research.md"
    print(f"Task: {task}\n")

    try:
        checkpointer = InMemorySaver()
        result = await invoke_supervisor(
            message=task,
            session_id="test-session-2",
            checkpointer=checkpointer
        )

        print("\n✅ Research task completed!")

        # Show files
        files = result.get('files', {})
        if files:
            print(f"\n📁 Files created ({len(files)}):")
            for filename, content in files.items():
                print(f"\n--- {filename} ---")
                print(content[:500])
                if len(content) > 500:
                    print(f"... ({len(content) - 500} more characters)")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_analysis_task():
    """Test analysis agent delegation (requires E2B_API_KEY)."""
    print("\n" + "="*60)
    print("Test 3: Analysis Task (Requires E2B_API_KEY)")
    print("="*60)

    task = "Calculate the fibonacci sequence up to 10 numbers using Python and save the results"
    print(f"Task: {task}\n")

    try:
        checkpointer = InMemorySaver()
        result = await invoke_supervisor(
            message=task,
            session_id="test-session-3",
            checkpointer=checkpointer
        )

        print("\n✅ Analysis task completed!")

        # Show files
        files = result.get('files', {})
        if files:
            print(f"\n📁 Files created ({len(files)}):")
            for filename, content in files.items():
                print(f"\n--- {filename} ---")
                print(content)

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_custom_task():
    """Run a custom task provided by the user."""
    print("\n" + "="*60)
    print("Custom Task Test")
    print("="*60)

    task = input("\nEnter your task: ")
    if not task.strip():
        print("No task provided, skipping.")
        return False

    try:
        checkpointer = InMemorySaver()
        result = await invoke_supervisor(
            message=task,
            session_id="test-custom",
            checkpointer=checkpointer
        )

        print("\n✅ Task completed!")

        # Show files
        files = result.get('files', {})
        if files:
            print(f"\n📁 Files created ({len(files)}):")
            for filename, content in files.items():
                print(f"\n--- {filename} ---")
                print(content)

        # Show messages
        messages = result.get('messages', [])
        print(f"\n💬 Conversation ({len(messages)} messages):")
        for msg in messages:
            role = getattr(msg, 'role', 'unknown')
            content = getattr(msg, 'content', str(msg))
            print(f"\n[{role.upper()}]: {content[:200]}")
            if len(content) > 200:
                print("...")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run interactive tests."""
    print("="*60)
    print("ATLAS Deep Agents Supervisor - Interactive Testing")
    print("="*60)
    print("\nThis script tests the new Deep Agents supervisor")
    print("Choose which tests to run:\n")
    print("1. Simple file operation (no API keys needed)")
    print("2. Research task (requires TAVILY_API_KEY)")
    print("3. Analysis task (requires E2B_API_KEY)")
    print("4. Custom task (you provide the task)")
    print("5. Run all tests")
    print("0. Exit")

    choice = input("\nEnter choice (0-5): ").strip()

    results = {}

    if choice == "1":
        results["simple"] = await test_simple_task()
    elif choice == "2":
        results["research"] = await test_research_task()
    elif choice == "3":
        results["analysis"] = await test_analysis_task()
    elif choice == "4":
        results["custom"] = await test_custom_task()
    elif choice == "5":
        print("\n🚀 Running all tests...\n")
        results["simple"] = await test_simple_task()
        await asyncio.sleep(1)
        results["research"] = await test_research_task()
        await asyncio.sleep(1)
        results["analysis"] = await test_analysis_task()
    elif choice == "0":
        print("\nExiting...")
        return
    else:
        print("\nInvalid choice. Exiting...")
        return

    # Show summary
    if results:
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {test_name}")
        print("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
