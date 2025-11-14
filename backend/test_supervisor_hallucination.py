#!/usr/bin/env python3
"""
Test script to verify tool hallucination is eliminated in LangChain Supervisor.

This script tests the exact scenario that previously caused hallucination:
User asks: "What's the S&P 500 return this month?"

Expected behavior (correct):
1. plan_task to break down the request
2. delegate_research to find S&P 500 data
3. delegate_analysis to calculate return
4. save_output to store results

Previous behavior (incorrect):
- Hallucinated tool: getMonthlyReturn("S&P 500")
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load environment variables from parent .env file
atlas_dir = backend_dir.parent
env_path = atlas_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded environment from: {env_path}")
else:
    print(f"⚠️  No .env file found at: {env_path}")

from src.agents.langchain_supervisor import LangChainSupervisor
from src.mlflow.tracking import ATLASMLflowTracker


async def test_supervisor_no_hallucination():
    """
    Test that the supervisor uses registered tools instead of hallucinating.
    """
    print("="*80)
    print("TESTING: LangChain Supervisor Tool Hallucination Fix")
    print("="*80)
    print()

    # Create supervisor
    task_id = "test_hallucination_fix"
    mlflow_tracker = ATLASMLflowTracker()

    print(f"✓ Creating supervisor for task: {task_id}")
    supervisor = LangChainSupervisor(
        task_id=task_id,
        mlflow_tracker=mlflow_tracker,
        model_name="gpt-4o",
        temperature=0.7
    )

    # Get tool names from the bound tools
    from src.agents.langchain_tools import TOOL_NAMES
    print(f"✓ Supervisor initialized with {len(TOOL_NAMES)} tools")
    print(f"✓ Tools available: {TOOL_NAMES}")
    print()

    # The test query that previously caused hallucination
    test_query = "What's the S&P 500 return this month?"

    print(f"📤 Sending test query: '{test_query}'")
    print("="*80)
    print()

    # Track events
    tool_calls = []
    content_chunks = []
    errors = []

    try:
        async for chunk in supervisor.send_message(test_query):
            chunk_type = chunk.get("type")
            chunk_data = chunk.get("data", {})

            if chunk_type == "content":
                content = chunk_data.get("content", "")
                if content:
                    content_chunks.append(content)
                    print(content, end="", flush=True)

            elif chunk_type == "tool_call_chunk":
                if chunk_data.get("name"):
                    tool_name = chunk_data["name"]
                    print(f"\n\n🔧 Tool Call Detected: {tool_name}")
                    tool_calls.append(tool_name)

            elif chunk_type == "tool_result":
                tool_name = chunk_data.get("tool_name", "unknown")
                success = chunk_data.get("success", False)
                status_icon = "✅" if success else "❌"
                print(f"{status_icon} Tool '{tool_name}' {'succeeded' if success else 'failed'}")

                if not success:
                    errors.append({
                        "tool": tool_name,
                        "error": chunk_data.get("error", "Unknown error")
                    })

            elif chunk_type == "error":
                error_msg = chunk_data.get("error", "Unknown error")
                print(f"\n❌ ERROR: {error_msg}")
                errors.append({"type": "general", "error": error_msg})

            elif chunk_type == "complete":
                print("\n\n✓ Response Complete")
                duration = chunk_data.get("duration_ms", 0)
                print(f"✓ Duration: {duration:.2f}ms")

    except Exception as e:
        print(f"\n\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        errors.append({"type": "exception", "error": str(e)})

    # Analysis
    print("\n")
    print("="*80)
    print("ANALYSIS")
    print("="*80)

    # Check for hallucinated tools
    registered_tools = {
        "plan_task", "update_plan",
        "create_todo", "update_todo_status",
        "save_output", "load_file", "list_outputs", "append_content",
        "delegate_research", "delegate_analysis", "delegate_writing"
    }

    hallucinated_tools = [t for t in tool_calls if t not in registered_tools]

    print(f"\n📊 Tools Called: {len(tool_calls)}")
    for tool in tool_calls:
        is_valid = tool in registered_tools
        status = "✅ VALID" if is_valid else "❌ HALLUCINATED"
        print(f"  {status}: {tool}")

    print(f"\n🎯 Hallucination Test Result:")
    if hallucinated_tools:
        print(f"  ❌ FAILED: Found {len(hallucinated_tools)} hallucinated tool(s)")
        print(f"  Hallucinated: {hallucinated_tools}")
    else:
        print(f"  ✅ PASSED: No hallucinated tools detected!")

    print(f"\n📝 Content Generated: {len(''.join(content_chunks))} characters")

    if errors:
        print(f"\n⚠️  Errors Encountered: {len(errors)}")
        for err in errors:
            print(f"  - {err}")
    else:
        print("\n✅ No errors encountered")

    # Expected behavior check
    print(f"\n🔍 Expected Tool Usage:")
    expected_tools = ["plan_task", "delegate_research", "delegate_analysis"]
    for expected in expected_tools:
        used = "✅" if expected in tool_calls else "⚠️ "
        print(f"  {used} {expected}")

    print("\n" + "="*80)

    # Final verdict
    if not hallucinated_tools and not errors:
        print("🎉 SUCCESS: Tool hallucination eliminated!")
        return True
    else:
        print("⚠️  NEEDS ATTENTION: Issues detected")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_supervisor_no_hallucination())
    sys.exit(0 if result else 1)
