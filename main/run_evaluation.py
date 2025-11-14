#!/usr/bin/env python3
"""
Baseline Evaluation Runner
===========================

Main script to run evaluation framework for researcher agent prompts.

Usage:
    # Run benchmark evaluation (all 32 queries)
    python run_evaluation.py --version benchmark

    # Run challenger evaluation
    python run_evaluation.py --version challenger_1

    # Run comparison
    python run_evaluation.py --compare benchmark challenger_1

    # Run on specific queries only
    python run_evaluation.py --version benchmark --queries 1,2,3

    # Adjust parallelism
    python run_evaluation.py --version benchmark --workers 8

Version: 1.0
Created: 2025-11-13
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from evaluation.test_runner import EvaluationRunner
from evaluation.statistical_analysis import compare_prompts, print_report

# Load environment variables
load_dotenv('/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.env')


def run_evaluation_cli(args):
    """Run evaluation from CLI arguments."""
    print("\n" + "=" * 80)
    print("RESEARCHER AGENT EVALUATION FRAMEWORK")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")

    # Initialize runner
    runner = EvaluationRunner(
        results_dir=args.results_dir,
        max_workers=args.workers,
        use_cache=not args.no_cache
    )

    # Parse query IDs if provided
    query_ids = None
    if args.queries:
        query_ids = [int(q.strip()) for q in args.queries.split(',')]
        print(f"\n📋 Running on specific queries: {query_ids}")

    # Run evaluation
    if args.version:
        print(f"\n🚀 Running evaluation for: {args.version}")
        results = runner.run_evaluation_batch(
            prompt_version=args.version,
            researcher_agent=None,  # TODO: Load actual agent
            query_ids=query_ids
        )

        print("\n" + "=" * 80)
        print("EVALUATION COMPLETE")
        print("=" * 80)
        print(f"\nResults saved to: {runner.results_dir}")
        print(f"Evaluated queries: {results['metadata']['total_queries']}")

        print("\n📊 Summary Statistics:")
        for rubric_name, stats in results['summary_statistics'].items():
            print(f"  {rubric_name}: {stats['mean']:.3f} ± {stats['count']}")

    elif args.compare:
        print(f"\n📊 Comparing prompts: {args.compare[0]} vs {args.compare[1]}")

        benchmark_path = Path(args.results_dir) / f"aggregated_{args.compare[0]}.json"
        challenger_path = Path(args.results_dir) / f"aggregated_{args.compare[1]}.json"

        if not benchmark_path.exists():
            print(f"\n❌ Error: Benchmark results not found: {benchmark_path}")
            print(f"   Run evaluation first: python run_evaluation.py --version {args.compare[0]}")
            return

        if not challenger_path.exists():
            print(f"\n❌ Error: Challenger results not found: {challenger_path}")
            print(f"   Run evaluation first: python run_evaluation.py --version {args.compare[1]}")
            return

        # Run comparison
        output_path = Path(args.results_dir) / f"statistical_comparison_{args.compare[0]}_vs_{args.compare[1]}.json"
        report = compare_prompts(
            benchmark_path,
            challenger_path,
            output_path
        )

        # Print report
        print_report(report)

        print(f"\n✅ Statistical report saved to: {output_path}")

    print(f"\n⏰ Completed at: {datetime.now().isoformat()}")
    print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run evaluation framework for researcher agent prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run benchmark evaluation
  python run_evaluation.py --version benchmark

  # Run challenger evaluation
  python run_evaluation.py --version challenger_1

  # Compare benchmark vs challenger
  python run_evaluation.py --compare benchmark challenger_1

  # Run on specific queries
  python run_evaluation.py --version benchmark --queries 1,2,3,4,5

  # Adjust parallelism
  python run_evaluation.py --version benchmark --workers 8

Results:
  Results are saved to ./results/ directory by default.
  Each evaluation creates:
    - response_<version>_q<N>.json (cached researcher responses)
    - evaluation_<version>_q<N>.json (cached evaluations)
    - aggregated_<version>.json (summary statistics)
    - statistical_comparison_<v1>_vs_<v2>.json (comparison report)
        """
    )

    # Main action: either run evaluation or compare
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--version',
        type=str,
        help='Prompt version to evaluate (e.g., "benchmark", "challenger_1")'
    )
    group.add_argument(
        '--compare',
        nargs=2,
        metavar=('BENCHMARK', 'CHALLENGER'),
        help='Compare two prompt versions statistically'
    )

    # Optional arguments
    parser.add_argument(
        '--queries',
        type=str,
        help='Comma-separated query IDs to run (e.g., "1,2,3,4,5"). Default: all queries'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers for evaluation (default: 4)'
    )
    parser.add_argument(
        '--results-dir',
        type=str,
        default='./results',
        help='Directory to store results (default: ./results)'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching (re-run all evaluations)'
    )

    args = parser.parse_args()

    # Run evaluation
    try:
        run_evaluation_cli(args)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
