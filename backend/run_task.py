"""
Simple command-line runner for ATLAS Deep Agents supervisor.

Usage:
    python run_task.py "Your task here"

Examples:
    python run_task.py "Create a file greeting.txt with hello world"
    python run_task.py "Research the benefits of async programming"
    python run_task.py "Calculate fibonacci sequence up to 10 numbers"
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Add ATLAS root to path
atlas_root = Path(__file__).parent.parent
sys.path.insert(0, str(atlas_root))

from backend.src.agents.supervisor_agent import invoke_supervisor
from langgraph.checkpoint.memory import InMemorySaver


async def run_task(task: str):
    """Run a single task with the supervisor."""
    print(f"\n🎯 Task: {task}\n")
    print("⏳ Processing...\n")

    try:
        checkpointer = InMemorySaver()
        result = await invoke_supervisor(
            message=task,
            session_id="cli-session",
            checkpointer=checkpointer
        )

        print("\n" + "="*60)
        print("✅ TASK COMPLETED")
        print("="*60)

        # Show files created
        files = result.get('files', {})
        if files:
            print(f"\n📁 Files Created ({len(files)}):")
            for filename, content in files.items():
                print(f"\n--- {filename} ---")
                print(content)
                print()

        # Show agent messages
        messages = result.get('messages', [])
        if messages:
            print(f"💬 Agent Messages ({len(messages)}):")
            for i, msg in enumerate(messages, 1):
                role = getattr(msg, 'type', getattr(msg, 'role', 'unknown'))
                content = getattr(msg, 'content', str(msg))

                if role in ['ai', 'assistant']:
                    print(f"\n[AGENT]: {content}")
                elif role in ['human', 'user']:
                    print(f"\n[USER]: {content}")
                elif role == 'tool':
                    # Show tool calls more concisely
                    tool_name = getattr(msg, 'name', 'unknown_tool')
                    print(f"\n[TOOL: {tool_name}]")

        print("\n" + "="*60)
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    success = asyncio.run(run_task(task))
    sys.exit(0 if success else 1)
