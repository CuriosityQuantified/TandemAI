"""
Evaluation Test Runner
======================

Orchestrates running 32 queries × 7 judges = 224 evaluations.
Runs both benchmark and challenger prompts and collects all judge ratings.

Features:
- Parallel execution for efficiency
- Progress tracking and resumption
- Result persistence
- Error handling and retry logic

Version: 1.0
Created: 2025-11-13
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Literal
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import traceback

from dotenv import load_dotenv
from tqdm import tqdm

# LangChain imports
from langchain_anthropic import ChatAnthropic

# Local imports
from evaluation.judge_agents import JudgeRegistry
from evaluation.rubrics import EvaluationResult, BinaryScore, ScaledScore

load_dotenv('/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.env')


# ==============================================================================
# DATA MODELS
# ==============================================================================

@dataclass
class ResearcherResponse:
    """Response from researcher agent."""
    query_id: int
    query_text: str
    prompt_version: str
    response_text: str
    execution_time: float
    error: str | None = None
    metadata: Dict[str, Any] | None = None


@dataclass
class EvaluationTask:
    """Single evaluation task."""
    query_id: int
    query_text: str
    prompt_version: str
    researcher_response: str
    rubric_name: str


@dataclass
class EvaluationTaskResult:
    """Result of single evaluation task."""
    query_id: int
    query_text: str
    prompt_version: str
    rubric_name: str
    score: float
    reasoning: str
    evaluation_time: float
    error: str | None = None


# ==============================================================================
# TEST RUNNER
# ==============================================================================

class EvaluationRunner:
    """Orchestrates evaluation of researcher agents."""

    def __init__(
        self,
        results_dir: str | Path = "./results",
        max_workers: int = 4,
        use_cache: bool = True
    ):
        """Initialize evaluation runner.

        Args:
            results_dir: Directory to store results
            max_workers: Max parallel workers for evaluation
            use_cache: Whether to use cached results
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True, parents=True)
        self.max_workers = max_workers
        self.use_cache = use_cache

        # Initialize judge registry
        self.judge_registry = JudgeRegistry()

        # Load query dataset
        self.queries = self._load_queries()

        print(f"✅ Initialized EvaluationRunner")
        print(f"   Results dir: {self.results_dir}")
        print(f"   Total queries: {len(self.queries)}")
        print(f"   Max workers: {max_workers}")

    def _load_queries(self) -> List[Dict[str, Any]]:
        """Load query dataset."""
        dataset_path = Path("prompts/researcher/query_dataset.json")
        if not dataset_path.exists():
            raise FileNotFoundError(f"Query dataset not found: {dataset_path}")

        with open(dataset_path, 'r') as f:
            data = json.load(f)

        return data['queries']

    def _get_cache_path(
        self,
        query_id: int,
        prompt_version: str,
        stage: Literal["response", "evaluation"]
    ) -> Path:
        """Get cache file path for a specific evaluation."""
        return self.results_dir / f"{stage}_{prompt_version}_q{query_id}.json"

    def _load_cached_response(
        self,
        query_id: int,
        prompt_version: str
    ) -> ResearcherResponse | None:
        """Load cached researcher response if available."""
        if not self.use_cache:
            return None

        cache_path = self._get_cache_path(query_id, prompt_version, "response")
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                data = json.load(f)
                return ResearcherResponse(**data)
        return None

    def _save_response_cache(self, response: ResearcherResponse) -> None:
        """Save researcher response to cache."""
        cache_path = self._get_cache_path(
            response.query_id,
            response.prompt_version,
            "response"
        )
        with open(cache_path, 'w') as f:
            json.dump(asdict(response), f, indent=2)

    def _load_cached_evaluation(
        self,
        query_id: int,
        prompt_version: str
    ) -> Dict[str, Any] | None:
        """Load cached evaluation results if available."""
        if not self.use_cache:
            return None

        cache_path = self._get_cache_path(query_id, prompt_version, "evaluation")
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                return json.load(f)
        return None

    def _save_evaluation_cache(
        self,
        query_id: int,
        prompt_version: str,
        evaluation: Dict[str, Any]
    ) -> None:
        """Save evaluation results to cache."""
        cache_path = self._get_cache_path(query_id, prompt_version, "evaluation")
        with open(cache_path, 'w') as f:
            json.dump(evaluation, f, indent=2)

    def run_researcher_query(
        self,
        query: Dict[str, Any],
        prompt_version: str,
        researcher_agent: Any
    ) -> ResearcherResponse:
        """Run a single query through researcher agent.

        Args:
            query: Query dict from dataset
            prompt_version: "benchmark" or "challenger_1", etc.
            researcher_agent: Configured researcher agent

        Returns:
            ResearcherResponse with result or error
        """
        query_id = query['id']
        query_text = query['query']

        # Check cache
        cached = self._load_cached_response(query_id, prompt_version)
        if cached:
            return cached

        # Run query
        try:
            start_time = datetime.now()

            # TODO: Actually invoke researcher agent
            # For now, return placeholder
            response_text = f"[Researcher response for query {query_id} with {prompt_version}]"
            metadata = {
                'category': query.get('category'),
                'complexity': query.get('complexity'),
                'expected_steps': query.get('expected_steps')
            }

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            response = ResearcherResponse(
                query_id=query_id,
                query_text=query_text,
                prompt_version=prompt_version,
                response_text=response_text,
                execution_time=execution_time,
                error=None,
                metadata=metadata
            )

            # Cache the response
            self._save_response_cache(response)
            return response

        except Exception as e:
            return ResearcherResponse(
                query_id=query_id,
                query_text=query_text,
                prompt_version=prompt_version,
                response_text="",
                execution_time=0.0,
                error=str(e),
                metadata={'traceback': traceback.format_exc()}
            )

    def run_single_evaluation(
        self,
        task: EvaluationTask
    ) -> EvaluationTaskResult:
        """Run a single judge evaluation.

        Args:
            task: EvaluationTask to execute

        Returns:
            EvaluationTaskResult
        """
        try:
            start_time = datetime.now()

            # Run judge
            result = self.judge_registry.evaluate(
                query=task.query_text,
                response=task.researcher_response,
                rubric_name=task.rubric_name
            )

            end_time = datetime.now()
            evaluation_time = (end_time - start_time).total_seconds()

            # Extract score and reasoning
            judge_result = result.get(task.rubric_name, {})
            score = judge_result.get('score', 0.0)
            reasoning = judge_result.get('reasoning', 'No reasoning provided')

            return EvaluationTaskResult(
                query_id=task.query_id,
                query_text=task.query_text,
                prompt_version=task.prompt_version,
                rubric_name=task.rubric_name,
                score=float(score),
                reasoning=reasoning,
                evaluation_time=evaluation_time,
                error=None
            )

        except Exception as e:
            return EvaluationTaskResult(
                query_id=task.query_id,
                query_text=task.query_text,
                prompt_version=task.prompt_version,
                rubric_name=task.rubric_name,
                score=0.0,
                reasoning="",
                evaluation_time=0.0,
                error=f"{type(e).__name__}: {str(e)}"
            )

    def run_evaluation_batch(
        self,
        prompt_version: str,
        researcher_agent: Any | None = None,
        query_ids: List[int] | None = None
    ) -> Dict[str, Any]:
        """Run evaluation for a batch of queries.

        Args:
            prompt_version: "benchmark" or "challenger_1", etc.
            researcher_agent: Configured researcher agent (None = use placeholder)
            query_ids: Specific query IDs to run (None = all)

        Returns:
            Dictionary with results and statistics
        """
        # Filter queries if needed
        queries_to_run = self.queries
        if query_ids:
            queries_to_run = [q for q in self.queries if q['id'] in query_ids]

        print(f"\n{'=' * 80}")
        print(f"RUNNING EVALUATION BATCH: {prompt_version}")
        print(f"{'=' * 80}")
        print(f"Queries to evaluate: {len(queries_to_run)}")
        print(f"Judges per query: 7")
        print(f"Total evaluations: {len(queries_to_run) * 7}")

        # Step 1: Collect researcher responses
        print(f"\n📝 Step 1: Collecting researcher responses...")
        responses: List[ResearcherResponse] = []

        for query in tqdm(queries_to_run, desc="Researcher queries"):
            response = self.run_researcher_query(query, prompt_version, researcher_agent)
            responses.append(response)

        # Count errors
        error_count = sum(1 for r in responses if r.error)
        print(f"   ✅ Collected {len(responses)} responses ({error_count} errors)")

        # Step 2: Create evaluation tasks (7 judges × N queries)
        print(f"\n🔍 Step 2: Creating evaluation tasks...")
        tasks: List[EvaluationTask] = []
        rubrics = [
            'planning_quality',
            'execution_completeness',
            'source_quality',
            'citation_accuracy',
            'answer_completeness',
            'factual_accuracy',
            'autonomy_score'
        ]

        for response in responses:
            if response.error:
                continue  # Skip failed responses

            for rubric_name in rubrics:
                tasks.append(EvaluationTask(
                    query_id=response.query_id,
                    query_text=response.query_text,
                    prompt_version=prompt_version,
                    researcher_response=response.response_text,
                    rubric_name=rubric_name
                ))

        print(f"   ✅ Created {len(tasks)} evaluation tasks")

        # Step 3: Run evaluations in parallel
        print(f"\n⚖️  Step 3: Running judge evaluations (max {self.max_workers} parallel)...")
        evaluation_results: List[EvaluationTaskResult] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.run_single_evaluation, task): task
                for task in tasks
            }

            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Evaluations"
            ):
                result = future.result()
                evaluation_results.append(result)

        # Count evaluation errors
        eval_error_count = sum(1 for r in evaluation_results if r.error)
        print(f"   ✅ Completed {len(evaluation_results)} evaluations ({eval_error_count} errors)")

        # Step 4: Aggregate results
        print(f"\n📊 Step 4: Aggregating results...")
        aggregated = self._aggregate_results(
            prompt_version,
            responses,
            evaluation_results
        )

        # Save aggregated results
        output_path = self.results_dir / f"aggregated_{prompt_version}.json"
        with open(output_path, 'w') as f:
            json.dump(aggregated, f, indent=2)

        print(f"   ✅ Saved aggregated results to {output_path}")

        return aggregated

    def _aggregate_results(
        self,
        prompt_version: str,
        responses: List[ResearcherResponse],
        evaluations: List[EvaluationTaskResult]
    ) -> Dict[str, Any]:
        """Aggregate evaluation results."""
        # Group evaluations by query
        by_query: Dict[int, Dict[str, Any]] = {}

        for response in responses:
            query_id = response.query_id
            by_query[query_id] = {
                'query_id': query_id,
                'query_text': response.query_text,
                'prompt_version': prompt_version,
                'response': response.response_text,
                'execution_time': response.execution_time,
                'response_error': response.error,
                'scores': {},
                'metadata': response.metadata
            }

        # Add evaluation scores
        for eval_result in evaluations:
            query_id = eval_result.query_id
            rubric_name = eval_result.rubric_name

            if query_id in by_query:
                by_query[query_id]['scores'][rubric_name] = {
                    'score': eval_result.score,
                    'reasoning': eval_result.reasoning,
                    'evaluation_time': eval_result.evaluation_time,
                    'error': eval_result.error
                }

        # Calculate summary statistics
        all_scores: Dict[str, List[float]] = {
            'planning_quality': [],
            'execution_completeness': [],
            'source_quality': [],
            'citation_accuracy': [],
            'answer_completeness': [],
            'factual_accuracy': [],
            'autonomy_score': []
        }

        for query_data in by_query.values():
            for rubric_name, score_data in query_data['scores'].items():
                if score_data['error'] is None:
                    all_scores[rubric_name].append(score_data['score'])

        summary_stats = {}
        for rubric_name, scores in all_scores.items():
            if scores:
                summary_stats[rubric_name] = {
                    'mean': sum(scores) / len(scores),
                    'min': min(scores),
                    'max': max(scores),
                    'count': len(scores)
                }
            else:
                summary_stats[rubric_name] = {
                    'mean': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'count': 0
                }

        return {
            'metadata': {
                'prompt_version': prompt_version,
                'total_queries': len(by_query),
                'timestamp': datetime.now().isoformat(),
                'runner_version': '1.0'
            },
            'summary_statistics': summary_stats,
            'query_results': list(by_query.values())
        }

    def compare_prompts(
        self,
        benchmark_version: str = "benchmark",
        challenger_version: str = "challenger_1"
    ) -> Dict[str, Any]:
        """Compare two prompt versions.

        Args:
            benchmark_version: Baseline prompt version
            challenger_version: Challenger prompt version

        Returns:
            Comparison results
        """
        print(f"\n{'=' * 80}")
        print(f"COMPARING PROMPTS")
        print(f"{'=' * 80}")
        print(f"Benchmark: {benchmark_version}")
        print(f"Challenger: {challenger_version}")

        # Load aggregated results
        benchmark_path = self.results_dir / f"aggregated_{benchmark_version}.json"
        challenger_path = self.results_dir / f"aggregated_{challenger_version}.json"

        if not benchmark_path.exists():
            raise FileNotFoundError(f"Benchmark results not found: {benchmark_path}")
        if not challenger_path.exists():
            raise FileNotFoundError(f"Challenger results not found: {challenger_path}")

        with open(benchmark_path, 'r') as f:
            benchmark_data = json.load(f)
        with open(challenger_path, 'r') as f:
            challenger_data = json.load(f)

        # Extract scores for comparison
        comparison = {
            'metadata': {
                'benchmark_version': benchmark_version,
                'challenger_version': challenger_version,
                'timestamp': datetime.now().isoformat()
            },
            'summary_comparison': {},
            'detailed_comparison': []
        }

        # Summary comparison
        benchmark_stats = benchmark_data['summary_statistics']
        challenger_stats = challenger_data['summary_statistics']

        for rubric_name in benchmark_stats.keys():
            b_mean = benchmark_stats[rubric_name]['mean']
            c_mean = challenger_stats[rubric_name]['mean']
            diff = c_mean - b_mean
            pct_change = (diff / b_mean * 100) if b_mean > 0 else 0

            comparison['summary_comparison'][rubric_name] = {
                'benchmark_mean': b_mean,
                'challenger_mean': c_mean,
                'difference': diff,
                'percent_change': pct_change
            }

        print(f"\n📊 Summary Comparison:")
        for rubric_name, stats in comparison['summary_comparison'].items():
            print(f"\n{rubric_name}:")
            print(f"   Benchmark: {stats['benchmark_mean']:.3f}")
            print(f"   Challenger: {stats['challenger_mean']:.3f}")
            print(f"   Difference: {stats['difference']:+.3f} ({stats['percent_change']:+.1f}%)")

        # Save comparison
        output_path = self.results_dir / f"comparison_{benchmark_version}_vs_{challenger_version}.json"
        with open(output_path, 'w') as f:
            json.dump(comparison, f, indent=2)

        print(f"\n✅ Saved comparison to {output_path}")

        return comparison


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

def run_evaluation(
    prompt_version: str,
    researcher_agent: Any | None = None,
    query_ids: List[int] | None = None,
    results_dir: str = "./results",
    max_workers: int = 4
) -> Dict[str, Any]:
    """Convenience function to run evaluation.

    Args:
        prompt_version: Prompt version to evaluate
        researcher_agent: Researcher agent (None = placeholder)
        query_ids: Specific queries to run (None = all)
        results_dir: Results directory
        max_workers: Max parallel workers

    Returns:
        Aggregated results
    """
    runner = EvaluationRunner(
        results_dir=results_dir,
        max_workers=max_workers
    )
    return runner.run_evaluation_batch(
        prompt_version=prompt_version,
        researcher_agent=researcher_agent,
        query_ids=query_ids
    )


# ==============================================================================
# TESTING
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("EVALUATION TEST RUNNER - Testing")
    print("=" * 80)

    # Test: Run small evaluation batch
    runner = EvaluationRunner(
        results_dir="./results",
        max_workers=2
    )

    print("\n🧪 Running test evaluation on queries 1-3...")
    results = runner.run_evaluation_batch(
        prompt_version="test_benchmark",
        researcher_agent=None,
        query_ids=[1, 2, 3]
    )

    print("\n✅ Test complete!")
    print(f"Evaluated {results['metadata']['total_queries']} queries")
    print("\nSummary statistics:")
    for rubric_name, stats in results['summary_statistics'].items():
        print(f"  {rubric_name}: {stats['mean']:.3f} (n={stats['count']})")
