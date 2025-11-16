"""Effort Level Configuration for Deep Research System

Defines 6-tier effort levels with minimum search counts and configuration parameters.
"""

from enum import Enum
from typing import TypedDict
from dataclasses import dataclass


class EffortLevel(str, Enum):
    """Six-tier effort level system"""
    QUICK = "quick"
    STANDARD = "standard"
    THOROUGH = "thorough"
    DEEP = "deep"
    EXTENDED_DEEP = "extended_deep"
    ULTRATHINK_DEEP = "ultrathink_deep"


@dataclass
class EffortConfig:
    """Configuration for each effort level"""
    name: str
    min_searches: int
    max_iterations: int
    depth: str
    use_knowledge_graph: bool
    use_vector_rag: bool
    enable_advanced_summarization: bool
    max_tokens_per_search: int
    parallel_searches: int
    quality_threshold: float
    enable_loop_detection: bool


# Effort level configurations
EFFORT_CONFIGS = {
    EffortLevel.QUICK: EffortConfig(
        name="quick",
        min_searches=5,
        max_iterations=3,
        depth="basic",
        use_knowledge_graph=False,
        use_vector_rag=False,
        enable_advanced_summarization=False,
        max_tokens_per_search=2000,
        parallel_searches=2,
        quality_threshold=0.6,
        enable_loop_detection=False,
    ),
    EffortLevel.STANDARD: EffortConfig(
        name="standard",
        min_searches=20,
        max_iterations=5,
        depth="standard",
        use_knowledge_graph=False,
        use_vector_rag=True,
        enable_advanced_summarization=False,
        max_tokens_per_search=4000,
        parallel_searches=3,
        quality_threshold=0.7,
        enable_loop_detection=True,
    ),
    EffortLevel.THOROUGH: EffortConfig(
        name="thorough",
        min_searches=50,
        max_iterations=8,
        depth="comprehensive",
        use_knowledge_graph=True,
        use_vector_rag=True,
        enable_advanced_summarization=True,
        max_tokens_per_search=6000,
        parallel_searches=4,
        quality_threshold=0.75,
        enable_loop_detection=True,
    ),
    EffortLevel.DEEP: EffortConfig(
        name="deep",
        min_searches=100,
        max_iterations=12,
        depth="deep",
        use_knowledge_graph=True,
        use_vector_rag=True,
        enable_advanced_summarization=True,
        max_tokens_per_search=8000,
        parallel_searches=5,
        quality_threshold=0.8,
        enable_loop_detection=True,
    ),
    EffortLevel.EXTENDED_DEEP: EffortConfig(
        name="extended_deep",
        min_searches=250,
        max_iterations=20,
        depth="extended",
        use_knowledge_graph=True,
        use_vector_rag=True,
        enable_advanced_summarization=True,
        max_tokens_per_search=10000,
        parallel_searches=6,
        quality_threshold=0.85,
        enable_loop_detection=True,
    ),
    EffortLevel.ULTRATHINK_DEEP: EffortConfig(
        name="ultrathink_deep",
        min_searches=500,
        max_iterations=30,
        depth="definitive",
        use_knowledge_graph=True,
        use_vector_rag=True,
        enable_advanced_summarization=True,
        max_tokens_per_search=12000,
        parallel_searches=8,
        quality_threshold=0.9,
        enable_loop_detection=True,
    ),
}


def get_effort_config(effort_level: str | EffortLevel) -> EffortConfig:
    """Get configuration for the specified effort level

    Args:
        effort_level: Effort level enum or string

    Returns:
        EffortConfig for the specified level

    Raises:
        ValueError: If effort level is invalid
    """
    if isinstance(effort_level, str):
        try:
            effort_level = EffortLevel(effort_level.lower())
        except ValueError:
            raise ValueError(
                f"Invalid effort level: {effort_level}. "
                f"Must be one of: {[e.value for e in EffortLevel]}"
            )

    return EFFORT_CONFIGS[effort_level]


def get_search_requirement(effort_level: str | EffortLevel) -> int:
    """Get minimum search requirement for effort level

    Args:
        effort_level: Effort level enum or string

    Returns:
        Minimum number of searches required
    """
    config = get_effort_config(effort_level)
    return config.min_searches


def should_continue_searching(
    current_count: int,
    effort_level: str | EffortLevel,
    quality_score: float | None = None
) -> bool:
    """Determine if more searches are needed

    Args:
        current_count: Current number of searches completed
        effort_level: Current effort level
        quality_score: Optional quality score (0-1)

    Returns:
        True if more searches needed, False otherwise
    """
    config = get_effort_config(effort_level)

    # Must meet minimum search requirement
    if current_count < config.min_searches:
        return True

    # If quality threshold met, can stop early
    if quality_score is not None and quality_score >= config.quality_threshold:
        return False

    # Continue if under maximum iterations
    return current_count < (config.min_searches * 2)
