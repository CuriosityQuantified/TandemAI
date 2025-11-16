"""
Debug script to test delegation routing directly.
Tests the full graph delegation flow to identify where it fails.
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from langgraph_studio_graphs import create_unified_graph
from langchain_core.messages import HumanMessage

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_delegation():
    """Test delegation routing directly"""
    print("\n" + "="*80)
    print("DELEGATION ROUTING DEBUG TEST")
    print("="*80 + "\n")

    print("📊 Step 1: Creating and compiling graph...")
    try:
        compiled = create_unified_graph()
        print("✅ Graph created and compiled successfully\n")
    except Exception as e:
        print(f"❌ Failed to create graph: {e}")
        import traceback
        traceback.print_exc()
        return

    print("📊 Step 2: Testing delegation request...")
    config = {
        "configurable": {
            "thread_id": "debug-test-delegation",
            "session_id": "debug-test",
        },
        "recursion_limit": 50  # Increase limit to see if delegation completes
    }

    test_message = "Delegate to researcher: Find the latest features in Python 3.13"
    print(f"📨 Test message: {test_message}\n")

    try:
        print("🔄 Invoking graph...")
        result = await compiled.ainvoke(
            {
                "messages": [
                    HumanMessage(content=test_message)
                ],
            },
            config=config
        )

        print("\n" + "="*80)
        print("✅ SUCCESS! Delegation completed")
        print("="*80 + "\n")

        print("📋 Result messages:")
        for i, msg in enumerate(result.get("messages", [])):
            msg_type = type(msg).__name__
            content = getattr(msg, 'content', '')
            content_preview = content[:200] + "..." if len(content) > 200 else content
            print(f"\n  Message {i+1} ({msg_type}):")
            print(f"    {content_preview}")

            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"    Tool calls: {len(msg.tool_calls)}")
                for tc in msg.tool_calls:
                    print(f"      - {tc.get('name', 'unknown')}")

    except Exception as e:
        print("\n" + "="*80)
        print("❌ ERROR: Delegation failed")
        print("="*80 + "\n")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}\n")
        print("Full traceback:")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Starting delegation debug test...\n")
    asyncio.run(test_delegation())
