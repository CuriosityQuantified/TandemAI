"""
Full 32-Test Evaluation Runner for Challenger V3 Configuration
================================================================

This script runs the complete 32-test evaluation suite on the Challenger V3
configuration with citation verification.

Expected Behavior:
- Runs all 32 test queries across 4 categories
- Tests automatic citation verification system
- Generates comprehensive evaluation report with judge scores
- Outputs results to evaluation/experiments/challenger_v3_full_eval/

Usage:
    python run_challenger_v3_full_eval.py
    python run_challenger_v3_full_eval.py --max-tests 10  # Run only 10 tests
    python run_challenger_v3_full_eval.py --category simple  # Run only simple category
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import argparse
import json

# Add project root to path
root_path = Path(__file__).parent
sys.path.insert(0, str(root_path))

# Load environment
from dotenv import load_dotenv
load_dotenv(root_path / ".env")

# Import evaluation framework
from evaluation.test_suite import (
    TEST_QUERIES,
    run_evaluation,
    print_evaluation_summary,
    save_results,
    QueryCategory
)

# Import V3 configuration
from evaluation.configs.test_config_challenger_3 import graph
from langchain_core.messages import HumanMessage


def create_challenger_v3_agent():
    """
    Create agent function that wraps the Challenger V3 graph.

    Returns:
        Callable with signature: agent(query: str) -> Dict[str, Any]
    """

    def execute_query(query: str) -> Dict[str, Any]:
        """Execute query with Challenger V3 configuration."""

        print(f"\n{'='*80}")
        print(f"EXECUTING QUERY WITH CHALLENGER V3")
        print(f"{'='*80}")
        print(f"Query: {query}")
        print()

        start_time = datetime.now()

        try:
            # Run the V3 graph
            result = graph.invoke(
                {"messages": [HumanMessage(content=query)]},
                config={
                    "configurable": {"thread_id": f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"},
                    "recursion_limit": 75
                }
            )

            execution_time = (datetime.now() - start_time).total_seconds()
            messages = result.get("messages", [])

            print(f"\n✅ V3 execution completed in {execution_time:.1f}s")
            print(f"   Total messages: {len(messages)}")

            # Extract final response
            final_response = None
            for msg in reversed(messages):
                if hasattr(msg, 'content') and msg.content and not (hasattr(msg, 'tool_calls') and msg.tool_calls):
                    final_response = msg.content
                    break

            # Handle structured response format
            if final_response and isinstance(final_response, list):
                if isinstance(final_response[0], dict) and 'text' in final_response[0]:
                    final_response = final_response[0]['text']

            # Check citation verification
            verify_calls = [
                msg for msg in messages
                if hasattr(msg, 'name') and msg.name == 'verify_citations'
            ]

            citation_verified = False
            if verify_calls:
                try:
                    final_verification = json.loads(verify_calls[-1].content)
                    citation_verified = final_verification.get("all_verified", False)
                except:
                    pass

            print(f"   Citation verification: {citation_verified}")
            print()

            return {
                "messages": messages,
                "response": final_response or "(No response generated)",
                "execution_time": execution_time,
                "citation_verified": citation_verified,
                "plan": None,  # V3 doesn't expose plan structure
                "files": []
            }

        except Exception as e:
            print(f"\n❌ V3 execution failed: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "messages": [],
                "response": f"Error: {str(e)}",
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "citation_verified": False,
                "error": str(e)
            }

    return execute_query


def main():
    """Main evaluation runner for Challenger V3."""

    parser = argparse.ArgumentParser(
        description="Run full 32-test evaluation on Challenger V3 configuration"
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["simple", "multi_aspect", "time_constrained", "comprehensive"],
        help="Run tests for specific category only"
    )
    parser.add_argument(
        "--max-tests",
        type=int,
        help="Maximum number of tests to run"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation/experiments/challenger_v3_full_eval/results.json",
        help="Output path for results"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--test-id",
        type=str,
        help="Run a specific test by ID (e.g., 'simple_1')"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("CHALLENGER V3 FULL EVALUATION")
    print("=" * 80)
    print()
    print("Configuration:")
    print("  - Agent: Challenger V3 (Citation Verification)")
    print("  - Model: Gemini 2.0 Flash Exp")
    print("  - Temperature: 0.3")
    print("  - Features: Automatic citation verification, graph-level enforcement")
    print()

    # Create agent function
    print("Step 1: Initializing Challenger V3 agent...")
    agent_function = create_challenger_v3_agent()
    print("✅ Agent initialized")
    print()

    # Determine which tests to run
    if args.test_id:
        print(f"Step 2: Running single test: {args.test_id}")
        # For single test, we need custom handling
        queries = [q for q in TEST_QUERIES if q.test_id == args.test_id]
        if not queries:
            print(f"❌ Test ID '{args.test_id}' not found")
            return 1
        print(f"   Total tests to run: {len(queries)}")
        print()

        # Run evaluation manually for single test
        print("=" * 80)
        print("RUNNING EVALUATION")
        print("=" * 80)
        print()

        evaluation_start = datetime.now()
        results = []
        for query in queries:
            print(f"Running test: {query.test_id} - {query.query}")
            response = agent_function(query.query)
            results.append({
                "test_id": query.test_id,
                "query": query.query,
                "category": query.category.value,
                "response_data": response,
                "scores": {}  # Would need judge evaluation
            })
    else:
        if args.category:
            print(f"Step 2: Running tests for category: {args.category}")
        else:
            print("Step 2: Running all 32 tests")

        if args.max_tests:
            print(f"   Limited to {args.max_tests} tests")

        print()

        # Run evaluation
        print("=" * 80)
        print("RUNNING EVALUATION")
        print("=" * 80)
        print()

        evaluation_start = datetime.now()

        results = run_evaluation(
            agent_function=agent_function,
            category=args.category,
            max_tests=args.max_tests,
            verbose=args.verbose
        )

    evaluation_duration = (datetime.now() - evaluation_start).total_seconds()

    print()
    print("=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    print(f"Total duration: {evaluation_duration:.1f}s")
    print()

    # Print summary
    print_evaluation_summary(results)

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    save_results(results, str(output_path))
    print()
    print(f"✅ Results saved to: {output_path}")
    print()

    # Calculate citation verification rate
    citation_verified_count = sum(
        1 for r in results
        if r.get("response_data", {}).get("citation_verified", False)
    )
    print(f"Citation Verification Rate: {citation_verified_count}/{len(results)} "
          f"({100*citation_verified_count/len(results):.1f}%)")
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Evaluation failed with error:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
