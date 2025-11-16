#!/usr/bin/env python3
"""
Custom Test Runner for Config 1 and Config 4

Allows running test configurations with custom queries from command line.

Usage:
    python run_custom_test.py --config 1 --query "Your custom research query"
    python run_custom_test.py --config 4 --query "Your custom research query"
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add test_configs to path
sys.path.insert(0, str(Path(__file__).parent))


def run_config_1(custom_query: str):
    """Run Config 1 with custom query."""
    print("\n" + "="*80)
    print("RUNNING CONFIG 1: DeepAgent + Command.goto")
    print("="*80)
    print(f"\n📝 Custom Query: {custom_query}\n")

    # Import Config 1 components
    from test_config_1_deepagent_supervisor_command import create_graph
    from langchain_core.messages import HumanMessage

    # Build graph
    print("📊 Building graph...")
    graph = create_graph()
    print("✓ Graph built\n")

    # Run with custom query
    config = {
        "configurable": {"thread_id": "custom-test-config-1"},
        "recursion_limit": 50
    }

    print(f"⚡ Executing with custom query...\n")
    print("-"*80)

    result = graph.invoke(
        {"messages": [HumanMessage(content=custom_query)]},
        config=config
    )

    print("\n" + "="*80)
    print("EXECUTION COMPLETE")
    print("="*80 + "\n")

    # Print message trace
    print("📊 MESSAGE TRACE:\n")
    for i, msg in enumerate(result["messages"], 1):
        msg_type = msg.__class__.__name__
        print(f"\n{i}. {msg_type}")

        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            print(f"   Tool calls: {len(msg.tool_calls)}")
            for tc in msg.tool_calls:
                print(f"     - {tc['name']}")

        if hasattr(msg, 'content') and msg.content:
            content_preview = str(msg.content)[:200]
            print(f"   Content: {content_preview}...")

    print("\n" + "="*80)
    print(f"✅ Config 1 completed with {len(result['messages'])} messages")
    print("="*80 + "\n")

    return result


async def run_config_4(custom_query: str):
    """Run Config 4 with custom query."""
    print("\n" + "="*80)
    print("RUNNING CONFIG 4: ReAct + Conditional Edges")
    print("="*80)
    print(f"\n📝 Custom Query: {custom_query}\n")

    # Import Config 4 components
    from test_config_4_react_supervisor_conditional import build_graph
    from langchain_core.messages import HumanMessage

    # Build graph
    print("📊 Building graph...")
    graph = await build_graph()
    print("✓ Graph built\n")

    # Format query with delegation instruction
    test_message = (
        f"Please delegate this research task to the researcher subagent: {custom_query}\n\n"
        f"Step 1: Use delegate_to_researcher tool to pass this query to the researcher.\n"
        f"The researcher will then plan and execute the research."
    )

    print(f"⚡ Executing with custom query...\n")
    print("-"*80)

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=test_message)]},
        {"recursion_limit": 50}
    )

    print("\n" + "="*80)
    print("EXECUTION COMPLETE")
    print("="*80 + "\n")

    # Print message trace
    print("📊 MESSAGE TRACE:\n")
    for i, msg in enumerate(result["messages"], 1):
        msg_type = msg.__class__.__name__
        print(f"\n{i}. {msg_type}")

        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            print(f"   Tool calls: {len(msg.tool_calls)}")
            for tc in msg.tool_calls:
                print(f"     - {tc['name']}")

        if hasattr(msg, 'name'):
            print(f"   Name: {msg.name}")

        if hasattr(msg, 'content') and msg.content:
            content_preview = str(msg.content)[:200]
            print(f"   Content: {content_preview}...")

    print("\n" + "="*80)
    print(f"✅ Config 4 completed with {len(result['messages'])} messages")
    print("="*80 + "\n")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Run test configurations with custom queries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_custom_test.py --config 1 --query "Research the top AI companies in 2024"
  python run_custom_test.py --config 4 --query "Analyze market trends in cloud computing"
  python run_custom_test.py -c 1 -q "What are the best practices for LangGraph development?"
        """
    )

    parser.add_argument(
        '--config', '-c',
        type=int,
        choices=[1, 4],
        required=True,
        help="Configuration to run (1 or 4)"
    )

    parser.add_argument(
        '--query', '-q',
        type=str,
        required=True,
        help="Custom research query to test"
    )

    args = parser.parse_args()

    try:
        if args.config == 1:
            result = run_config_1(args.query)
        elif args.config == 4:
            result = asyncio.run(run_config_4(args.query))

        print("\n✅ Test completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
