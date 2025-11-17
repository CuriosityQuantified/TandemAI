"""
Quick Validation Test - 2 Queries on Researcher v3.0

Tests the complete evaluation pipeline end-to-end with minimal queries
before committing to full 32-query evaluation.

Run: python evaluation/quick_validation.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.test_suite import get_test_suite
from evaluation.agent_invoker import invoke_researcher_with_prompt
from evaluation.judge_integration import run_evaluation_for_query
from backend.prompts.versions.researcher.v3_0 import get_researcher_prompt as get_v3_0_prompt


def main():
    print("="*80)
    print("QUICK VALIDATION TEST - Researcher v3.0")
    print("="*80)
    print("\nTesting evaluation pipeline with 2 queries before full run")
    print("This validates: agent invocation → response extraction → judge evaluation")
    print()

    # Get test suite and select first 2 queries
    test_suite = get_test_suite()
    test_queries = test_suite[:2]

    print(f"Selected queries:")
    for i, q in enumerate(test_queries):
        print(f"  [{i+1}] {q.id}: {q.query[:60]}...")
    print()

    results = []

    for i, query in enumerate(test_queries):
        print(f"\n{'='*80}")
        print(f"QUERY {i+1}/2: {query.id}")
        print(f"{'='*80}")
        print(f"Query: {query.query}")
        print()

        try:
            # Step 1: Invoke researcher with v3.0 prompt
            print("Step 1: Invoking researcher agent...")
            agent_response = invoke_researcher_with_prompt(
                prompt_func=get_v3_0_prompt,
                query=query.query,
                config={
                    "configurable": {"thread_id": f"quickval_v3.0_{query.id}"},
                    "recursion_limit": 50
                }
            )
            print(f"✓ Agent completed")
            print(f"  Response length: {len(agent_response)} chars")
            print(f"\n  Response preview:")
            print(f"  {agent_response[:200]}...")
            print()

            # Step 2: Run judges
            print("Step 2: Running 7 judges...")
            eval_result = run_evaluation_for_query(
                query=query,
                agent_response=agent_response,
                judge_model="gemini-2.5-flash",
                verbose=True
            )
            print()

            # Step 3: Display results
            print("Step 3: Evaluation results:")
            print(f"  Planning Quality: {eval_result.planning_quality.score}")
            print(f"  Execution Completeness: {eval_result.execution_completeness.score}/5")
            print(f"  Source Quality: {eval_result.source_quality.score}/5")
            print(f"  Citation Accuracy: {eval_result.citation_accuracy.score}")
            print(f"  Answer Completeness: {eval_result.answer_completeness.score}/5")
            print(f"  Factual Accuracy: {eval_result.factual_accuracy.score}")
            print(f"  Autonomy Score: {eval_result.autonomy_score.score}")
            print(f"\n  Overall Score: {eval_result.overall_score:.2f}/7.0")

            results.append(eval_result)

        except Exception as e:
            print(f"\n✗ FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    # Summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")
    print(f"Queries tested: {len(results)}/2")
    if len(results) == 2:
        avg_score = sum(r.overall_score for r in results) / len(results)
        print(f"Average overall score: {avg_score:.2f}/7.0")
        print()
        print("✓ VALIDATION PASSED - Pipeline working correctly!")
        print()
        print("Ready to proceed with:")
        print("  1. Full baseline (32 queries on v3.0)")
        print("  2. Full challenger (32 queries on v3.1)")
        print("  3. Statistical comparison")
        return True
    else:
        print("\n✗ VALIDATION FAILED - Fix errors before proceeding")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
