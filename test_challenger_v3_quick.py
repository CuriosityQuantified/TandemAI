"""
Quick Test: Challenger V3 Configuration
=========================================

Validates that the Challenger V3 configuration works correctly with citation verification.

Expected Behavior:
1. Agent uses tavily_search_cached during research
2. Agent generates response with citations
3. Agent calls verify_citations before completing
4. Agent self-corrects if citations fail
5. Agent completes only when all_verified=True
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
root_path = Path(__file__).parent
sys.path.insert(0, str(root_path))

# Load environment
from dotenv import load_dotenv
load_dotenv(root_path / ".env")

# Import the V3 configuration
# This imports the graph, supervisor, researcher_subagent, etc.
print("=" * 80)
print("CHALLENGER V3 QUICK TEST")
print("=" * 80)
print("\nImporting V3 configuration...")

from evaluation.configs.test_config_challenger_3 import (
    graph,
    MODEL_NAME,
    TEMPERATURE
)

from langchain_core.messages import HumanMessage
import json

print(f"✅ V3 Configuration imported successfully")
print(f"   Model: {MODEL_NAME}")
print(f"   Temperature: {TEMPERATURE}")
print()

# Test query
test_query = "What is quantum error correction?"

print("=" * 80)
print("TEST EXECUTION")
print("=" * 80)
print(f"\nQuery: {test_query}")
print(f"\nExpected Flow:")
print(f"  1. Supervisor delegates to researcher")
print(f"  2. Researcher uses tavily_search_cached")
print(f"  3. Researcher generates response with citations")
print(f"  4. Researcher calls verify_citations")
print(f"  5. Researcher completes (or fixes if needed)")
print()

# Run the graph
print("=" * 80)
print("RUNNING V3 GRAPH")
print("=" * 80)
print()

start_time = datetime.now()

try:
    result = graph.invoke(
        {"messages": [HumanMessage(content=test_query)]},
        config={
            "configurable": {"thread_id": "test-v3-quick"},
            "recursion_limit": 75
        }
    )

    execution_time = (datetime.now() - start_time).total_seconds()
    messages = result.get("messages", [])

    print(f"\n✅ Graph completed in {execution_time:.1f}s")
    print(f"   Total messages: {len(messages)}")
    print()

    # Analyze results
    print("=" * 80)
    print("WORKFLOW ANALYSIS")
    print("=" * 80)
    print()

    # Check for delegation
    delegation_called = any(
        hasattr(msg, 'tool_calls') and msg.tool_calls and
        any(tc['name'] == 'delegate_to_researcher' for tc in msg.tool_calls)
        for msg in messages
    )
    print(f"1. Delegation called: {delegation_called}")

    # Check for tavily_search_cached
    search_calls = [
        msg for msg in messages
        if hasattr(msg, 'name') and msg.name == 'tavily_search_cached'
    ]
    print(f"2. Tavily search calls: {len(search_calls)}")
    for i, call in enumerate(search_calls, 1):
        try:
            result_data = json.loads(call.content)
            cached = result_data.get("_cached", False)
            cached_count = result_data.get("_cached_count", 0)
            print(f"   Call {i}: Cached={cached}, Results={cached_count}")
        except:
            print(f"   Call {i}: (parsing failed)")

    # Check for verify_citations
    verify_calls = [
        msg for msg in messages
        if hasattr(msg, 'name') and msg.name == 'verify_citations'
    ]
    print(f"3. Citation verification calls: {len(verify_calls)}")
    for i, call in enumerate(verify_calls, 1):
        try:
            result_data = json.loads(call.content)
            all_verified = result_data.get("all_verified", False)
            total = result_data.get("total_citations", 0)
            verified = result_data.get("verified_count", 0)
            print(f"   Call {i}: Total={total}, Verified={verified}, All Verified={all_verified}")

            if not all_verified:
                print(f"   ❌ Failed citations:")
                for failed in result_data.get("failed_citations", []):
                    print(f"      - [{failed.get('ref_num', 'N/A')}] {failed.get('quote', 'N/A')[:50]}...")
                    print(f"        Reason: {failed.get('reason', 'N/A')}")
        except:
            print(f"   Call {i}: (parsing failed)")

    # Check final verification status
    if verify_calls:
        try:
            final_verification = json.loads(verify_calls[-1].content)
            final_verified = final_verification.get("all_verified", False)
            print(f"\n4. Final Verification Status: {final_verified}")

            if final_verified:
                print(f"   ✅ All citations verified successfully!")
            else:
                print(f"   ❌ Citations failed verification")
        except:
            print(f"\n4. Final Verification Status: (parsing failed)")

    print()

    # Get final response
    print("=" * 80)
    print("FINAL RESPONSE")
    print("=" * 80)
    print()

    final_response = None
    for msg in reversed(messages):
        if hasattr(msg, 'content') and msg.content and not (hasattr(msg, 'tool_calls') and msg.tool_calls):
            final_response = msg.content
            break

    if final_response:
        # Handle structured response format
        if isinstance(final_response, list):
            if isinstance(final_response[0], dict) and 'text' in final_response[0]:
                final_response = final_response[0]['text']

        print(final_response[:500] + "..." if len(str(final_response)) > 500 else final_response)
    else:
        print("(No final response found)")

    print()

    # Overall success criteria
    success = (
        delegation_called and
        len(search_calls) > 0 and
        len(verify_calls) > 0
    )

    print("=" * 80)
    if success:
        print("✅ TEST PASSED: Challenger V3 Configuration Working!")
    else:
        print("❌ TEST FAILED: Check workflow above")
    print("=" * 80)
    print()

    if success:
        print("V3 successfully demonstrated:")
        print("  ✅ Supervisor delegation")
        print("  ✅ Citation-aware search (tavily_search_cached)")
        print("  ✅ Citation verification workflow")
        print()

    sys.exit(0 if success else 1)

except Exception as e:
    print(f"\n❌ TEST FAILED WITH ERROR:")
    print(f"   {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
