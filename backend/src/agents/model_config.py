"""
Centralized model configuration for all ATLAS agents.

PRIMARY MODEL: Claude Sonnet models (3.5, 4, 4.5) - more tolerant of edge cases
FALLBACK MODEL: Groq qwen/qwen3-32b - faster but stricter validation

Recommended Configuration:
- Supervisor Agent: Sonnet 4.5 (best orchestration)
- Research Agent: Sonnet 4.5 (best overall performance)
- Analysis Agent: Sonnet 4 (extended thinking mode)
- Writing Agent: Sonnet 4.5 (best quality)
- Reviewer Agent: Sonnet 4.5 (best code evaluation)

All imports are ABSOLUTE.
"""

import os
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic


def get_claude_sonnet_4_5(temperature: float = 0.7) -> ChatAnthropic:
    """
    Get Claude Sonnet 4.5 (RECOMMENDED - best performance).

    Args:
        temperature: Model temperature (0.0-1.0)
            - 0.3: Precise, factual (reviewer agent)
            - 0.5: Factual, focused (research agent)
            - 0.7: Balanced reasoning (supervisor agent)
            - 0.8: Creative, engaging (writing agent)

    Returns:
        ChatAnthropic instance configured with:
        - Model: claude-sonnet-4-5-20250929 (Sept 2025, latest)
        - Max tokens: 30,000 (can go up to 64,000)
        - Performance: 77.2% SWE-bench Verified (best coding model)
        - Focus: 30+ hours on complex tasks
        - Pricing: $3/MTok input, $15/MTok output

    Example:
        >>> model = get_claude_sonnet_4_5(temperature=0.5)
        >>> response = await model.ainvoke("Research AI trends")
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Please add ANTHROPIC_API_KEY to your .env file."
        )

    return ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        temperature=temperature,
        max_tokens=30000,
        anthropic_api_key=api_key,
    )


def get_claude_sonnet_4(temperature: float = 0.7) -> ChatAnthropic:
    """
    Get Claude Sonnet 4 (for extended thinking mode).

    Args:
        temperature: Model temperature (0.0-1.0)
            - Use None or omit for extended thinking mode
            - 0.3: Precise analysis (if not using thinking mode)

    Returns:
        ChatAnthropic instance configured with:
        - Model: claude-sonnet-4-20250514 (May 2025)
        - Max tokens: 30,000 (can go up to 64,000)
        - Performance: 72.7% SWE-bench Verified
        - Features: Hybrid model with extended thinking mode
        - Pricing: $3/MTok input, $15/MTok output

    Example:
        >>> model = get_claude_sonnet_4(temperature=0.3)
        >>> response = await model.ainvoke("Analyze this complex problem")
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Please add ANTHROPIC_API_KEY to your .env file."
        )

    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=temperature,
        max_tokens=30000,
        anthropic_api_key=api_key,
    )


def get_claude_sonnet_3_5(temperature: float = 0.7) -> ChatAnthropic:
    """
    Get Claude 3.5 Sonnet (legacy compatibility).

    Args:
        temperature: Model temperature (0.0-1.0)

    Returns:
        ChatAnthropic instance configured with:
        - Model: claude-3-5-sonnet-20241022 (Oct 2024)
        - Max tokens: 8,192 (lower than Sonnet 4/4.5)
        - Performance: 49% SWE-bench Verified
        - Pricing: $3/MTok input, $15/MTok output

    Example:
        >>> model = get_claude_sonnet_3_5(temperature=0.7)
        >>> response = await model.ainvoke("General task")
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Please add ANTHROPIC_API_KEY to your .env file."
        )

    return ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=temperature,
        max_tokens=8192,  # Max for 3.5 Sonnet
        anthropic_api_key=api_key,
    )


def get_groq_model(temperature: float = 0.7) -> ChatGroq:
    """
    Get configured Groq model instance.

    Args:
        temperature: Model temperature (0.0-2.0)
            - 0.3: Precise, factual (analysis agent)
            - 0.5: Factual, focused (research agent)
            - 0.7: Balanced reasoning (supervisor agent)
            - 0.8: Creative, engaging (writing agent)

    Returns:
        ChatGroq instance configured with:
        - Model: qwen/qwen3-32b (32B parameters, balanced speed/quality)
        - Max tokens: 20,000
        - Streaming: Enabled
        - Tool calling: Native Groq function calling with parallel tool use
        - Reasoning: Includes reasoning traces for transparency
        - API key: From GROQ_API_KEY environment variable

    Example:
        >>> model = get_groq_model(temperature=0.5)
        >>> response = await model.ainvoke("What is AI?")
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY environment variable not set. "
            "Please add GROQ_API_KEY to your .env file."
        )

    return ChatGroq(
        model="qwen/qwen3-32b",
        temperature=temperature,
        max_tokens=20000,
        streaming=True,
        groq_api_key=api_key,
    )
