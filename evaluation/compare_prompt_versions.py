"""
Prompt Version Comparison Tool

Runs A/B testing on different prompt versions using identical test suite and judges.
Generates statistical comparison reports with t-tests and effect sizes.

Usage:
    python evaluation/compare_prompt_versions.py \\
        --versions baseline_v1.0,supervisor_v1.1,researcher_v3.1 \\
        --test-suite evaluation/test_suite.py \\
        --judges gemini-2.5-flash \\
        --output evaluation/experiments/version_comparison_2025_11_16/

Example:
    # Compare supervisor v1.0 vs v1.1
    python evaluation/compare_prompt_versions.py \\
        --versions supervisor_v1.0,supervisor_v1.1 \\
        --quick  # Run 8-query quick validation first

Features:
    - Runs same 32-query test suite on each version
    - Uses consistent judge configuration (Gemini 2.5 Flash)
    - Calculates statistical significance (paired t-test, p-value)
    - Computes effect sizes (Cohen's d)
    - Generates comparison reports with visualizations
    - Saves results for later analysis
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
import statistics

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import evaluation framework
from evaluation.test_suite import get_test_suite, TestQuery
from evaluation.judge_agents import (
    JudgeRegistry,
    EvaluationResult,
    run_evaluation_for_query
)
from evaluation.rubrics import get_all_rubrics


# ============================================================================
# PROMPT VERSION LOADERS
# ============================================================================

def load_prompt_version(version_id: str) -> Dict[str, Any]:
    """
    Load a specific prompt version by ID.

    Args:
        version_id: Version identifier (e.g., "supervisor_v1.0", "researcher_v3.1")

    Returns:
        Dict with:
            - version_id: str
            - prompt_path: Path
            - version_number: str
            - version_date: str
            - changes: str
            - performance: Dict
            - known_issues: str

    Raises:
        FileNotFoundError: If version file doesn't exist
    """
    # Parse version_id to extract agent and version
    # Format: "supervisor_v1.0" or "researcher_v3.1"
    parts = version_id.split("_v")
    if len(parts) != 2:
        raise ValueError(f"Invalid version_id format: {version_id}. Expected: 'agent_vX.Y'")

    agent_name = parts[0]
    version_num = parts[1]

    # Determine path based on agent name
    if agent_name == "supervisor":
        prompt_path = project_root / f"backend/prompts/versions/supervisor/v{version_num}.py"
    elif agent_name == "researcher":
        prompt_path = project_root / f"backend/prompts/versions/researcher/v{version_num}.py"
    else:
        raise ValueError(f"Unknown agent: {agent_name}. Expected: supervisor or researcher")

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt version not found: {prompt_path}")

    # Load version metadata by importing the module
    spec = __import__('importlib.util').util.spec_from_file_location(f"prompt_{version_id}", prompt_path)
    module = __import__('importlib.util').util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return {
        "version_id": version_id,
        "agent_name": agent_name,
        "prompt_path": prompt_path,
        "version_number": getattr(module, "PROMPT_VERSION", "unknown"),
        "version_date": getattr(module, "PROMPT_DATE", "unknown"),
        "changes": getattr(module, "PROMPT_CHANGES", "No changelog provided"),
        "performance": getattr(module, "PROMPT_PERFORMANCE", {}),
        "known_issues": getattr(module, "KNOWN_ISSUES", "None documented"),
        "get_prompt_func": getattr(module, f"get_{agent_name}_prompt"),
    }


# ============================================================================
# EVALUATION RUNNER
# ============================================================================

def run_version_evaluation(
    version_info: Dict[str, Any],
    test_queries: List[TestQuery],
    judge_model: str = "gemini-2.5-flash",
    output_dir: Path = None
) -> Dict[str, Any]:
    """
    Run evaluation for a specific prompt version.

    Args:
        version_info: Version metadata from load_prompt_version()
        test_queries: List of test queries to run
        judge_model: Judge model to use (default: gemini-2.5-flash)
        output_dir: Where to save results

    Returns:
        Dict with:
            - version_id: str
            - total_queries: int
            - results: List[EvaluationResult]
            - aggregate_metrics: Dict[str, float]
    """
    print(f"\n{'='*80}")
    print(f"EVALUATING: {version_info['version_id']}")
    print(f"Version: {version_info['version_number']}")
    print(f"Date: {version_info['version_date']}")
    print(f"Queries: {len(test_queries)}")
    print(f"{'='*80}\n")

    results = []

    # TODO: Implement actual agent invocation
    # For now, this is a placeholder structure
    # In full implementation, this would:
    # 1. Load the prompt version
    # 2. Configure agent with that prompt
    # 3. Run agent on each test query
    # 4. Collect agent responses
    # 5. Run judges on responses
    # 6. Aggregate results

    for i, query in enumerate(test_queries):
        print(f"[{i+1}/{len(test_queries)}] Running query: {query.id}")

        # Placeholder: In real implementation, invoke agent with version's prompt
        # agent_response = invoke_agent_with_prompt(
        #     prompt_func=version_info['get_prompt_func'],
        #     query=query.query
        # )
        agent_response = f"Placeholder response for {query.id}"

        # Run judges on response
        # eval_result = run_evaluation_for_query(
        #     query=query,
        #     agent_response=agent_response,
        #     judge_model=judge_model
        # )

        # Placeholder result
        eval_result = EvaluationResult(
            query_id=query.id,
            planning_quality=0.8,
            execution_completeness=4.0,
            source_quality=4.0,
            citation_accuracy=0.9,
            answer_completeness=4.0,
            factual_accuracy=0.85,
            autonomy_score=1.0,
            judge_reasoning={}
        )

        results.append(eval_result)

    # Aggregate metrics
    aggregate_metrics = {
        "planning_quality_mean": statistics.mean([r.planning_quality for r in results]),
        "execution_completeness_mean": statistics.mean([r.execution_completeness for r in results]),
        "source_quality_mean": statistics.mean([r.source_quality for r in results]),
        "citation_accuracy_mean": statistics.mean([r.citation_accuracy for r in results]),
        "answer_completeness_mean": statistics.mean([r.answer_completeness for r in results]),
        "factual_accuracy_mean": statistics.mean([r.factual_accuracy for r in results]),
        "autonomy_score_mean": statistics.mean([r.autonomy_score for r in results]),
        "overall_score_mean": statistics.mean([
            r.planning_quality + r.execution_completeness + r.source_quality +
            r.citation_accuracy + r.answer_completeness + r.factual_accuracy + r.autonomy_score
            for r in results
        ]) / 7.0,
    }

    # Save results if output_dir provided
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        results_file = output_dir / f"{version_info['version_id']}_results.json"

        with open(results_file, 'w') as f:
            json.dump({
                "version_info": {
                    "version_id": version_info['version_id'],
                    "version_number": version_info['version_number'],
                    "version_date": version_info['version_date'],
                    "changes": version_info['changes'],
                },
                "total_queries": len(test_queries),
                "aggregate_metrics": aggregate_metrics,
                "results": [r.dict() for r in results]
            }, f, indent=2)

        print(f"\n✓ Results saved to: {results_file}")

    return {
        "version_id": version_info['version_id'],
        "total_queries": len(test_queries),
        "results": results,
        "aggregate_metrics": aggregate_metrics,
    }


# ============================================================================
# STATISTICAL COMPARISON
# ============================================================================

def calculate_cohens_d(group1: List[float], group2: List[float]) -> float:
    """
    Calculate Cohen's d effect size.

    Interpretation:
        - |d| < 0.2: Negligible
        - 0.2 ≤ |d| < 0.5: Small
        - 0.5 ≤ |d| < 0.8: Medium
        - |d| ≥ 0.8: Large
    """
    mean1 = statistics.mean(group1)
    mean2 = statistics.mean(group2)

    # Pooled standard deviation
    n1, n2 = len(group1), len(group2)
    var1 = statistics.variance(group1) if n1 > 1 else 0
    var2 = statistics.variance(group2) if n2 > 1 else 0
    pooled_std = ((var1 * (n1 - 1) + var2 * (n2 - 1)) / (n1 + n2 - 2)) ** 0.5

    if pooled_std == 0:
        return 0.0

    return (mean1 - mean2) / pooled_std


def paired_ttest(group1: List[float], group2: List[float]) -> Tuple[float, float]:
    """
    Perform paired t-test.

    Returns:
        (t_statistic, p_value)
    """
    # Simple implementation for paired t-test
    # In production, use scipy.stats.ttest_rel

    if len(group1) != len(group2):
        raise ValueError("Groups must have equal length for paired t-test")

    differences = [a - b for a, b in zip(group1, group2)]

    if len(differences) == 0:
        return 0.0, 1.0

    mean_diff = statistics.mean(differences)

    if len(differences) == 1:
        return 0.0, 1.0

    std_diff = statistics.stdev(differences)

    if std_diff == 0:
        return 0.0, 1.0

    n = len(differences)
    t_stat = mean_diff / (std_diff / (n ** 0.5))

    # Simplified p-value approximation (for production, use scipy)
    # This is a rough approximation - use scipy.stats for accurate p-values
    import math
    df = n - 1
    p_value = 2 * (1 - abs(math.erf(abs(t_stat) / math.sqrt(2))))

    return t_stat, p_value


def compare_versions(
    baseline_results: Dict[str, Any],
    comparison_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Statistical comparison of two prompt versions.

    Returns:
        Dict with comparison metrics and statistical tests
    """
    baseline_metrics = baseline_results['aggregate_metrics']
    comparison_metrics = comparison_results['aggregate_metrics']

    comparison = {
        "baseline_version": baseline_results['version_id'],
        "comparison_version": comparison_results['version_id'],
        "metric_comparisons": {},
    }

    # For each metric, calculate difference, effect size, and significance
    metrics = [
        "planning_quality_mean",
        "execution_completeness_mean",
        "source_quality_mean",
        "citation_accuracy_mean",
        "answer_completeness_mean",
        "factual_accuracy_mean",
        "autonomy_score_mean",
        "overall_score_mean",
    ]

    for metric in metrics:
        baseline_vals = [getattr(r, metric.replace("_mean", "")) for r in baseline_results['results']]
        comparison_vals = [getattr(r, metric.replace("_mean", "")) for r in comparison_results['results']]

        baseline_mean = baseline_metrics[metric]
        comparison_mean = comparison_metrics[metric]

        difference = comparison_mean - baseline_mean
        percent_change = (difference / baseline_mean * 100) if baseline_mean != 0 else 0

        # Statistical tests
        cohens_d = calculate_cohens_d(comparison_vals, baseline_vals)
        t_stat, p_value = paired_ttest(comparison_vals, baseline_vals)

        # Interpretation
        if abs(cohens_d) < 0.2:
            effect_size_interp = "Negligible"
        elif abs(cohens_d) < 0.5:
            effect_size_interp = "Small"
        elif abs(cohens_d) < 0.8:
            effect_size_interp = "Medium"
        else:
            effect_size_interp = "Large"

        significant = p_value < 0.05

        comparison["metric_comparisons"][metric] = {
            "baseline_mean": baseline_mean,
            "comparison_mean": comparison_mean,
            "difference": difference,
            "percent_change": percent_change,
            "cohens_d": cohens_d,
            "effect_size_interpretation": effect_size_interp,
            "t_statistic": t_stat,
            "p_value": p_value,
            "statistically_significant": significant,
        }

    return comparison


# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_comparison_report(
    comparisons: List[Dict[str, Any]],
    output_dir: Path
):
    """
    Generate markdown report summarizing all comparisons.
    """
    report_path = output_dir / "COMPARISON_REPORT.md"

    with open(report_path, 'w') as f:
        f.write("# Prompt Version Comparison Report\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        for comp in comparisons:
            f.write(f"## {comp['comparison_version']} vs {comp['baseline_version']}\n\n")

            f.write("| Metric | Baseline | Comparison | Δ | % Change | Effect Size | p-value | Significant? |\n")
            f.write("|--------|----------|------------|---|----------|-------------|---------|-------------|\n")

            for metric_name, metric_data in comp['metric_comparisons'].items():
                metric_display = metric_name.replace("_mean", "").replace("_", " ").title()

                baseline = f"{metric_data['baseline_mean']:.3f}"
                comparison = f"{metric_data['comparison_mean']:.3f}"
                diff = f"{metric_data['difference']:+.3f}"
                pct = f"{metric_data['percent_change']:+.1f}%"
                cohens_d = f"{metric_data['cohens_d']:.2f} ({metric_data['effect_size_interpretation']})"
                p_val = f"{metric_data['p_value']:.4f}"
                sig = "✅ Yes" if metric_data['statistically_significant'] else "❌ No"

                f.write(f"| {metric_display} | {baseline} | {comparison} | {diff} | {pct} | {cohens_d} | {p_val} | {sig} |\n")

            f.write("\n")

            # Summary
            f.write("### Summary\n\n")
            significant_improvements = sum(
                1 for m in comp['metric_comparisons'].values()
                if m['statistically_significant'] and m['difference'] > 0
            )
            significant_regressions = sum(
                1 for m in comp['metric_comparisons'].values()
                if m['statistically_significant'] and m['difference'] < 0
            )

            f.write(f"- **Significant Improvements**: {significant_improvements}/8 metrics\n")
            f.write(f"- **Significant Regressions**: {significant_regressions}/8 metrics\n")

            overall_improvement = comp['metric_comparisons']['overall_score_mean']['difference']
            overall_pct = comp['metric_comparisons']['overall_score_mean']['percent_change']
            f.write(f"- **Overall Score Change**: {overall_improvement:+.3f} ({overall_pct:+.1f}%)\n")

            f.write("\n---\n\n")

    print(f"\n✓ Comparison report saved to: {report_path}")


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Compare different prompt versions using identical test suite and judges",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--versions",
        type=str,
        required=True,
        help="Comma-separated list of version IDs (e.g., supervisor_v1.0,supervisor_v1.1)"
    )

    parser.add_argument(
        "--baseline",
        type=str,
        default=None,
        help="Baseline version for comparison (default: first version in list)"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick 8-query validation instead of full 32-query suite"
    )

    parser.add_argument(
        "--judge-model",
        type=str,
        default="gemini-2.5-flash",
        help="Judge model to use (default: gemini-2.5-flash)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory (default: evaluation/experiments/version_comparison_{timestamp}/)"
    )

    args = parser.parse_args()

    # Parse version IDs
    version_ids = [v.strip() for v in args.versions.split(",")]

    if len(version_ids) < 2:
        print("❌ Error: Must specify at least 2 versions for comparison")
        sys.exit(1)

    # Determine baseline
    baseline_id = args.baseline if args.baseline else version_ids[0]

    if baseline_id not in version_ids:
        print(f"❌ Error: Baseline version '{baseline_id}' not in version list")
        sys.exit(1)

    # Load test suite
    test_suite = get_test_suite()
    if args.quick:
        # Use first 8 queries for quick validation
        test_queries = test_suite[:8]
        print(f"🚀 Running QUICK validation with {len(test_queries)} queries")
    else:
        test_queries = test_suite
        print(f"🚀 Running FULL evaluation with {len(test_queries)} queries")

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = project_root / f"evaluation/experiments/version_comparison_{timestamp}"

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")

    # Load all versions
    print(f"\n{'='*80}")
    print("LOADING PROMPT VERSIONS")
    print(f"{'='*80}\n")

    version_infos = {}
    for version_id in version_ids:
        try:
            version_info = load_prompt_version(version_id)
            version_infos[version_id] = version_info
            print(f"✓ Loaded: {version_id} (v{version_info['version_number']})")
        except Exception as e:
            print(f"❌ Error loading {version_id}: {e}")
            sys.exit(1)

    # Run evaluations
    print(f"\n{'='*80}")
    print("RUNNING EVALUATIONS")
    print(f"{'='*80}\n")

    all_results = {}
    for version_id in version_ids:
        results = run_version_evaluation(
            version_info=version_infos[version_id],
            test_queries=test_queries,
            judge_model=args.judge_model,
            output_dir=output_dir
        )
        all_results[version_id] = results

    # Compare all versions to baseline
    print(f"\n{'='*80}")
    print("STATISTICAL COMPARISON")
    print(f"{'='*80}\n")

    comparisons = []
    baseline_results = all_results[baseline_id]

    for version_id in version_ids:
        if version_id == baseline_id:
            continue

        comparison = compare_versions(
            baseline_results=baseline_results,
            comparison_results=all_results[version_id]
        )
        comparisons.append(comparison)

        print(f"\n📊 {version_id} vs {baseline_id}:")
        print(f"   Overall score: {comparison['metric_comparisons']['overall_score_mean']['difference']:+.3f} "
              f"({comparison['metric_comparisons']['overall_score_mean']['percent_change']:+.1f}%)")
        print(f"   Significant improvements: {sum(1 for m in comparison['metric_comparisons'].values() if m['statistically_significant'] and m['difference'] > 0)}/8")

    # Generate report
    print(f"\n{'='*80}")
    print("GENERATING REPORT")
    print(f"{'='*80}\n")

    generate_comparison_report(comparisons, output_dir)

    print(f"\n{'='*80}")
    print("✅ COMPARISON COMPLETE")
    print(f"{'='*80}\n")
    print(f"Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
