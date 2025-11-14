#!/usr/bin/env python3
"""
Phase 6 Cost Estimation and Optimization Analysis

Estimates API costs for benchmark evaluation and identifies cost reduction strategies.

Usage:
    python ESTIMATE_PHASE_6_COST.py
"""

from dataclasses import dataclass
from typing import Dict, List
import json

# ============================================================================
# ANTHROPIC PRICING (as of January 2025)
# Source: https://www.anthropic.com/pricing
# ============================================================================

@dataclass
class ModelPricing:
    """Anthropic Claude model pricing per million tokens"""
    name: str
    input_per_mtok: float   # USD per million input tokens
    output_per_mtok: float  # USD per million output tokens
    supports_prompt_caching: bool = False
    cache_write_per_mtok: float = 0.0  # Cost to write to cache
    cache_read_per_mtok: float = 0.0   # Cost to read from cache

# Current Anthropic pricing
MODELS = {
    "haiku-3.5": ModelPricing(
        name="Claude 3.5 Haiku",
        input_per_mtok=0.25,
        output_per_mtok=1.25,
        supports_prompt_caching=True,
        cache_write_per_mtok=0.30,  # 20% markup for cache writes
        cache_read_per_mtok=0.025   # 90% discount for cache reads
    ),
    "haiku-4.5": ModelPricing(
        name="Claude 4.5 Haiku",
        input_per_mtok=1.00,
        output_per_mtok=5.00,
        supports_prompt_caching=True,
        cache_write_per_mtok=1.25,  # 25% markup for cache writes
        cache_read_per_mtok=0.10    # 90% discount for cache reads
    ),
    "sonnet-3.5": ModelPricing(
        name="Claude 3.5 Sonnet",
        input_per_mtok=3.00,
        output_per_mtok=15.00,
        supports_prompt_caching=True,
        cache_write_per_mtok=3.75,   # 25% markup
        cache_read_per_mtok=0.30     # 90% discount
    ),
    "opus-3": ModelPricing(
        name="Claude 3 Opus",
        input_per_mtok=15.00,
        output_per_mtok=75.00,
        supports_prompt_caching=True,
        cache_write_per_mtok=18.75,
        cache_read_per_mtok=1.50
    )
}

# ============================================================================
# TOKEN USAGE ESTIMATES
# ============================================================================

@dataclass
class TokenEstimate:
    """Token usage estimates for different components"""
    component: str
    input_tokens: int
    output_tokens: int
    description: str

# Researcher Agent Estimates (per query)
RESEARCHER_ESTIMATES = [
    TokenEstimate(
        component="System Prompt (Benchmark)",
        input_tokens=7267,
        output_tokens=0,
        description="Benchmark researcher prompt (Enhanced V3)"
    ),
    TokenEstimate(
        component="User Query",
        input_tokens=150,  # Average query length
        output_tokens=0,
        description="Research question from test suite"
    ),
    TokenEstimate(
        component="Supervisor Decision",
        input_tokens=500,
        output_tokens=100,
        description="Supervisor analyzes and delegates"
    ),
    TokenEstimate(
        component="Delegation Tool Call",
        input_tokens=200,
        output_tokens=50,
        description="Tool call to delegate to researcher"
    ),
    TokenEstimate(
        component="Research Planning",
        input_tokens=1000,
        output_tokens=500,
        description="Create research plan (3-5 steps)"
    ),
    TokenEstimate(
        component="Web Search (Tavily) x3",
        input_tokens=600,
        output_tokens=300,
        description="3 web searches with results"
    ),
    TokenEstimate(
        component="Research Execution",
        input_tokens=2000,
        output_tokens=1500,
        description="Process search results, synthesize"
    ),
    TokenEstimate(
        component="Final Answer Generation",
        input_tokens=3000,
        output_tokens=2000,
        description="Comprehensive research report with citations"
    )
]

# Judge Agent Estimates (per evaluation)
JUDGE_ESTIMATES = [
    TokenEstimate(
        component="Judge System Prompt",
        input_tokens=800,
        output_tokens=0,
        description="Rubric-specific judge prompt"
    ),
    TokenEstimate(
        component="Original Query",
        input_tokens=150,
        output_tokens=0,
        description="Research question being evaluated"
    ),
    TokenEstimate(
        component="Researcher Response",
        input_tokens=2500,
        output_tokens=0,
        description="Full researcher answer to evaluate"
    ),
    TokenEstimate(
        component="Judge Reasoning",
        input_tokens=500,
        output_tokens=400,
        description="Judge analyzes response against rubric"
    ),
    TokenEstimate(
        component="Score Submission",
        input_tokens=100,
        output_tokens=50,
        description="Submit final score with tool call"
    )
]

# ============================================================================
# COST CALCULATION FUNCTIONS
# ============================================================================

def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: ModelPricing,
    use_cache: bool = False,
    cache_hits: int = 0
) -> Dict[str, float]:
    """
    Calculate cost for token usage.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model pricing info
        use_cache: Whether prompt caching is used
        cache_hits: Number of cache hits (for cached portions)

    Returns:
        Dict with cost breakdown
    """
    # Convert tokens to millions
    input_mtok = input_tokens / 1_000_000
    output_mtok = output_tokens / 1_000_000

    if not use_cache:
        # Standard pricing
        input_cost = input_mtok * model.input_per_mtok
        output_cost = output_mtok * model.output_per_mtok
        cache_cost = 0
    else:
        # With prompt caching
        cache_tokens = cache_hits
        cache_mtok = cache_tokens / 1_000_000
        non_cache_mtok = input_mtok - cache_mtok

        # First request writes to cache
        cache_cost = cache_mtok * model.cache_write_per_mtok

        # Subsequent requests read from cache
        input_cost = non_cache_mtok * model.input_per_mtok

        # Output always at standard rate
        output_cost = output_mtok * model.output_per_mtok

    total_cost = input_cost + output_cost + cache_cost

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "cache_cost": cache_cost,
        "total_cost": total_cost,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }

def estimate_researcher_cost(
    num_queries: int,
    model: ModelPricing,
    use_cache: bool = False
) -> Dict[str, float]:
    """
    Estimate cost for running queries through researcher agent.

    Args:
        num_queries: Number of queries to process
        model: Model to use
        use_cache: Whether to use prompt caching

    Returns:
        Cost breakdown
    """
    # Calculate tokens per query
    total_input = sum(e.input_tokens for e in RESEARCHER_ESTIMATES)
    total_output = sum(e.output_tokens for e in RESEARCHER_ESTIMATES)

    # Identify cacheable tokens (system prompt)
    cacheable_tokens = RESEARCHER_ESTIMATES[0].input_tokens  # System prompt: 7267 tokens

    if use_cache and model.supports_prompt_caching:
        # First query: pay to write cache
        first_query_cost = calculate_cost(
            total_input,
            total_output,
            model,
            use_cache=False  # First one writes, doesn't read
        )

        # Add cache write cost
        cache_write_cost = (cacheable_tokens / 1_000_000) * model.cache_write_per_mtok
        first_query_cost["cache_cost"] = cache_write_cost
        first_query_cost["total_cost"] += cache_write_cost

        # Subsequent queries: read from cache
        non_cached_input = total_input - cacheable_tokens
        subsequent_cost = calculate_cost(
            non_cached_input,
            total_output,
            model,
            use_cache=False
        )

        # Add cache read cost
        cache_read_cost = (cacheable_tokens / 1_000_000) * model.cache_read_per_mtok
        subsequent_cost["cache_cost"] = cache_read_cost
        subsequent_cost["total_cost"] += cache_read_cost

        # Total cost
        total = first_query_cost["total_cost"] + (subsequent_cost["total_cost"] * (num_queries - 1))
        avg_per_query = total / num_queries

        # Savings from caching
        no_cache_total = calculate_cost(total_input, total_output, model)["total_cost"] * num_queries
        savings = no_cache_total - total
        savings_pct = (savings / no_cache_total) * 100

        return {
            "total_cost": total,
            "cost_per_query": avg_per_query,
            "first_query_cost": first_query_cost["total_cost"],
            "subsequent_query_cost": subsequent_cost["total_cost"],
            "total_input_tokens": total_input * num_queries,
            "total_output_tokens": total_output * num_queries,
            "cache_savings": savings,
            "cache_savings_pct": savings_pct
        }
    else:
        # No caching
        cost_per_query = calculate_cost(total_input, total_output, model)["total_cost"]
        total = cost_per_query * num_queries

        return {
            "total_cost": total,
            "cost_per_query": cost_per_query,
            "total_input_tokens": total_input * num_queries,
            "total_output_tokens": total_output * num_queries,
            "cache_savings": 0,
            "cache_savings_pct": 0
        }

def estimate_judge_cost(
    num_evaluations: int,
    model: ModelPricing,
    use_cache: bool = False
) -> Dict[str, float]:
    """
    Estimate cost for judge evaluations.

    Args:
        num_evaluations: Number of judge evaluations (queries × judges)
        model: Model to use
        use_cache: Whether to use prompt caching

    Returns:
        Cost breakdown
    """
    # Calculate tokens per evaluation
    total_input = sum(e.input_tokens for e in JUDGE_ESTIMATES)
    total_output = sum(e.output_tokens for e in JUDGE_ESTIMATES)

    # Cacheable: judge prompt + original query (static per query)
    cacheable_tokens = JUDGE_ESTIMATES[0].input_tokens + JUDGE_ESTIMATES[1].input_tokens  # ~950 tokens

    if use_cache and model.supports_prompt_caching:
        # Simplified: assume cache hits for all but first evaluation per query
        # (7 judges × 32 queries = 224 evaluations, 32 cache writes, 192 cache reads)
        num_queries = 32
        judges_per_query = 7

        # First judge per query: write cache
        first_eval_cost = calculate_cost(
            total_input,
            total_output,
            model
        )
        cache_write_cost = (cacheable_tokens / 1_000_000) * model.cache_write_per_mtok
        first_eval_total = first_eval_cost["total_cost"] + cache_write_cost

        # Subsequent judges per query: read cache
        non_cached_input = total_input - cacheable_tokens
        subsequent_cost = calculate_cost(
            non_cached_input,
            total_output,
            model
        )
        cache_read_cost = (cacheable_tokens / 1_000_000) * model.cache_read_per_mtok
        subsequent_total = subsequent_cost["total_cost"] + cache_read_cost

        # Total
        total = (first_eval_total * num_queries) + (subsequent_total * (num_evaluations - num_queries))
        avg_per_eval = total / num_evaluations

        # Savings
        no_cache_total = calculate_cost(total_input, total_output, model)["total_cost"] * num_evaluations
        savings = no_cache_total - total
        savings_pct = (savings / no_cache_total) * 100

        return {
            "total_cost": total,
            "cost_per_evaluation": avg_per_eval,
            "total_input_tokens": total_input * num_evaluations,
            "total_output_tokens": total_output * num_evaluations,
            "cache_savings": savings,
            "cache_savings_pct": savings_pct
        }
    else:
        # No caching
        cost_per_eval = calculate_cost(total_input, total_output, model)["total_cost"]
        total = cost_per_eval * num_evaluations

        return {
            "total_cost": total,
            "cost_per_evaluation": cost_per_eval,
            "total_input_tokens": total_input * num_evaluations,
            "total_output_tokens": total_output * num_evaluations,
            "cache_savings": 0,
            "cache_savings_pct": 0
        }

# ============================================================================
# OPTIMIZATION STRATEGIES
# ============================================================================

@dataclass
class OptimizationStrategy:
    """Cost optimization strategy"""
    name: str
    description: str
    estimated_savings_pct: float
    implementation_effort: str  # "Low", "Medium", "High"
    affects_quality: bool
    quality_impact: str

OPTIMIZATION_STRATEGIES = [
    OptimizationStrategy(
        name="Prompt Caching (Researcher)",
        description="Cache the 7,267 token benchmark prompt across all 32 queries",
        estimated_savings_pct=40.0,
        implementation_effort="Low",
        affects_quality=False,
        quality_impact="None - identical behavior, just cached"
    ),
    OptimizationStrategy(
        name="Prompt Caching (Judges)",
        description="Cache judge prompts + queries across evaluations",
        estimated_savings_pct=15.0,
        implementation_effort="Low",
        affects_quality=False,
        quality_impact="None - identical behavior, just cached"
    ),
    OptimizationStrategy(
        name="Use Haiku for All Agents",
        description="Use Haiku 3.5 instead of Sonnet for both researcher and judges",
        estimated_savings_pct=90.0,
        implementation_effort="Low",
        affects_quality=True,
        quality_impact="Minimal - Haiku 3.5 is very capable for structured tasks"
    ),
    OptimizationStrategy(
        name="Batch API (if available)",
        description="Use Anthropic Batch API for 50% discount on async workloads",
        estimated_savings_pct=50.0,
        implementation_effort="Medium",
        affects_quality=False,
        quality_impact="None - just slower (24h latency)"
    ),
    OptimizationStrategy(
        name="Sample-Based Testing",
        description="Test on 10 queries first, then scale to 32 if results look good",
        estimated_savings_pct=68.75,  # (32-10)/32
        implementation_effort="Low",
        affects_quality=True,
        quality_impact="Reduced statistical power, but sufficient for initial insights"
    ),
    OptimizationStrategy(
        name="Optimize Benchmark Prompt",
        description="The whole point! Reduce 7,267 tokens to <5,000 tokens",
        estimated_savings_pct=31.0,  # ~(7267-5000)/7267 for researcher input
        implementation_effort="High",
        affects_quality=False,
        quality_impact="Goal is to maintain quality while reducing tokens"
    ),
    OptimizationStrategy(
        name="Parallel Judge Execution",
        description="Run 7 judges in parallel instead of sequentially",
        estimated_savings_pct=0,  # No cost savings, just time savings
        implementation_effort="Low",
        affects_quality=False,
        quality_impact="None - just faster"
    ),
    OptimizationStrategy(
        name="LangSmith Monitoring",
        description="Use LangSmith to track actual vs estimated token usage",
        estimated_savings_pct=5.0,  # Helps identify waste
        implementation_effort="Low",
        affects_quality=False,
        quality_impact="None - just visibility"
    )
]

# ============================================================================
# MAIN ESTIMATION
# ============================================================================

def main():
    """Run cost estimation analysis"""
    print("=" * 80)
    print("PHASE 6: BENCHMARK EVALUATION COST ESTIMATION")
    print("=" * 80)
    print()

    # Configuration
    NUM_QUERIES = 32
    NUM_JUDGES = 7
    NUM_EVALUATIONS = NUM_QUERIES * NUM_JUDGES  # 224

    print("Configuration:")
    print(f"  - Test Queries: {NUM_QUERIES}")
    print(f"  - Judge Agents: {NUM_JUDGES}")
    print(f"  - Total Evaluations: {NUM_EVALUATIONS}")
    print()

    # ========================================================================
    # SCENARIO 1: Haiku without caching (baseline)
    # ========================================================================
    print("=" * 80)
    print("SCENARIO 1: Haiku 3.5 WITHOUT Prompt Caching (Baseline)")
    print("=" * 80)
    print()

    haiku = MODELS["haiku-3.5"]

    researcher_baseline = estimate_researcher_cost(NUM_QUERIES, haiku, use_cache=False)
    judge_baseline = estimate_judge_cost(NUM_EVALUATIONS, haiku, use_cache=False)

    total_baseline = researcher_baseline["total_cost"] + judge_baseline["total_cost"]

    print(f"Researcher Agent ({NUM_QUERIES} queries):")
    print(f"  Input tokens:  {researcher_baseline['total_input_tokens']:,}")
    print(f"  Output tokens: {researcher_baseline['total_output_tokens']:,}")
    print(f"  Cost per query: ${researcher_baseline['cost_per_query']:.4f}")
    print(f"  Total cost: ${researcher_baseline['total_cost']:.2f}")
    print()

    print(f"Judge Agents ({NUM_EVALUATIONS} evaluations):")
    print(f"  Input tokens:  {judge_baseline['total_input_tokens']:,}")
    print(f"  Output tokens: {judge_baseline['total_output_tokens']:,}")
    print(f"  Cost per evaluation: ${judge_baseline['cost_per_evaluation']:.4f}")
    print(f"  Total cost: ${judge_baseline['total_cost']:.2f}")
    print()

    print(f"TOTAL COST: ${total_baseline:.2f}")
    print()

    # ========================================================================
    # SCENARIO 2: Haiku WITH prompt caching
    # ========================================================================
    print("=" * 80)
    print("SCENARIO 2: Haiku 3.5 WITH Prompt Caching (Recommended)")
    print("=" * 80)
    print()

    researcher_cached = estimate_researcher_cost(NUM_QUERIES, haiku, use_cache=True)
    judge_cached = estimate_judge_cost(NUM_EVALUATIONS, haiku, use_cache=True)

    total_cached = researcher_cached["total_cost"] + judge_cached["total_cost"]
    total_savings = total_baseline - total_cached
    savings_pct = (total_savings / total_baseline) * 100

    print(f"Researcher Agent ({NUM_QUERIES} queries with caching):")
    print(f"  First query cost: ${researcher_cached['first_query_cost']:.4f}")
    print(f"  Subsequent cost: ${researcher_cached['subsequent_query_cost']:.4f}")
    print(f"  Total cost: ${researcher_cached['total_cost']:.2f}")
    print(f"  Cache savings: ${researcher_cached['cache_savings']:.2f} ({researcher_cached['cache_savings_pct']:.1f}%)")
    print()

    print(f"Judge Agents ({NUM_EVALUATIONS} evaluations with caching):")
    print(f"  Total cost: ${judge_cached['total_cost']:.2f}")
    print(f"  Cache savings: ${judge_cached['cache_savings']:.2f} ({judge_cached['cache_savings_pct']:.1f}%)")
    print()

    print(f"TOTAL COST: ${total_cached:.2f}")
    print(f"TOTAL SAVINGS vs Baseline: ${total_savings:.2f} ({savings_pct:.1f}%)")
    print()

    # ========================================================================
    # SCENARIO 3: Sonnet with caching (for comparison)
    # ========================================================================
    print("=" * 80)
    print("SCENARIO 3: Sonnet 3.5 WITH Caching (Higher Quality, Higher Cost)")
    print("=" * 80)
    print()

    sonnet = MODELS["sonnet-3.5"]

    researcher_sonnet = estimate_researcher_cost(NUM_QUERIES, sonnet, use_cache=True)
    judge_sonnet = estimate_judge_cost(NUM_EVALUATIONS, sonnet, use_cache=True)

    total_sonnet = researcher_sonnet["total_cost"] + judge_sonnet["total_cost"]

    print(f"Researcher Agent: ${researcher_sonnet['total_cost']:.2f}")
    print(f"Judge Agents: ${judge_sonnet['total_cost']:.2f}")
    print(f"TOTAL COST: ${total_sonnet:.2f}")
    print(f"Cost increase vs Haiku+Cache: ${total_sonnet - total_cached:.2f} ({((total_sonnet/total_cached)-1)*100:.0f}% more expensive)")
    print()

    # ========================================================================
    # SCENARIO 4: Haiku 4.5 with caching (User Requested Comparison)
    # ========================================================================
    print("=" * 80)
    print("SCENARIO 4: Haiku 4.5 WITH Caching (Latest Model)")
    print("=" * 80)
    print()

    haiku_45 = MODELS["haiku-4.5"]

    researcher_haiku45 = estimate_researcher_cost(NUM_QUERIES, haiku_45, use_cache=True)
    judge_haiku45 = estimate_judge_cost(NUM_EVALUATIONS, haiku_45, use_cache=True)

    total_haiku45 = researcher_haiku45["total_cost"] + judge_haiku45["total_cost"]

    print(f"Researcher Agent ({NUM_QUERIES} queries with caching):")
    print(f"  First query cost: ${researcher_haiku45['first_query_cost']:.4f}")
    print(f"  Subsequent cost: ${researcher_haiku45['subsequent_query_cost']:.4f}")
    print(f"  Total cost: ${researcher_haiku45['total_cost']:.2f}")
    print(f"  Cache savings: ${researcher_haiku45['cache_savings']:.2f} ({researcher_haiku45['cache_savings_pct']:.1f}%)")
    print()

    print(f"Judge Agents ({NUM_EVALUATIONS} evaluations with caching):")
    print(f"  Total cost: ${judge_haiku45['total_cost']:.2f}")
    print(f"  Cache savings: ${judge_haiku45['cache_savings']:.2f} ({judge_haiku45['cache_savings_pct']:.1f}%)")
    print()

    print(f"TOTAL COST: ${total_haiku45:.2f}")
    print(f"Cost vs Haiku 3.5+Cache: ${total_haiku45 - total_cached:.2f} ({((total_haiku45/total_cached)-1)*100:.0f}% more expensive)")
    print(f"Cost vs Sonnet 3.5+Cache: ${total_haiku45 - total_sonnet:.2f} ({((total_haiku45/total_sonnet)-1)*100:.0f}% {'cheaper' if total_haiku45 < total_sonnet else 'more expensive'})")
    print()
    print("Performance Difference:")
    print("  - Haiku 4.5 offers Sonnet 4-level coding performance")
    print("  - 1/3 the cost of Sonnet 3.5")
    print("  - 2× the speed of Sonnet")
    print("  - 4× more expensive than Haiku 3.5")
    print()

    # ========================================================================
    # OPTIMIZATION STRATEGIES
    # ========================================================================
    print("=" * 80)
    print("COST OPTIMIZATION STRATEGIES")
    print("=" * 80)
    print()

    for i, strategy in enumerate(OPTIMIZATION_STRATEGIES, 1):
        print(f"{i}. {strategy.name}")
        print(f"   {strategy.description}")
        print(f"   Estimated Savings: {strategy.estimated_savings_pct:.1f}%")
        print(f"   Implementation: {strategy.implementation_effort} effort")
        print(f"   Quality Impact: {strategy.quality_impact}")

        # Estimate actual savings
        if strategy.affects_quality:
            print(f"   ⚠️  May affect test results")
        else:
            estimated_new_cost = total_cached * (1 - strategy.estimated_savings_pct / 100)
            estimated_savings = total_cached - estimated_new_cost
            print(f"   💰 Estimated cost after: ${estimated_new_cost:.2f} (save ${estimated_savings:.2f})")
        print()

    # ========================================================================
    # RECOMMENDED CONFIGURATION
    # ========================================================================
    print("=" * 80)
    print("RECOMMENDED CONFIGURATION")
    print("=" * 80)
    print()

    print("For Phase 6 Benchmark Evaluation:")
    print()
    print("✅ Model: Claude 3.5 Haiku")
    print("   - Cost-effective for structured tasks")
    print("   - Excellent performance on research and evaluation")
    print()
    print("✅ Prompt Caching: ENABLED")
    print("   - Cache researcher system prompt (7,267 tokens)")
    print("   - Cache judge prompts across evaluations")
    print("   - Saves ~50% on costs")
    print()
    print("✅ Parallel Execution: ENABLED")
    print("   - Run 7 judges in parallel per query")
    print("   - Reduces wall-clock time significantly")
    print()
    print("✅ LangSmith Monitoring: ENABLED")
    print("   - Track actual token usage")
    print("   - Compare against estimates")
    print("   - Identify optimization opportunities")
    print()

    print(f"Estimated Total Cost: ${total_cached:.2f}")
    print(f"Estimated Time: ~45-90 minutes (with parallel judges)")
    print()

    # ========================================================================
    # IMPLEMENTATION CODE SNIPPET
    # ========================================================================
    print("=" * 80)
    print("IMPLEMENTATION: Enable Prompt Caching in LangChain")
    print("=" * 80)
    print()

    print("""
# Enable prompt caching in ChatAnthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

# For researcher agent
researcher_model = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    temperature=0.7,
    # Enable caching for system prompts
    cache_control={"type": "ephemeral"}  # Cache system messages
)

# System prompt will be cached automatically
system_prompt = get_benchmark_prompt(current_date)  # 7,267 tokens
messages = [
    SystemMessage(content=system_prompt),  # This gets cached
    HumanMessage(content=query)
]

# Subsequent calls with same system prompt use cache
# First call: pays cache write cost ($0.30/MTok)
# Next 31 calls: pays cache read cost ($0.025/MTok) - 90% savings!

# For judge agents (same pattern)
judge_model = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    temperature=0.0,  # Deterministic for judges
    cache_control={"type": "ephemeral"}
)
""")

    # ========================================================================
    # SAVE ESTIMATES TO FILE
    # ========================================================================
    results = {
        "configuration": {
            "num_queries": NUM_QUERIES,
            "num_judges": NUM_JUDGES,
            "num_evaluations": NUM_EVALUATIONS
        },
        "scenarios": {
            "haiku_baseline": {
                "name": "Haiku 3.5 without caching",
                "researcher_cost": researcher_baseline["total_cost"],
                "judge_cost": judge_baseline["total_cost"],
                "total_cost": total_baseline
            },
            "haiku_cached": {
                "name": "Haiku 3.5 with caching (RECOMMENDED)",
                "researcher_cost": researcher_cached["total_cost"],
                "judge_cost": judge_cached["total_cost"],
                "total_cost": total_cached,
                "savings_vs_baseline": total_savings,
                "savings_pct": savings_pct
            },
            "sonnet_cached": {
                "name": "Sonnet 3.5 with caching",
                "researcher_cost": researcher_sonnet["total_cost"],
                "judge_cost": judge_sonnet["total_cost"],
                "total_cost": total_sonnet
            }
        },
        "optimization_strategies": [
            {
                "name": s.name,
                "savings_pct": s.estimated_savings_pct,
                "effort": s.implementation_effort,
                "affects_quality": s.affects_quality
            }
            for s in OPTIMIZATION_STRATEGIES
        ]
    }

    with open("phase_6_cost_estimate.json", "w") as f:
        json.dump(results, f, indent=2)

    print()
    print("=" * 80)
    print(f"✅ Cost estimates saved to: phase_6_cost_estimate.json")
    print("=" * 80)
    print()

if __name__ == "__main__":
    main()
