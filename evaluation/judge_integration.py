"""
Judge Integration - Evaluation Orchestration for Prompt Testing

Provides high-level functions to run judge evaluations on agent responses,
integrating the judge_agents.py and rubrics.py components.

Replaces the missing run_evaluation_for_query() function that was imported
but not defined in judge_agents.py.
"""

from typing import Dict, Any, List
from dataclasses import asdict

from langchain_google_genai import ChatGoogleGenerativeAI

from evaluation.judge_agents import (
    JudgeRegistry,
    aggregate_judgments_to_evaluation_result
)
from evaluation.rubrics import EvaluationResult
from evaluation.test_suite import TestQuery


def run_evaluation_for_query(
    query: TestQuery,
    agent_response: str,
    judge_model: str = "gemini-2.5-flash",
    verbose: bool = False
) -> EvaluationResult:
    """
    Run all 7 judges on an agent's response to a test query.

    This is the main integration function that:
    1. Invokes JudgeRegistry to run all judges
    2. Aggregates judge decisions into EvaluationResult
    3. Returns structured evaluation with all scores

    Args:
        query: TestQuery object with query text and metadata
        agent_response: Agent's response text to evaluate
        judge_model: Model to use for judges (default: gemini-2.5-flash)
        verbose: Print progress messages

    Returns:
        EvaluationResult with all judge scores and reasoning

    Example:
        >>> from evaluation.test_suite import get_test_suite
        >>> test_suite = get_test_suite()
        >>> query = test_suite[0]  # First query
        >>> agent_response = "Research response with citations..."
        >>> result = run_evaluation_for_query(query, agent_response)
        >>> print(f"Overall score: {result.overall_score}")
        3.98
    """
    if verbose:
        print(f"  Running 7 judges on query: {query.id}")

    # Create model object from model name
    model = ChatGoogleGenerativeAI(model=judge_model, temperature=0.0)

    # Create judge registry
    registry = JudgeRegistry(model=model)

    # Run all judges (rubric_name=None means run all)
    judge_decisions = registry.evaluate(
        query=query.query,
        response=agent_response,
        rubric_name=None  # Run all 7 judges
    )

    if verbose:
        print(f"  ✓ Judges completed: {len(judge_decisions)} decisions")

    # Aggregate judge decisions into EvaluationResult
    evaluation_result = aggregate_judgments_to_evaluation_result(
        query_id=query.id,
        query_text=query.query,
        prompt_version="unknown",  # Will be set by caller
        judge_decisions=judge_decisions,
        researcher_response=agent_response
    )

    if verbose:
        print(f"  ✓ Overall score: {evaluation_result.overall_score:.2f}")

    return evaluation_result


def run_evaluation_batch(
    queries: List[TestQuery],
    responses: List[str],
    prompt_version: str,
    judge_model: str = "gemini-2.5-flash",
    verbose: bool = False
) -> List[EvaluationResult]:
    """
    Run evaluations on a batch of query-response pairs.

    More efficient than calling run_evaluation_for_query() individually
    when you need to track prompt_version across all evaluations.

    Args:
        queries: List of TestQuery objects
        responses: List of agent response strings (same order as queries)
        prompt_version: Version ID (e.g., "researcher_v3.0")
        judge_model: Model to use for judges
        verbose: Print progress messages

    Returns:
        List of EvaluationResult objects (same order as queries)

    Raises:
        ValueError: If queries and responses lists have different lengths

    Example:
        >>> from evaluation.test_suite import get_test_suite
        >>> queries = get_test_suite()[:8]  # First 8 queries
        >>> responses = ["Response 1", "Response 2", ...]  # 8 responses
        >>> results = run_evaluation_batch(
        ...     queries, responses, prompt_version="researcher_v3.0"
        ... )
        >>> len(results)
        8
    """
    if len(queries) != len(responses):
        raise ValueError(
            f"Queries and responses must have same length: "
            f"got {len(queries)} queries, {len(responses)} responses"
        )

    if verbose:
        print(f"Running batch evaluation: {len(queries)} queries")

    results = []

    for i, (query, response) in enumerate(zip(queries, responses)):
        if verbose:
            print(f"\n[{i+1}/{len(queries)}] {query.id}")

        # Run evaluation for this query
        result = run_evaluation_for_query(
            query=query,
            agent_response=response,
            judge_model=judge_model,
            verbose=verbose
        )

        # Set prompt version
        result.prompt_version = prompt_version

        results.append(result)

    if verbose:
        # Print summary statistics
        avg_score = sum(r.overall_score for r in results) / len(results)
        print(f"\n{'='*60}")
        print(f"Batch evaluation complete:")
        print(f"  - Total queries: {len(results)}")
        print(f"  - Average overall score: {avg_score:.2f}")
        print(f"  - Prompt version: {prompt_version}")
        print(f"{'='*60}")

    return results


def aggregate_results_summary(results: List[EvaluationResult]) -> Dict[str, Any]:
    """
    Aggregate evaluation results into summary statistics.

    Args:
        results: List of EvaluationResult objects

    Returns:
        Dict with mean scores for all metrics

    Example:
        >>> results = run_evaluation_batch(...)
        >>> summary = aggregate_results_summary(results)
        >>> print(summary["planning_quality_mean"])
        0.85
    """
    if not results:
        return {}

    # Calculate means for all metrics
    summary = {
        "total_queries": len(results),
        "planning_quality_mean": sum(r.planning_quality.score for r in results) / len(results),
        "execution_completeness_mean": sum(r.execution_completeness.score for r in results) / len(results),
        "source_quality_mean": sum(r.source_quality.score for r in results) / len(results),
        "citation_accuracy_mean": sum(r.citation_accuracy.score for r in results) / len(results),
        "answer_completeness_mean": sum(r.answer_completeness.score for r in results) / len(results),
        "factual_accuracy_mean": sum(r.factual_accuracy.score for r in results) / len(results),
        "autonomy_score_mean": sum(r.autonomy_score.score for r in results) / len(results),
        "overall_score_mean": sum(r.overall_score for r in results) / len(results),
    }

    return summary


def results_to_dict(results: List[EvaluationResult]) -> List[Dict[str, Any]]:
    """
    Convert EvaluationResult objects to dictionaries for JSON serialization.

    Args:
        results: List of EvaluationResult objects

    Returns:
        List of dictionaries

    Example:
        >>> results = run_evaluation_batch(...)
        >>> results_dict = results_to_dict(results)
        >>> import json
        >>> json.dump(results_dict, open("results.json", "w"), indent=2)
    """
    return [asdict(result) for result in results]


if __name__ == "__main__":
    """
    Quick test of judge integration.
    Run: python evaluation/judge_integration.py
    """
    print("="*80)
    print("JUDGE INTEGRATION - Quick Validation Test")
    print("="*80)

    # Import test suite
    from evaluation.test_suite import get_test_suite

    # Get first test query
    test_suite = get_test_suite()
    test_query = test_suite[0]

    print(f"\nTest query: {test_query.id}")
    print(f"Query text: {test_query.query[:60]}...")

    # Create mock agent response
    mock_response = """
    Research Findings:

    "AI development has accelerated significantly in 2025" [OpenAI Research, https://openai.com/research/ai-2025, Accessed: 2025-11-16] [1].

    Key trends include:
    1. Multimodal AI systems
    2. Improved reasoning capabilities
    3. Enhanced safety measures

    ## Sources
    [1] "AI development has accelerated significantly in 2025" - OpenAI Research - https://openai.com/research/ai-2025 - Accessed: 2025-11-16
    """

    print("\n" + "="*80)
    print("Running evaluation...")
    print("="*80)

    try:
        result = run_evaluation_for_query(
            query=test_query,
            agent_response=mock_response,
            judge_model="gemini-2.5-flash",
            verbose=True
        )

        print("\n" + "="*80)
        print("Evaluation Results:")
        print("="*80)
        print(f"Planning Quality: {result.planning_quality.score}")
        print(f"Execution Completeness: {result.execution_completeness.score}")
        print(f"Source Quality: {result.source_quality.score}")
        print(f"Citation Accuracy: {result.citation_accuracy.score}")
        print(f"Answer Completeness: {result.answer_completeness.score}")
        print(f"Factual Accuracy: {result.factual_accuracy.score}")
        print(f"Autonomy Score: {result.autonomy_score.score}")
        print(f"\nOverall Score: {result.overall_score:.2f}")

        print("\n" + "="*80)
        print("✓ Judge integration validation complete!")
        print("="*80)

    except Exception as e:
        print(f"\n✗ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
