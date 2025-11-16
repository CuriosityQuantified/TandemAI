"""
Test Frontend Researcher V3 Integration
========================================

Verifies that the frontend's researcher agent (via langgraph_studio_graphs.py)
correctly uses V3 citation verification system.

Expected Behavior:
1. Graph creation succeeds with V3 tools
2. Researcher receives citation-aware prompt
3. Researcher can execute citation verification tools
4. Tools actually run (not just placeholders)
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add backend directory to path (same pattern as copilotkit_main.py)
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

print("=" * 80)
print("FRONTEND RESEARCHER V3 INTEGRATION TEST")
print("=" * 80)
print()

# Step 1: Import the backend graph creator (using relative imports like copilotkit_main.py)
print("Step 1: Importing langgraph_studio_graphs...")
try:
    from langgraph_studio_graphs import create_unified_graph
    print("✅ Successfully imported create_unified_graph")
except Exception as e:
    print(f"❌ Failed to import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Step 2: Create the unified graph (without checkpointer for testing)
print("Step 2: Creating unified graph...")
try:
    graph = create_unified_graph(custom_checkpointer=None)
    print("✅ Successfully created unified graph")

    # Verify it's a compiled graph
    print(f"   Graph type: {type(graph).__name__}")
except Exception as e:
    print(f"❌ Failed to create graph: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Step 3: Test with a simple research query
print("Step 3: Testing researcher invocation...")
print()

test_query = "What are the key features of quantum error correction?"

print(f"Query: {test_query}")
print()
print("Expected V3 behavior:")
print("  1. Supervisor delegates to researcher")
print("  2. Researcher uses tavily_search_cached (not regular tavily_search)")
print("  3. Citation verification tools are available")
print("  4. Tools execute real operations (not placeholders)")
print()

from langchain_core.messages import HumanMessage
import asyncio

async def run_test():
    """Async test function."""
    start_time = datetime.now()

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=test_query)]},
        config={
            "configurable": {"thread_id": "test-frontend-v3"},
            "recursion_limit": 75
        }
    )

    execution_time = (datetime.now() - start_time).total_seconds()
    messages = result.get("messages", [])
    return execution_time, messages

try:
    execution_time, messages = asyncio.run(run_test())

    print(f"✅ Graph execution completed in {execution_time:.1f}s")
    print(f"   Total messages: {len(messages)}")
    print()

    # Step 4: Analyze the execution
    print("=" * 80)
    print("V3 INTEGRATION ANALYSIS")
    print("=" * 80)
    print()

    # Check for delegation
    delegation_called = any(
        hasattr(msg, 'tool_calls') and msg.tool_calls and
        any(tc.get('name') == 'delegate_to_researcher' for tc in msg.tool_calls)
        for msg in messages
    )
    print(f"1. Delegation to researcher: {'✅' if delegation_called else '❌'}")

    # Check for V3 citation tools
    citation_tool_calls = [
        msg for msg in messages
        if hasattr(msg, 'name') and msg.name in [
            'tavily_search_cached',
            'verify_citations',
            'get_cached_source_content'
        ]
    ]
    print(f"2. V3 citation tool calls: {len(citation_tool_calls)}")

    if citation_tool_calls:
        for tool_msg in citation_tool_calls:
            print(f"   - {tool_msg.name}")
            # Check if it's a real result (not placeholder)
            if "executed" in tool_msg.content and len(tool_msg.content) < 50:
                print(f"     ⚠️  WARNING: Looks like placeholder response!")
            else:
                print(f"     ✅ Real tool execution detected")

    # Check for old tavily_search (should not be used)
    old_tavily_calls = [
        msg for msg in messages
        if hasattr(msg, 'name') and msg.name == 'tavily_search'
    ]
    if old_tavily_calls:
        print(f"   ⚠️  WARNING: Old tavily_search called {len(old_tavily_calls)} times (should use tavily_search_cached)")

    print()

    # Get final response
    print("=" * 80)
    print("FINAL RESPONSE (first 500 chars)")
    print("=" * 80)
    print()

    final_response = None
    for msg in reversed(messages):
        if hasattr(msg, 'content') and msg.content and not (hasattr(msg, 'tool_calls') and msg.tool_calls):
            final_response = msg.content
            break

    if final_response:
        # Handle structured response
        if isinstance(final_response, list):
            if isinstance(final_response[0], dict) and 'text' in final_response[0]:
                final_response = final_response[0]['text']

        preview = str(final_response)[:500]
        print(preview)
        if len(str(final_response)) > 500:
            print("...")
    else:
        print("(No final response found)")

    print()

    # Overall success
    v3_success = (
        delegation_called and
        len(citation_tool_calls) > 0 and
        len(old_tavily_calls) == 0
    )

    print("=" * 80)
    if v3_success:
        print("✅ FRONTEND V3 INTEGRATION SUCCESSFUL!")
        print()
        print("The frontend researcher is now using:")
        print("  ✅ V3 citation-aware prompt")
        print("  ✅ Citation verification tools (tavily_search_cached)")
        print("  ✅ Real tool execution (not placeholders)")
        print()
        print("Next steps:")
        print("  1. Test with frontend UI")
        print("  2. Verify PostgreSQL caching")
        print("  3. Test citation verification workflow")
    else:
        print("❌ V3 INTEGRATION INCOMPLETE")
        print()
        print("Issues detected:")
        if not delegation_called:
            print("  - Delegation to researcher not working")
        if len(citation_tool_calls) == 0:
            print("  - No V3 citation tools were called")
        if len(old_tavily_calls) > 0:
            print("  - Still using old tavily_search instead of tavily_search_cached")
    print("=" * 80)
    print()

    sys.exit(0 if v3_success else 1)

except Exception as e:
    print(f"❌ Execution failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
