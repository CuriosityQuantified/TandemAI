"""
Statistical Analysis for Evaluation Results
============================================

Implements statistical tests to compare benchmark vs challenger prompts:
- Paired t-tests
- Cohen's d effect sizes
- 95% confidence intervals
- Statistical significance determination (p < 0.05)

Version: 1.0
Created: 2025-11-13
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from scipy import stats


# ==============================================================================
# DATA MODELS
# ==============================================================================

@dataclass
class StatisticalResult:
    """Statistical test result for a single rubric."""
    rubric_name: str
    benchmark_mean: float
    challenger_mean: float
    mean_difference: float
    percent_change: float

    # Paired t-test
    t_statistic: float
    p_value: float
    degrees_of_freedom: int
    is_significant: bool  # p < 0.05

    # Effect size
    cohens_d: float
    effect_size_interpretation: str  # "negligible", "small", "medium", "large"

    # Confidence interval
    ci_95_lower: float
    ci_95_upper: float

    # Sample info
    n_pairs: int
    benchmark_std: float
    challenger_std: float


@dataclass
class ComparisonReport:
    """Complete statistical comparison report."""
    benchmark_version: str
    challenger_version: str
    total_queries: int
    timestamp: str

    # Per-rubric results
    rubric_results: Dict[str, StatisticalResult]

    # Overall summary
    significant_improvements: List[str]
    significant_regressions: List[str]
    no_significant_change: List[str]

    # Recommendation
    overall_recommendation: str  # "adopt", "reject", "inconclusive"
    recommendation_reasoning: str


# ==============================================================================
# STATISTICAL FUNCTIONS
# ==============================================================================

def calculate_cohens_d(
    group1: np.ndarray,
    group2: np.ndarray
) -> float:
    """Calculate Cohen's d effect size.

    Args:
        group1: First group of scores
        group2: Second group of scores

    Returns:
        Cohen's d effect size
    """
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

    # Cohen's d
    d = (np.mean(group2) - np.mean(group1)) / pooled_std
    return d


def interpret_cohens_d(d: float) -> str:
    """Interpret Cohen's d effect size.

    Args:
        d: Cohen's d value

    Returns:
        Interpretation string
    """
    abs_d = abs(d)
    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    else:
        return "large"


def paired_t_test_with_ci(
    benchmark_scores: np.ndarray,
    challenger_scores: np.ndarray,
    alpha: float = 0.05
) -> Tuple[float, float, int, Tuple[float, float]]:
    """Perform paired t-test and calculate confidence interval.

    Args:
        benchmark_scores: Benchmark scores
        challenger_scores: Challenger scores
        alpha: Significance level (default 0.05)

    Returns:
        Tuple of (t_statistic, p_value, df, (ci_lower, ci_upper))
    """
    # Paired t-test
    t_stat, p_value = stats.ttest_rel(challenger_scores, benchmark_scores)

    # Degrees of freedom
    n = len(benchmark_scores)
    df = n - 1

    # Calculate differences
    differences = challenger_scores - benchmark_scores
    mean_diff = np.mean(differences)
    std_diff = np.std(differences, ddof=1)
    se_diff = std_diff / np.sqrt(n)

    # 95% confidence interval
    t_critical = stats.t.ppf(1 - alpha/2, df)
    ci_lower = mean_diff - t_critical * se_diff
    ci_upper = mean_diff + t_critical * se_diff

    return t_stat, p_value, df, (ci_lower, ci_upper)


# ==============================================================================
# ANALYSIS FUNCTIONS
# ==============================================================================

def extract_scores_by_rubric(
    results_data: Dict[str, Any],
    rubric_name: str
) -> List[float]:
    """Extract scores for a specific rubric from results.

    Args:
        results_data: Aggregated results data
        rubric_name: Name of rubric

    Returns:
        List of scores
    """
    scores = []
    for query_result in results_data['query_results']:
        rubric_data = query_result['scores'].get(rubric_name)
        if rubric_data and rubric_data['error'] is None:
            scores.append(rubric_data['score'])
    return scores


def analyze_rubric(
    rubric_name: str,
    benchmark_scores: np.ndarray,
    challenger_scores: np.ndarray
) -> StatisticalResult:
    """Perform statistical analysis for a single rubric.

    Args:
        rubric_name: Name of rubric
        benchmark_scores: Benchmark scores
        challenger_scores: Challenger scores

    Returns:
        StatisticalResult
    """
    # Basic statistics
    benchmark_mean = np.mean(benchmark_scores)
    challenger_mean = np.mean(challenger_scores)
    mean_diff = challenger_mean - benchmark_mean
    pct_change = (mean_diff / benchmark_mean * 100) if benchmark_mean > 0 else 0

    # Paired t-test with CI
    t_stat, p_value, df, (ci_lower, ci_upper) = paired_t_test_with_ci(
        benchmark_scores,
        challenger_scores
    )

    # Significance
    is_significant = p_value < 0.05

    # Effect size
    cohens_d = calculate_cohens_d(benchmark_scores, challenger_scores)
    effect_interpretation = interpret_cohens_d(cohens_d)

    return StatisticalResult(
        rubric_name=rubric_name,
        benchmark_mean=float(benchmark_mean),
        challenger_mean=float(challenger_mean),
        mean_difference=float(mean_diff),
        percent_change=float(pct_change),
        t_statistic=float(t_stat),
        p_value=float(p_value),
        degrees_of_freedom=int(df),
        is_significant=is_significant,
        cohens_d=float(cohens_d),
        effect_size_interpretation=effect_interpretation,
        ci_95_lower=float(ci_lower),
        ci_95_upper=float(ci_upper),
        n_pairs=len(benchmark_scores),
        benchmark_std=float(np.std(benchmark_scores, ddof=1)),
        challenger_std=float(np.std(challenger_scores, ddof=1))
    )


def compare_prompts(
    benchmark_results_path: str | Path,
    challenger_results_path: str | Path,
    output_path: str | Path | None = None
) -> ComparisonReport:
    """Compare two prompt versions statistically.

    Args:
        benchmark_results_path: Path to benchmark aggregated results
        challenger_results_path: Path to challenger aggregated results
        output_path: Optional path to save report

    Returns:
        ComparisonReport
    """
    # Load results
    with open(benchmark_results_path, 'r') as f:
        benchmark_data = json.load(f)
    with open(challenger_results_path, 'r') as f:
        challenger_data = json.load(f)

    # Extract metadata
    benchmark_version = benchmark_data['metadata']['prompt_version']
    challenger_version = challenger_data['metadata']['prompt_version']

    # All rubrics
    rubrics = [
        'planning_quality',
        'execution_completeness',
        'source_quality',
        'citation_accuracy',
        'answer_completeness',
        'factual_accuracy',
        'autonomy_score'
    ]

    # Analyze each rubric
    rubric_results = {}
    for rubric_name in rubrics:
        benchmark_scores = np.array(
            extract_scores_by_rubric(benchmark_data, rubric_name)
        )
        challenger_scores = np.array(
            extract_scores_by_rubric(challenger_data, rubric_name)
        )

        # Ensure same number of samples
        min_len = min(len(benchmark_scores), len(challenger_scores))
        if min_len == 0:
            print(f"⚠️  Warning: No valid scores for {rubric_name}, skipping")
            continue

        benchmark_scores = benchmark_scores[:min_len]
        challenger_scores = challenger_scores[:min_len]

        result = analyze_rubric(rubric_name, benchmark_scores, challenger_scores)
        rubric_results[rubric_name] = result

    # Categorize results
    significant_improvements = []
    significant_regressions = []
    no_significant_change = []

    for rubric_name, result in rubric_results.items():
        if result.is_significant:
            if result.mean_difference > 0:
                significant_improvements.append(rubric_name)
            else:
                significant_regressions.append(rubric_name)
        else:
            no_significant_change.append(rubric_name)

    # Overall recommendation
    recommendation, reasoning = generate_recommendation(
        rubric_results,
        significant_improvements,
        significant_regressions
    )

    # Create report
    report = ComparisonReport(
        benchmark_version=benchmark_version,
        challenger_version=challenger_version,
        total_queries=min_len,
        timestamp=benchmark_data['metadata']['timestamp'],
        rubric_results=rubric_results,
        significant_improvements=significant_improvements,
        significant_regressions=significant_regressions,
        no_significant_change=no_significant_change,
        overall_recommendation=recommendation,
        recommendation_reasoning=reasoning
    )

    # Save report if path provided
    if output_path:
        save_report(report, output_path)

    return report


def generate_recommendation(
    rubric_results: Dict[str, StatisticalResult],
    improvements: List[str],
    regressions: List[str]
) -> Tuple[str, str]:
    """Generate overall recommendation.

    Args:
        rubric_results: Dictionary of rubric results
        improvements: List of rubrics with significant improvements
        regressions: List of rubrics with significant regressions

    Returns:
        Tuple of (recommendation, reasoning)
    """
    n_improvements = len(improvements)
    n_regressions = len(regressions)

    # Decision logic
    if n_regressions > 0:
        # Any regression is concerning
        recommendation = "reject"
        reasoning = (
            f"Challenger shows {n_regressions} significant regression(s) "
            f"({', '.join(regressions)}). Even with {n_improvements} improvement(s), "
            f"regressions indicate the challenger may harm performance."
        )

    elif n_improvements >= 3:
        # Strong improvements, no regressions
        recommendation = "adopt"
        reasoning = (
            f"Challenger shows {n_improvements} significant improvements "
            f"({', '.join(improvements)}) with no regressions. "
            f"Strong evidence for adoption."
        )

    elif n_improvements >= 1:
        # Moderate improvements, no regressions
        recommendation = "adopt"
        reasoning = (
            f"Challenger shows {n_improvements} significant improvement(s) "
            f"({', '.join(improvements)}) with no regressions. "
            f"Recommend adoption with monitoring."
        )

    else:
        # No significant changes
        recommendation = "inconclusive"
        reasoning = (
            f"No significant differences detected between benchmark and challenger. "
            f"May need larger sample size or the changes have minimal impact."
        )

    return recommendation, reasoning


def save_report(
    report: ComparisonReport,
    output_path: str | Path
) -> None:
    """Save comparison report to JSON file.

    Args:
        report: ComparisonReport to save
        output_path: Output file path
    """
    # Convert to dict
    report_dict = {
        'benchmark_version': report.benchmark_version,
        'challenger_version': report.challenger_version,
        'total_queries': report.total_queries,
        'timestamp': report.timestamp,
        'rubric_results': {
            name: asdict(result)
            for name, result in report.rubric_results.items()
        },
        'significant_improvements': report.significant_improvements,
        'significant_regressions': report.significant_regressions,
        'no_significant_change': report.no_significant_change,
        'overall_recommendation': report.overall_recommendation,
        'recommendation_reasoning': report.recommendation_reasoning
    }

    with open(output_path, 'w') as f:
        json.dump(report_dict, f, indent=2)


def print_report(report: ComparisonReport) -> None:
    """Print comparison report to console.

    Args:
        report: ComparisonReport to print
    """
    print("\n" + "=" * 80)
    print("STATISTICAL COMPARISON REPORT")
    print("=" * 80)
    print(f"\nBenchmark: {report.benchmark_version}")
    print(f"Challenger: {report.challenger_version}")
    print(f"Sample size: {report.total_queries} paired observations")

    print("\n" + "-" * 80)
    print("RUBRIC-BY-RUBRIC ANALYSIS")
    print("-" * 80)

    for rubric_name, result in report.rubric_results.items():
        print(f"\n{rubric_name.upper().replace('_', ' ')}")
        print(f"  Benchmark mean:  {result.benchmark_mean:.3f} (SD={result.benchmark_std:.3f})")
        print(f"  Challenger mean: {result.challenger_mean:.3f} (SD={result.challenger_std:.3f})")
        print(f"  Difference:      {result.mean_difference:+.3f} ({result.percent_change:+.1f}%)")
        print(f"  95% CI:          [{result.ci_95_lower:.3f}, {result.ci_95_upper:.3f}]")
        print(f"  t-statistic:     {result.t_statistic:.3f} (df={result.degrees_of_freedom})")
        print(f"  p-value:         {result.p_value:.4f} {'***' if result.p_value < 0.001 else '**' if result.p_value < 0.01 else '*' if result.p_value < 0.05 else 'ns'}")
        print(f"  Cohen's d:       {result.cohens_d:.3f} ({result.effect_size_interpretation})")
        print(f"  Significant:     {'✅ YES' if result.is_significant else '❌ NO'}")

    print("\n" + "-" * 80)
    print("SUMMARY")
    print("-" * 80)
    print(f"\n✅ Significant improvements: {len(report.significant_improvements)}")
    if report.significant_improvements:
        for rubric in report.significant_improvements:
            result = report.rubric_results[rubric]
            print(f"   - {rubric}: {result.mean_difference:+.3f} (p={result.p_value:.4f})")

    print(f"\n❌ Significant regressions: {len(report.significant_regressions)}")
    if report.significant_regressions:
        for rubric in report.significant_regressions:
            result = report.rubric_results[rubric]
            print(f"   - {rubric}: {result.mean_difference:+.3f} (p={result.p_value:.4f})")

    print(f"\n➖ No significant change: {len(report.no_significant_change)}")
    if report.no_significant_change:
        for rubric in report.no_significant_change:
            print(f"   - {rubric}")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print(f"\n{report.overall_recommendation.upper()}")
    print(f"\n{report.recommendation_reasoning}")
    print("\n" + "=" * 80)


# ==============================================================================
# TESTING
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("STATISTICAL ANALYSIS - Testing")
    print("=" * 80)

    # Test: Generate synthetic data
    print("\n🧪 Generating synthetic test data...")
    np.random.seed(42)

    n_queries = 32
    benchmark_scores = np.random.normal(3.5, 0.8, n_queries)  # Mean 3.5, SD 0.8
    challenger_scores = np.random.normal(3.8, 0.7, n_queries)  # Mean 3.8, SD 0.7

    # Test: Statistical analysis
    print("\n📊 Running statistical analysis...")
    result = analyze_rubric(
        "test_rubric",
        benchmark_scores,
        challenger_scores
    )

    print(f"\nResults:")
    print(f"  Benchmark mean: {result.benchmark_mean:.3f}")
    print(f"  Challenger mean: {result.challenger_mean:.3f}")
    print(f"  Difference: {result.mean_difference:+.3f}")
    print(f"  p-value: {result.p_value:.4f}")
    print(f"  Significant: {result.is_significant}")
    print(f"  Cohen's d: {result.cohens_d:.3f} ({result.effect_size_interpretation})")
    print(f"  95% CI: [{result.ci_95_lower:.3f}, {result.ci_95_upper:.3f}]")

    print("\n✅ Statistical analysis test complete!")
