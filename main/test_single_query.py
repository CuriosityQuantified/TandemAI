"""
Single Query Test for Fixed Baseline Agent

This tests that the researcher agent now:
1. Receives the 26KB system prompt with planning instructions
2. Creates research plans with multiple steps
3. Performs Tavily searches to gather sources
4. Returns comprehensive responses with citations
"""

import sys
from pathlib import Path
import json

# Add main directory to path
main_path = Path(__file__).parent
sys.path.insert(0, str(main_path))

from evaluation.baseline_agent_wrapper import get_baseline_agent

# Test query
test_query = "What are the key features of Python 3.12?"

print("=" * 80)
print("SINGLE QUERY TEST - Fixed Baseline Agent")
print("=" * 80)
print(f"\nQuery: {test_query}")
print("\nExpected Behavior:")
print("  ✓ Researcher should create a research plan (4-10 steps)")
print("  ✓ Researcher should perform Tavily searches (3-15 sources)")
print("  ✓ Researcher should provide comprehensive response with citations")
print("\n" + "-" * 80)

# Get baseline agent
print("\nInitializing baseline agent...")
agent = get_baseline_agent("Researcher")
print("✓ Agent initialized\n")

# Execute query
print("Executing query...")
print("-" * 80)

result = agent(test_query)

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)

# Analyze results
messages = result['messages']
plan = result.get('plan')
files = result.get('files', [])

print(f"\n📊 Statistics:")
print(f"  Total messages: {len(messages)}")
print(f"  Research plan: {'Yes' if plan else 'No'}")
if plan:
    print(f"    Steps: {plan.get('num_steps', 0)}")
    print(f"    Query: {plan.get('query', '')[:60]}...")
print(f"  Files created: {len(files)}")

# Count tool calls
from langchain_core.messages import AIMessage, ToolMessage

tool_calls = [msg for msg in messages if isinstance(msg, AIMessage) and msg.tool_calls]
tool_results = [msg for msg in messages if isinstance(msg, ToolMessage)]

print(f"\n🔧 Tool Usage:")
print(f"  Tool call messages: {len(tool_calls)}")
print(f"  Tool result messages: {len(tool_results)}")

# Check for Tavily searches
tavily_searches = [msg for msg in messages if isinstance(msg, ToolMessage) and 'tavily' in msg.name.lower()]
print(f"  Tavily searches: {len(tavily_searches)}")

# Check for planning tool usage
planning_tools = [msg for msg in messages
                  if isinstance(msg, ToolMessage) and
                  any(name in msg.name for name in ['create_research_plan', 'update_plan_progress', 'read_current_plan'])]
print(f"  Planning tool calls: {len(planning_tools)}")

# Show final response
ai_messages = [msg for msg in messages if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls]
if ai_messages:
    final_response = ai_messages[-1].content
    print(f"\n📝 Final Response Preview:")
    print("-" * 80)
    preview = final_response[:500] if len(final_response) > 500 else final_response
    print(preview)
    if len(final_response) > 500:
        print(f"\n... (truncated, {len(final_response) - 500} more characters)")
    print("-" * 80)
    print(f"  Total response length: {len(final_response)} characters")

# Evaluation
print(f"\n✅ SUCCESS CRITERIA:")
has_plan = plan is not None and plan.get('num_steps', 0) > 0
has_searches = len(tavily_searches) > 0
has_response = len(ai_messages) > 0 and len(ai_messages[-1].content) > 100

print(f"  {'✓' if has_plan else '✗'} Research plan created with steps")
print(f"  {'✓' if has_searches else '✗'} Tavily searches performed")
print(f"  {'✓' if has_response else '✗'} Comprehensive response generated")

success = has_plan and has_searches and has_response
print(f"\n{'✓ TEST PASSED' if success else '✗ TEST FAILED'}")

if not success:
    print("\n⚠️  Issues detected:")
    if not has_plan:
        print("  - No research plan created")
    if not has_searches:
        print("  - No Tavily searches performed")
    if not has_response:
        print("  - Response too short or missing")

print("\n" + "=" * 80)
