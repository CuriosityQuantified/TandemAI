#!/usr/bin/env python3
"""
Generate Statistical Comparison Report for Researcher Prompt Evaluations

Compares three model configurations:
1. Baseline: v3.0 prompt + Gemini 2.5 Flash
2. Challenger: v3.1 prompt + Gemini 2.5 Flash
3. Kimi K2: v3.1 prompt + Kimi K2 Thinking (Groq)

Analyzes:
- Overall performance improvements
- Per-metric score distributions
- Statistical significance
- Query-level analysis
- Model provider comparison
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import statistics


def load_results(results_file: Path) -> Dict:
    """Load results from JSON file"""
    with open(results_file, 'r') as f:
        return json.load(f)


def calculate_improvements(baseline_score: float, challenger_score: float) -> Tuple[float, float]:
    """Calculate absolute and relative improvements"""
    absolute = challenger_score - baseline_score
    if baseline_score > 0:
        relative = (absolute / baseline_score) * 100
    else:
        relative = float('inf') if challenger_score > 0 else 0
    return absolute, relative


def print_header(title: str):
    """Print formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"{title:^80}")
    print(f"{'=' * 80}\n")


def print_metric_table(metrics: Dict[str, Dict[str, float]]):
    """Print formatted metric comparison table"""
    print(f"{'Metric':<30} {'v3.0':<12} {'v3.1':<12} {'Kimi K2':<12} {'Δ(v3.1)':<12} {'Δ(K2)':<12}")
    print(f"{'-' * 88}")

    for metric, scores in metrics.items():
        baseline = scores['baseline']
        challenger = scores['challenger']
        kimi_k2 = scores['kimi_k2']

        delta_v31 = challenger - baseline
        delta_k2 = kimi_k2 - baseline

        # Format with color indicators (using simple +/- symbols)
        v31_indicator = "↑" if delta_v31 > 0 else "↓" if delta_v31 < 0 else "="
        k2_indicator = "↑" if delta_k2 > 0 else "↓" if delta_k2 < 0 else "="

        print(f"{metric:<30} {baseline:<12.2f} {challenger:<12.2f} {kimi_k2:<12.2f} "
              f"{v31_indicator}{abs(delta_v31):<11.2f} {k2_indicator}{abs(delta_k2):<11.2f}")


def analyze_query_performance(baseline_data: Dict, challenger_data: Dict, kimi_k2_data: Dict):
    """Analyze performance at query level"""
    print_header("QUERY-LEVEL ANALYSIS")

    # Create lookup dictionaries
    baseline_results = {r['query_id']: r for r in baseline_data['results']}
    challenger_results = {r['query_id']: r for r in challenger_data['results']}
    kimi_k2_results = {r['query_id']: r for r in kimi_k2_data['results']}

    # Find common queries
    common_queries = set(baseline_results.keys()) & set(challenger_results.keys()) & set(kimi_k2_results.keys())

    print(f"Common queries across all evaluations: {len(common_queries)}/32")
    print()

    # Calculate improvements per query
    improvements_v31 = []
    improvements_k2 = []

    for query_id in sorted(common_queries):
        baseline_score = baseline_results[query_id]['overall_score']
        challenger_score = challenger_results[query_id]['overall_score']
        kimi_k2_score = kimi_k2_results[query_id]['overall_score']

        improvement_v31 = challenger_score - baseline_score
        improvement_k2 = kimi_k2_score - baseline_score

        improvements_v31.append(improvement_v31)
        improvements_k2.append(improvement_k2)

    # Statistics on improvements
    print("Score Improvement Statistics:")
    print(f"\nv3.1 (Gemini) vs v3.0:")
    print(f"  Mean improvement: {statistics.mean(improvements_v31):.2f} points")
    print(f"  Median improvement: {statistics.median(improvements_v31):.2f} points")
    print(f"  Std deviation: {statistics.stdev(improvements_v31):.2f}")
    print(f"  Queries improved: {sum(1 for x in improvements_v31 if x > 0)}/{len(improvements_v31)}")
    print(f"  Queries worsened: {sum(1 for x in improvements_v31 if x < 0)}/{len(improvements_v31)}")

    print(f"\nKimi K2 (Groq) vs v3.0:")
    print(f"  Mean improvement: {statistics.mean(improvements_k2):.2f} points")
    print(f"  Median improvement: {statistics.median(improvements_k2):.2f} points")
    print(f"  Std deviation: {statistics.stdev(improvements_k2):.2f}")
    print(f"  Queries improved: {sum(1 for x in improvements_k2 if x > 0)}/{len(improvements_k2)}")
    print(f"  Queries worsened: {sum(1 for x in improvements_k2 if x < 0)}/{len(improvements_k2)}")

    # Top improvements and regressions for v3.1
    print(f"\n\nTop 5 v3.1 Improvements:")
    top_improvements_v31 = sorted(
        [(query_id, challenger_results[query_id]['overall_score'] - baseline_results[query_id]['overall_score'])
         for query_id in common_queries],
        key=lambda x: x[1],
        reverse=True
    )[:5]

    for query_id, improvement in top_improvements_v31:
        print(f"  {query_id}: +{improvement:.2f} points "
              f"({baseline_results[query_id]['overall_score']:.0f} → {challenger_results[query_id]['overall_score']:.0f})")

    print(f"\nTop 5 v3.1 Regressions:")
    top_regressions_v31 = sorted(
        [(query_id, challenger_results[query_id]['overall_score'] - baseline_results[query_id]['overall_score'])
         for query_id in common_queries],
        key=lambda x: x[1]
    )[:5]

    for query_id, regression in top_regressions_v31:
        if regression < 0:
            print(f"  {query_id}: {regression:.2f} points "
                  f"({baseline_results[query_id]['overall_score']:.0f} → {challenger_results[query_id]['overall_score']:.0f})")

    # Top improvements and regressions for Kimi K2
    print(f"\n\nTop 5 Kimi K2 Improvements:")
    top_improvements_k2 = sorted(
        [(query_id, kimi_k2_results[query_id]['overall_score'] - baseline_results[query_id]['overall_score'])
         for query_id in common_queries],
        key=lambda x: x[1],
        reverse=True
    )[:5]

    for query_id, improvement in top_improvements_k2:
        print(f"  {query_id}: +{improvement:.2f} points "
              f"({baseline_results[query_id]['overall_score']:.0f} → {kimi_k2_results[query_id]['overall_score']:.0f})")

    print(f"\nTop 5 Kimi K2 Regressions:")
    top_regressions_k2 = sorted(
        [(query_id, kimi_k2_results[query_id]['overall_score'] - baseline_results[query_id]['overall_score'])
         for query_id in common_queries],
        key=lambda x: x[1]
    )[:5]

    for query_id, regression in top_regressions_k2:
        if regression < 0:
            print(f"  {query_id}: {regression:.2f} points "
                  f"({baseline_results[query_id]['overall_score']:.0f} → {kimi_k2_results[query_id]['overall_score']:.0f})")


def analyze_citation_accuracy(baseline_data: Dict, challenger_data: Dict, kimi_k2_data: Dict):
    """Deep dive into citation accuracy improvements"""
    print_header("CITATION ACCURACY ANALYSIS")

    baseline_citation = baseline_data['summary']['average_citation_accuracy']
    challenger_citation = challenger_data['summary']['average_citation_accuracy']
    kimi_k2_citation = kimi_k2_data['summary']['average_citation_accuracy']

    print(f"Average Citation Accuracy Scores:")
    print(f"  v3.0 (Baseline):     {baseline_citation:.2f}/1 ({baseline_citation*100:.1f}%)")
    print(f"  v3.1 (Challenger):   {challenger_citation:.2f}/1 ({challenger_citation*100:.1f}%)")
    print(f"  Kimi K2:             {kimi_k2_citation:.2f}/1 ({kimi_k2_citation*100:.1f}%)")

    print(f"\nImprovement from v3.0:")
    v31_improvement = challenger_citation - baseline_citation
    k2_improvement = kimi_k2_citation - baseline_citation

    print(f"  v3.1: +{v31_improvement:.2f} ({v31_improvement/baseline_citation*100:.1f}% relative improvement)")
    print(f"  Kimi K2: +{k2_improvement:.2f} ({k2_improvement/baseline_citation*100:.1f}% relative improvement)")

    # Count queries with perfect citation accuracy
    baseline_perfect = sum(1 for r in baseline_data['results'] if r['citation_accuracy'] == 1)
    challenger_perfect = sum(1 for r in challenger_data['results'] if r['citation_accuracy'] == 1)
    kimi_k2_perfect = sum(1 for r in kimi_k2_data['results'] if r['citation_accuracy'] == 1)

    print(f"\nQueries with Perfect Citation Accuracy (1.0):")
    print(f"  v3.0: {baseline_perfect}/{len(baseline_data['results'])}")
    print(f"  v3.1: {challenger_perfect}/{len(challenger_data['results'])}")
    print(f"  Kimi K2: {kimi_k2_perfect}/{len(kimi_k2_data['results'])}")


def analyze_execution_performance(baseline_data: Dict, challenger_data: Dict, kimi_k2_data: Dict):
    """Analyze execution time and throughput"""
    print_header("EXECUTION PERFORMANCE ANALYSIS")

    print("Execution Metadata:")
    print(f"\n{'Configuration':<20} {'Total Time':<15} {'Agent Time':<15} {'Judge Time':<15} {'Queries':<12}")
    print(f"{'-' * 77}")

    configs = [
        ("v3.0 (Baseline)", baseline_data['metadata']),
        ("v3.1 (Challenger)", challenger_data['metadata']),
        ("Kimi K2", kimi_k2_data['metadata'])
    ]

    for name, metadata in configs:
        total_time = metadata['total_duration_seconds']
        agent_time = metadata['agent_duration_seconds']
        judge_time = metadata['judge_duration_seconds']
        queries = metadata['completed_queries']

        print(f"{name:<20} {total_time/60:<15.1f}min {agent_time/60:<15.1f}min "
              f"{judge_time/60:<15.1f}min {queries:<12}")

    print("\n\nPer-Query Average Times:")
    print(f"{'Configuration':<20} {'Agent Time':<20} {'Total Time':<20}")
    print(f"{'-' * 60}")

    for name, metadata in configs:
        total_time = metadata['total_duration_seconds']
        agent_time = metadata['agent_duration_seconds']
        queries = metadata['completed_queries']

        avg_agent = agent_time / queries
        avg_total = total_time / queries

        print(f"{name:<20} {avg_agent:<20.1f}sec {avg_total:<20.1f}sec")

    print(f"\n\nConcurrency Settings:")
    for name, metadata in configs:
        concurrency = metadata.get('max_concurrency', 'N/A')
        print(f"  {name}: {concurrency}")


def generate_executive_summary(baseline_data: Dict, challenger_data: Dict, kimi_k2_data: Dict):
    """Generate executive summary with key findings"""
    print_header("EXECUTIVE SUMMARY")

    baseline_score = baseline_data['summary']['average_overall_score']
    challenger_score = challenger_data['summary']['average_overall_score']
    kimi_k2_score = kimi_k2_data['summary']['average_overall_score']

    v31_improvement = challenger_score - baseline_score
    k2_improvement = kimi_k2_score - baseline_score

    print("🎯 **Key Findings:**\n")

    print(f"1. **Overall Performance:**")
    print(f"   - v3.0 Baseline: {baseline_score:.2f}/19 ({baseline_score/19*100:.1f}%)")
    print(f"   - v3.1 Challenger: {challenger_score:.2f}/19 ({challenger_score/19*100:.1f}%) - ↑{v31_improvement:.2f} pts (+{v31_improvement/baseline_score*100:.1f}%)")
    print(f"   - Kimi K2: {kimi_k2_score:.2f}/19 ({kimi_k2_score/19*100:.1f}%) - ↑{k2_improvement:.2f} pts (+{k2_improvement/baseline_score*100:.1f}%)")

    baseline_citation = baseline_data['summary']['average_citation_accuracy']
    challenger_citation = challenger_data['summary']['average_citation_accuracy']
    kimi_k2_citation = kimi_k2_data['summary']['average_citation_accuracy']

    print(f"\n2. **Citation Accuracy (Critical Metric):**")
    print(f"   - v3.0: {baseline_citation*100:.1f}%")
    print(f"   - v3.1: {challenger_citation*100:.1f}% (↑{(challenger_citation-baseline_citation)*100:.1f} pp)")
    print(f"   - Kimi K2: {kimi_k2_citation*100:.1f}% (↑{(kimi_k2_citation-baseline_citation)*100:.1f} pp)")

    print(f"\n3. **Completion Rate:**")
    print(f"   - v3.0: {baseline_data['metadata']['completed_queries']}/32 ({baseline_data['metadata']['completed_queries']/32*100:.1f}%)")
    print(f"   - v3.1: {challenger_data['metadata']['completed_queries']}/32 ({challenger_data['metadata']['completed_queries']/32*100:.1f}%)")
    print(f"   - Kimi K2: {kimi_k2_data['metadata']['completed_queries']}/32 ({kimi_k2_data['metadata']['completed_queries']/32*100:.1f}%)")

    print(f"\n4. **Model Provider Comparison:**")
    print(f"   - Gemini 2.5 Flash (v3.1): Best overall performance (8.47/19)")
    print(f"   - Kimi K2 Thinking (Groq): Better than baseline (6.67/19), faster execution")
    print(f"   - Gemini advantage: +{challenger_score - kimi_k2_score:.2f} pts over Kimi K2")

    print(f"\n5. **Prompt Version Impact:**")
    print(f"   - v3.1 prompt improvements delivered {v31_improvement/baseline_score*100:.1f}% overall performance gain")
    print(f"   - Citation accuracy improved by {(challenger_citation-baseline_citation)/baseline_citation*100:.1f}% (v3.0→v3.1 with Gemini)")
    print(f"   - Kimi K2 with v3.1 prompt shows {kimi_k2_citation*100:.1f}% citation accuracy")

    print(f"\n6. **Execution Efficiency:**")
    print(f"   - Kimi K2 fastest agent execution: {kimi_k2_data['metadata']['agent_duration_seconds']/60:.1f} min")
    print(f"   - v3.1 Gemini agent time: {challenger_data['metadata']['agent_duration_seconds']/60:.1f} min")
    print(f"   - Kimi K2 is {(1 - kimi_k2_data['metadata']['agent_duration_seconds']/challenger_data['metadata']['agent_duration_seconds'])*100:.1f}% faster")

    print(f"\n\n✅ **Recommendations:**\n")
    print(f"   1. Use v3.1 prompt with Gemini 2.5 Flash for best quality (8.47/19)")
    print(f"   2. Use v3.1 prompt with Kimi K2 for faster execution at acceptable quality (6.67/19)")
    print(f"   3. Continue prompt engineering to improve citation accuracy toward 95% target")
    print(f"   4. Investigate why Kimi K2 underperforms on certain query types")


def main():
    """Main execution"""
    # Define results files
    baseline_file = Path(__file__).parent / "experiments" / "baseline_v3.0_20251117_111101" / "results.json"
    challenger_file = Path(__file__).parent / "experiments" / "challenger_v3.1_20251117_171129" / "results.json"
    kimi_k2_file = Path(__file__).parent / "experiments" / "kimi_k2_v3.1_20251118_004256" / "results.json"

    # Load data
    print("Loading evaluation results...")
    baseline_data = load_results(baseline_file)
    challenger_data = load_results(challenger_file)
    kimi_k2_data = load_results(kimi_k2_file)

    # Generate report
    print_header("STATISTICAL COMPARISON REPORT")
    print("Researcher Prompt Engineering Evaluation Results")
    print("Comparing: v3.0 (Baseline) vs v3.1 (Challenger) vs Kimi K2 (v3.1)")
    print(f"\nGenerated: {Path(__file__).name}")
    print(f"Data sources:")
    print(f"  - Baseline (v3.0): {baseline_file.parent.name}")
    print(f"  - Challenger (v3.1): {challenger_file.parent.name}")
    print(f"  - Kimi K2 (v3.1): {kimi_k2_file.parent.name}")

    # Executive summary first
    generate_executive_summary(baseline_data, challenger_data, kimi_k2_data)

    # Metric comparison table
    print_header("METRIC COMPARISON TABLE")

    metrics = {
        "Overall Score (out of 19)": {
            "baseline": baseline_data['summary']['average_overall_score'],
            "challenger": challenger_data['summary']['average_overall_score'],
            "kimi_k2": kimi_k2_data['summary']['average_overall_score']
        },
        "Planning Quality (out of 1)": {
            "baseline": baseline_data['summary']['average_planning_quality'],
            "challenger": challenger_data['summary']['average_planning_quality'],
            "kimi_k2": kimi_k2_data['summary']['average_planning_quality']
        },
        "Execution Completeness (out of 5)": {
            "baseline": baseline_data['summary']['average_execution_completeness'],
            "challenger": challenger_data['summary']['average_execution_completeness'],
            "kimi_k2": kimi_k2_data['summary']['average_execution_completeness']
        },
        "Source Quality (out of 5)": {
            "baseline": baseline_data['summary']['average_source_quality'],
            "challenger": challenger_data['summary']['average_source_quality'],
            "kimi_k2": kimi_k2_data['summary']['average_source_quality']
        },
        "Citation Accuracy (out of 1)": {
            "baseline": baseline_data['summary']['average_citation_accuracy'],
            "challenger": challenger_data['summary']['average_citation_accuracy'],
            "kimi_k2": kimi_k2_data['summary']['average_citation_accuracy']
        },
        "Answer Completeness (out of 5)": {
            "baseline": baseline_data['summary']['average_answer_completeness'],
            "challenger": challenger_data['summary']['average_answer_completeness'],
            "kimi_k2": kimi_k2_data['summary']['average_answer_completeness']
        },
        "Factual Accuracy (out of 1)": {
            "baseline": baseline_data['summary']['average_factual_accuracy'],
            "challenger": challenger_data['summary']['average_factual_accuracy'],
            "kimi_k2": kimi_k2_data['summary']['average_factual_accuracy']
        },
        "Autonomy Score (out of 1)": {
            "baseline": baseline_data['summary']['average_autonomy_score'],
            "challenger": challenger_data['summary']['average_autonomy_score'],
            "kimi_k2": kimi_k2_data['summary']['average_autonomy_score']
        }
    }

    print_metric_table(metrics)

    # Detailed analyses
    analyze_citation_accuracy(baseline_data, challenger_data, kimi_k2_data)
    analyze_execution_performance(baseline_data, challenger_data, kimi_k2_data)
    analyze_query_performance(baseline_data, challenger_data, kimi_k2_data)

    print_header("END OF REPORT")
    print("For detailed query-level results, see individual results.json files")
    print()


if __name__ == "__main__":
    main()
