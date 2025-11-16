"""
Challenger Researcher/Fact-Finding Agent System Prompt - v1 (TEMPLATE)

VERSION: 1.0 (Challenger - To Be Optimized)
DATE CREATED: 2025-11-13
OPTIMIZATION STATUS: ❌ NOT OPTIMIZED - This is a template placeholder

OPTIMIZATION GOALS:
  - Target: Reduce token count while maintaining or improving performance
  - Baseline comparison: 7,267 tokens (Enhanced V3)
  - Target: <15,000 tokens (acceptable range)
  - Acceptable range: 7,000-15,000 tokens

EVALUATION METRICS (vs Benchmark):
  - Planning Quality: Maintain or improve binary (Good/Poor) rating
  - Execution Completeness: Maintain or improve 1-5 scale rating
  - Source Quality: Maintain or improve 1-5 scale rating
  - Citation Accuracy: Maintain or improve binary rating
  - Answer Completeness: Maintain or improve 1-5 scale rating
  - Factual Accuracy: Maintain or improve binary rating
  - Autonomy Score: Maintain or improve binary rating

PROMPT ENGINEERING STRATEGY:
  This challenger prompt should explore one or more of these optimization techniques:

  1. **Structural Compression**
     - Remove redundant sections
     - Consolidate overlapping instructions
     - Use bullet points instead of prose where appropriate

  2. **Directive Consolidation**
     - Merge related rules into single directives
     - Remove duplicated reminders
     - Streamline decision trees

  3. **Example Pruning**
     - Keep only the most illustrative examples
     - Remove verbose explanations
     - Use shorter code snippets

  4. **Primacy-Recency Optimization**
     - Keep critical directives at start and end
     - Move less critical content to middle
     - Maintain key reminders in both positions

  5. **Citation Format Simplification**
     - Streamline citation requirements
     - Simplify format specification
     - Remove redundant attribution rules

INSTRUCTIONS FOR OPTIMIZATION:
  When creating this challenger prompt, copy the benchmark prompt structure
  but apply the optimization techniques above. The goal is to maintain behavioral
  fidelity (same agent performance) while reducing token count.

  Statistical significance testing (N=32 queries × 7 judges = 224 evaluations)
  will determine if the optimization maintains quality while improving efficiency.
"""

import anthropic
import os
from typing import Tuple, Dict, Any

# ==============================================================================
# PROMPT CONTENT (PLACEHOLDER - TO BE OPTIMIZED)
# ==============================================================================

RESEARCHER_SYSTEM_PROMPT = """[PLACEHOLDER]

This is a template for the first challenger prompt.

When optimizing, you should:
1. Copy the benchmark prompt from benchmark_researcher_prompt.py
2. Apply optimization techniques to reduce token count
3. Maintain all critical functionality:
   - Autonomous execution
   - Planning decision tree
   - Task completion verification
   - Sequential execution pattern
   - Extensive citation protocol
   - Progress tracking
4. Test against benchmark using the evaluation framework

TARGET: Achieve <7,267 tokens while maintaining performance metrics.

After optimization, this placeholder will be replaced with the optimized prompt.
"""


# ==============================================================================
# TOKEN COUNTING FUNCTIONS (Reused from Benchmark)
# ==============================================================================

def count_prompt_tokens(
    prompt: str,
    model: str = "claude-sonnet-4-5-20250929"
) -> int:
    """
    Count tokens in the system prompt using Anthropic SDK.

    Args:
        prompt: The system prompt text to count tokens for
        model: The Claude model to use for token counting
               Default: claude-sonnet-4-5-20250929 (Sonnet 4.5)

    Returns:
        Number of tokens in the prompt

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set

    Example:
        >>> count = count_prompt_tokens(RESEARCHER_SYSTEM_PROMPT.format(current_date="2025-11-13"))
        >>> print(f"Token count: {count}")
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Required for token counting."
        )

    client = anthropic.Anthropic(api_key=api_key)

    # Token counting uses the beta messages count_tokens API
    response = client.beta.messages.count_tokens(
        model=model,
        system=prompt,
        messages=[{"role": "user", "content": "test"}]
    )

    return response.input_tokens


def validate_token_limit(
    prompt: str,
    max_tokens: int = 15000,
    model: str = "claude-sonnet-4-5-20250929"
) -> Tuple[bool, int, str]:
    """
    Validate that prompt is under the token limit.

    Args:
        prompt: The system prompt text to validate
        max_tokens: Maximum allowed tokens (default: 15000)
        model: The Claude model to use for token counting

    Returns:
        Tuple of (is_valid, actual_count, message)
        - is_valid: True if under limit, False otherwise
        - actual_count: Actual token count
        - message: Human-readable status message

    Example:
        >>> is_valid, count, msg = validate_token_limit(
        ...     RESEARCHER_SYSTEM_PROMPT.format(current_date="2025-11-13")
        ... )
        >>> print(f"{msg} ({count} tokens)")
    """
    count = count_prompt_tokens(prompt, model)
    is_valid = count <= max_tokens

    # Calculate vs benchmark
    benchmark_tokens = 7267
    reduction = benchmark_tokens - count
    reduction_pct = (reduction / benchmark_tokens) * 100 if benchmark_tokens > 0 else 0

    if is_valid:
        remaining = max_tokens - count
        percentage = (count / max_tokens) * 100
        message = (
            f"✅ VALID - Under token limit "
            f"({count}/{max_tokens} tokens, {percentage:.1f}% used, "
            f"{remaining} tokens remaining)\n"
            f"   vs Benchmark: {reduction:+d} tokens ({reduction_pct:+.1f}%)"
        )
    else:
        excess = count - max_tokens
        percentage = (count / max_tokens) * 100
        message = (
            f"❌ INVALID - Exceeds token limit "
            f"({count}/{max_tokens} tokens, {percentage:.1f}% used, "
            f"{excess} tokens over limit)\n"
            f"   vs Benchmark: {reduction:+d} tokens ({reduction_pct:+.1f}%)"
        )

    return is_valid, count, message


def get_prompt_metadata() -> Dict[str, Any]:
    """
    Get metadata about this challenger prompt version.

    Returns:
        Dictionary with version info, token count, optimization status, etc.

    Example:
        >>> metadata = get_prompt_metadata()
        >>> print(f"Version: {metadata['version']}")
        >>> print(f"Token count: {metadata['token_count']}")
        >>> print(f"Optimization status: {metadata['optimization_status']}")
    """
    from datetime import datetime

    current_date = datetime.now().strftime("%Y-%m-%d")
    formatted_prompt = RESEARCHER_SYSTEM_PROMPT.format(current_date=current_date)

    is_valid, token_count, validation_message = validate_token_limit(formatted_prompt)

    # Calculate comparison with benchmark
    benchmark_tokens = 7267
    token_reduction = benchmark_tokens - token_count
    reduction_percentage = (token_reduction / benchmark_tokens) * 100 if benchmark_tokens > 0 else 0

    return {
        "version": "1.0",
        "name": "Challenger v1 (Template - Not Optimized)",
        "date_created": "2025-11-13",
        "model": "claude-sonnet-4-5-20250929",
        "token_count": token_count,
        "token_limit": 15000,
        "is_valid": is_valid,
        "validation_message": validation_message,
        "optimization_status": "NOT_OPTIMIZED",
        "benchmark_comparison": {
            "benchmark_tokens": benchmark_tokens,
            "challenger_tokens": token_count,
            "token_reduction": token_reduction,
            "reduction_percentage": reduction_percentage,
            "target_tokens": 15000,
            "stretch_goal_met": token_count < 15000
        },
        "optimization_goals": [
            "Reduce token count while maintaining performance",
            "Target: <15,000 tokens (acceptable range)",
            "Target: <15,000 tokens (acceptable range)",
            "Maintain all 7 evaluation metrics"
        ],
        "evaluation_pending": True,
        "ready_for_testing": False
    }


def get_researcher_prompt(current_date: str) -> str:
    """
    Get researcher/fact-finding prompt with current date injected.

    Args:
        current_date: Current date in YYYY-MM-DD format

    Returns:
        Complete researcher system prompt with date context

    Example:
        >>> from datetime import datetime
        >>> current_date = datetime.now().strftime("%Y-%m-%d")
        >>> prompt = get_researcher_prompt(current_date)
    """
    return RESEARCHER_SYSTEM_PROMPT.format(current_date=current_date)


# ==============================================================================
# DISPLAY TOKEN COUNT (Run on import)
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("CHALLENGER RESEARCHER PROMPT v1 - TOKEN COUNT ANALYSIS")
    print("=" * 80)
    print()

    metadata = get_prompt_metadata()

    print(f"Version: {metadata['version']}")
    print(f"Name: {metadata['name']}")
    print(f"Date Created: {metadata['date_created']}")
    print(f"Model: {metadata['model']}")
    print(f"Optimization Status: ⚠️  {metadata['optimization_status']}")
    print()

    print("TOKEN COUNT ANALYSIS:")
    print(metadata['validation_message'])
    print()

    print("BENCHMARK COMPARISON:")
    comp = metadata['benchmark_comparison']
    print(f"  Benchmark (Enhanced V3): {comp['benchmark_tokens']:,} tokens")
    print(f"  Challenger v1: {comp['challenger_tokens']:,} tokens")
    print(f"  Reduction: {comp['token_reduction']:+,} tokens ({comp['reduction_percentage']:+.1f}%)")
    print(f"  Target: <{comp['target_tokens']:,} tokens")
    print(f"  Stretch Goal (<15,000): {'✅ MET' if comp['stretch_goal_met'] else '❌ NOT MET'}")
    print()

    print("OPTIMIZATION GOALS:")
    for goal in metadata['optimization_goals']:
        print(f"  • {goal}")
    print()

    print("STATUS:")
    if metadata['ready_for_testing']:
        print("  ✅ Ready for evaluation against benchmark")
    else:
        print("  ⚠️  NOT READY - Placeholder template only")
        print("  📝 Action Required: Replace placeholder with optimized prompt")
    print()

    print("=" * 80)
