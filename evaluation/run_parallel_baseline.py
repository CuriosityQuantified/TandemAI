"""
Run Full Baseline Evaluation (32 queries) on Researcher v3.0 - PARALLEL EXECUTION

This script runs all 32 test queries in parallel using asyncio for maximum speed.
Uses a semaphore to limit concurrency and avoid overwhelming the API.

Usage:
    python evaluation/run_parallel_baseline.py

Expected runtime: ~3-5 minutes (vs ~30-60 minutes sequential)
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.test_suite import get_test_suite
from evaluation.agent_invoker import async_invoke_researcher_batch
from evaluation.judge_integration import run_evaluation_for_query
from evaluation.rubrics import EvaluationResult
from backend.prompts.versions.researcher.v3_0 import get_researcher_prompt as get_v3_0_prompt


async def run_parallel_baseline_evaluation(
    max_concurrency: int = 10,
    save_results: bool = True
):
    """
    Run all 32 queries on researcher v3.0 in parallel.

    Args:
        max_concurrency: Maximum concurrent agent executions (default: 10)
        save_results: Whether to save results to JSON file

    Returns:
        List of EvaluationResult objects
    """
    print("=" * 80)
    print("PARALLEL BASELINE EVALUATION - Researcher v3.0")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  - Total queries: 32")
    print(f"  - Max concurrency: {max_concurrency}")
    print(f"  - Prompt version: v3.0 (baseline)")
    print(f"  - Judge model: gemini-2.5-flash")
    print()

    # Step 1: Get test suite
    print("Step 1: Loading test suite...")
    test_suite = get_test_suite()
    queries = [q.query for q in test_suite]
    print(f"  ✓ Loaded {len(queries)} queries\n")

    # Step 2: Run all agents in parallel
    print("Step 2: Running all 32 agent executions in parallel...")
    print(f"{'=' * 80}\n")

    start_time = datetime.now()

    responses = await async_invoke_researcher_batch(
        prompt_func=get_v3_0_prompt,
        queries=queries,
        max_concurrency=max_concurrency,
        verbose=True
    )

    agent_duration = (datetime.now() - start_time).total_seconds()

    print(f"\n✓ All agents completed in {agent_duration:.1f} seconds")
    print(f"  Average: {agent_duration/len(queries):.1f} sec/query\n")

    # Step 3: Run judges on all responses (sequential for now)
    print(f"\nStep 3: Running judge evaluations on {len(responses)} responses...")
    print(f"{'=' * 80}\n")

    results = []
    judge_start = datetime.now()

    for i, (query_obj, response) in enumerate(zip(test_suite, responses)):
        print(f"[{i+1}/{len(responses)}] Judging: {query_obj.id}")

        try:
            eval_result = run_evaluation_for_query(
                query=query_obj,
                agent_response=response,
                judge_model="gemini-2.5-flash",
                verbose=False
            )

            # Set metadata
            eval_result.prompt_version = "researcher_v3.0"

            results.append(eval_result)

            print(f"  ✓ Score: {eval_result.overall_score:.2f}/19")

        except Exception as e:
            print(f"  ✗ Judge failed: {str(e)}")
            continue

    judge_duration = (datetime.now() - start_time).total_seconds()

    print(f"\n✓ All judge evaluations completed in {judge_duration:.1f} seconds")
    print(f"  Average: {judge_duration/len(results):.1f} sec/query\n")

    # Step 4: Calculate summary statistics
    print(f"\n{'=' * 80}")
    print("EVALUATION SUMMARY")
    print(f"{'=' * 80}\n")

    total_duration = (datetime.now() - start_time).total_seconds()

    print(f"Total time: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
    print(f"Queries completed: {len(results)}/{len(test_suite)}")
    print()

    if results:
        # Overall scores
        avg_overall = sum(r.overall_score for r in results) / len(results)
        print(f"Average overall score: {avg_overall:.2f}/19")
        print()

        # Individual metrics
        print("Average scores by metric:")
        print(f"  Planning Quality:        {sum(r.planning_quality.score for r in results) / len(results):.2f}/1")
        print(f"  Execution Completeness:  {sum(r.execution_completeness.score for r in results) / len(results):.2f}/5")
        print(f"  Source Quality:          {sum(r.source_quality.score for r in results) / len(results):.2f}/5")
        print(f"  Citation Accuracy:       {sum(r.citation_accuracy.score for r in results) / len(results):.2f}/1")
        print(f"  Answer Completeness:     {sum(r.answer_completeness.score for r in results) / len(results):.2f}/5")
        print(f"  Factual Accuracy:        {sum(r.factual_accuracy.score for r in results) / len(results):.2f}/1")
        print(f"  Autonomy Score:          {sum(r.autonomy_score.score for r in results) / len(results):.2f}/1")

    # Step 5: Save results
    if save_results and results:
        output_dir = Path(__file__).parent / "experiments" / f"baseline_v3.0_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "results.json"

        results_data = {
            "metadata": {
                "prompt_version": "researcher_v3.0",
                "timestamp": datetime.now().isoformat(),
                "total_queries": len(test_suite),
                "completed_queries": len(results),
                "max_concurrency": max_concurrency,
                "total_duration_seconds": total_duration,
                "agent_duration_seconds": agent_duration,
                "judge_duration_seconds": judge_duration
            },
            "summary": {
                "average_overall_score": avg_overall if results else 0,
                "average_planning_quality": sum(r.planning_quality.score for r in results) / len(results) if results else 0,
                "average_execution_completeness": sum(r.execution_completeness.score for r in results) / len(results) if results else 0,
                "average_source_quality": sum(r.source_quality.score for r in results) / len(results) if results else 0,
                "average_citation_accuracy": sum(r.citation_accuracy.score for r in results) / len(results) if results else 0,
                "average_answer_completeness": sum(r.answer_completeness.score for r in results) / len(results) if results else 0,
                "average_factual_accuracy": sum(r.factual_accuracy.score for r in results) / len(results) if results else 0,
                "average_autonomy_score": sum(r.autonomy_score.score for r in results) / len(results) if results else 0
            },
            "results": [
                {
                    "query_id": r.query_id,
                    "query_text": r.query_text,
                    "overall_score": r.overall_score,
                    "planning_quality": r.planning_quality.score,
                    "execution_completeness": r.execution_completeness.score,
                    "source_quality": r.source_quality.score,
                    "citation_accuracy": r.citation_accuracy.score,
                    "answer_completeness": r.answer_completeness.score,
                    "factual_accuracy": r.factual_accuracy.score,
                    "autonomy_score": r.autonomy_score.score
                }
                for r in results
            ]
        }

        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"\n✓ Results saved to: {output_file}")

    print(f"\n{'=' * 80}\n")

    return results


if __name__ == "__main__":
    print("\n🚀 Starting parallel baseline evaluation...\n")

    # Run async main function
    results = asyncio.run(run_parallel_baseline_evaluation(
        max_concurrency=10,  # Adjust based on API limits
        save_results=True
    ))

    print("✅ Evaluation complete!")

    # Exit with success if we got results
    sys.exit(0 if results else 1)
