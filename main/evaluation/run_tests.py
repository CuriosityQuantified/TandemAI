"""
Run Evaluation Tests for Benchmark Researcher Agent

This script demonstrates how to run the evaluation test suite against
the benchmark researcher agent and generate comprehensive reports.

USAGE:
    # Run all tests
    python evaluation/run_tests.py

    # Run specific category
    python evaluation/run_tests.py --category simple

    # Run limited number of tests
    python evaluation/run_tests.py --max-tests 5

    # Run with custom output path
    python evaluation/run_tests.py --output results/my_eval.json
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import argparse
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test suite
from evaluation.test_suite import (
    TEST_QUERIES,
    run_evaluation,
    print_evaluation_summary,
    save_results,
    QueryCategory
)

# Import the researcher agent (adjust import based on your setup)
# This assumes you have module-2-2-simple.py or similar with the agent


# ==============================================================================
# AGENT WRAPPER FUNCTION
# ==============================================================================

def create_agent_function():
    """
    Create an agent function compatible with the test suite.

    The test suite expects a function with signature:
        agent_function(query: str) -> Dict[str, Any]

    The returned dict should contain:
        - messages: List of messages (final message has the response)
        - plan: Optional plan dict with steps
        - files: Optional list of files created

    Returns:
        Callable agent function
    """
    # Import your agent setup here
    # Example: from module_2_2_simple import setup_agent

    # For demonstration, we'll create a placeholder
    # Replace this with your actual agent implementation

    try:
        # Option 1: Import from existing module
        from module_2_2_simple import setup_agent, run_agent_task
        print("✓ Loaded agent from module_2_2_simple.py")

        def agent_function(query: str) -> Dict[str, Any]:
            """Wrapper for run_agent_task"""
            result = run_agent_task(query, thread_id=f"eval_{datetime.now().timestamp()}")
            return result

        return agent_function

    except ImportError:
        print("⚠️  Could not import module_2_2_simple.py")
        print("Creating mock agent for demonstration purposes")

        def mock_agent(query: str) -> Dict[str, Any]:
            """
            Mock agent for testing the evaluation framework.
            Replace this with your actual agent.
            """
            # Simulate agent response
            from langchain_core.messages import HumanMessage, AIMessage

            return {
                "messages": [
                    HumanMessage(content=query),
                    AIMessage(content=f"""
Based on my research, here are the findings:

"Example finding from source" [Example Source, https://example.com, Accessed: {datetime.now().strftime('%Y-%m-%d')}]

This demonstrates the citation format expected by the evaluation framework.

## Additional Findings

"Another exact quote from a different source" [Another Source, https://example2.com, Accessed: {datetime.now().strftime('%Y-%m-%d')}]

## Source List

1. Example Source - https://example.com
2. Another Source - https://example2.com
                    """)
                ],
                "plan": {
                    "steps": [
                        {"step_index": 0, "description": "Research topic", "status": "completed"},
                        {"step_index": 1, "description": "Verify findings", "status": "completed"},
                        {"step_index": 2, "description": "Compile results", "status": "completed"}
                    ]
                },
                "files": []
            }

        return mock_agent


# ==============================================================================
# MAIN EVALUATION RUNNER
# ==============================================================================

def main():
    """Main evaluation runner"""
    parser = argparse.ArgumentParser(
        description="Run evaluation tests for benchmark researcher agent"
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
        default="/Users/nicholaspate/Documents/01_Active/ATLAS/main/results/evaluation_results.json",
        help="Output path for results JSON"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Print verbose output"
    )
    parser.add_argument(
        "--test-id",
        type=str,
        help="Run a single test by ID (e.g., SIMPLE-001)"
    )

    args = parser.parse_args()

    print(f"""
{'='*80}
BENCHMARK RESEARCHER AGENT - EVALUATION FRAMEWORK
{'='*80}

Configuration:
  Category: {args.category or 'All'}
  Max Tests: {args.max_tests or 'Unlimited'}
  Output: {args.output}
  Verbose: {args.verbose}
  Test ID: {args.test_id or 'All'}

{'='*80}
""")

    # Create agent function
    print("\nInitializing agent...")
    agent_function = create_agent_function()
    print("✓ Agent initialized\n")

    # Run evaluation
    if args.test_id:
        # Run single test
        test_query = next((q for q in TEST_QUERIES if q.id == args.test_id), None)
        if not test_query:
            print(f"Error: Test ID '{args.test_id}' not found")
            sys.exit(1)

        print(f"Running single test: {args.test_id}")
        from evaluation.test_suite import run_single_test
        result = run_single_test(agent_function, test_query, verbose=args.verbose)
        results = [result]

    else:
        # Run multiple tests
        results = run_evaluation(
            agent_function=agent_function,
            category=args.category,
            max_tests=args.max_tests,
            verbose=args.verbose
        )

    # Print summary
    print_evaluation_summary(results)

    # Save results
    save_results(results, output_path=args.output)

    # Print final stats
    passed = sum(1 for r in results if r.overall_pass)
    total = len(results)
    pass_rate = (passed / total) * 100 if total > 0 else 0

    print(f"""
{'='*80}
EVALUATION COMPLETE
{'='*80}

Final Results:
  Tests Run: {total}
  Tests Passed: {passed}
  Pass Rate: {pass_rate:.1f}%

Results saved to: {args.output}

Next Steps:
  1. Review detailed results in {args.output}
  2. Analyze failed tests to identify improvement areas
  3. Iterate on prompt engineering based on findings
  4. Re-run evaluation to measure improvements

{'='*80}
""")

    # Exit with appropriate code
    sys.exit(0 if pass_rate >= 70 else 1)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def list_tests():
    """List all available tests"""
    print(f"\nAvailable Tests ({len(TEST_QUERIES)} total):\n")

    from collections import defaultdict
    by_category = defaultdict(list)
    for q in TEST_QUERIES:
        by_category[q.category].append(q)

    for category in [QueryCategory.SIMPLE, QueryCategory.MULTI_ASPECT,
                     QueryCategory.TIME_CONSTRAINED, QueryCategory.COMPREHENSIVE]:
        queries = by_category[category]
        print(f"{category.value.upper()} ({len(queries)} tests):")
        for q in queries:
            print(f"  {q.id}: {q.query[:70]}...")
        print()


def analyze_results(results_path: str):
    """Analyze saved results"""
    import json

    with open(results_path, 'r') as f:
        data = json.load(f)

    print(f"\nAnalyzing results from: {results_path}")
    print(f"Timestamp: {data['timestamp']}")
    print(f"Total Tests: {data['total_tests']}")
    print(f"Passed: {data['passed']}")
    print(f"Pass Rate: {(data['passed']/data['total_tests'])*100:.1f}%\n")

    # Find failing tests
    failing = [r for r in data['results'] if not r['overall_pass']]
    if failing:
        print(f"Failing Tests ({len(failing)}):")
        for r in failing:
            print(f"  {r['test_query']['id']}: {r['test_query']['query'][:60]}...")
            print(f"    Issues: {', '.join(r['notes'])}")
        print()


# ==============================================================================
# CLI COMMANDS
# ==============================================================================

if __name__ == "__main__":
    # Check for special commands
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_tests()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "analyze":
        if len(sys.argv) < 3:
            print("Usage: python evaluation/run_tests.py analyze <results_path>")
            sys.exit(1)
        analyze_results(sys.argv[2])
        sys.exit(0)

    # Run main evaluation
    main()
