"""State Schema for Deep Research Workflow

Defines the state structure for the multi-agent research system with
search tracking, context management, and quality metrics.
"""

from typing import Annotated, TypedDict, Literal
from operator import add
from datetime import datetime
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Individual search result"""
    query: str
    content: str
    url: str
    title: str
    score: float | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class Citation(BaseModel):
    """Citation/source reference"""
    url: str
    title: str
    snippet: str
    relevance_score: float


class ActionRecord(BaseModel):
    """Record of an agent action"""
    action_type: Literal["search", "analyze", "write", "critique", "user_interaction"]
    agent_name: str
    input: str
    output: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class QualityMetrics(BaseModel):
    """Quality assessment metrics"""
    completeness: float  # 0-1
    accuracy: float  # 0-1
    relevance: float  # 0-1
    citation_quality: float  # 0-1
    overall_score: float  # 0-1


class ResearchState(TypedDict):
    """State for deep research workflow

    Uses Annotated with operator.add for accumulator fields that append to lists.
    """

    # Core research data
    query: str  # Original research question
    clarified_query: str | None  # Clarified/refined query
    final_report: str | None  # Final research report

    # Search tracking (accumulator - appends to list)
    search_results: Annotated[list[SearchResult], add]
    search_count: int  # Total searches performed

    # Citations tracking (accumulator)
    citations: Annotated[list[Citation], add]

    # Action history (accumulator - keep last 5 + essential)
    action_history: Annotated[list[ActionRecord], add]

    # Context management
    context_summary: str | None  # Compressed context
    essential_findings: list[str]  # Key discoveries to preserve

    # Effort level configuration
    effort_level: str  # quick, standard, thorough, deep, extended_deep, ultrathink_deep
    min_searches_required: int
    max_iterations: int

    # Progress tracking
    iteration: int  # Current iteration number
    phase: Literal["planning", "researching", "analyzing", "writing", "critiquing", "done"]

    # Quality metrics
    quality_metrics: QualityMetrics | None
    quality_threshold_met: bool

    # Loop detection
    query_history: Annotated[list[str], add]  # Track all queries for duplicate detection
    novelty_scores: list[float]  # Track novelty of each search
    stuck_count: int  # Number of times stuck in loop

    # User interaction
    user_feedback: str | None
    approval_required: bool
    hitl_enabled: bool
    planning_approved: bool

    # Knowledge graph state (for thorough+)
    kg_entities_count: int  # Number of entities in KG
    kg_relationships_count: int  # Number of relationships

    # Vector DB state (for standard+)
    vector_docs_count: int  # Number of docs in vector store

    # Metadata
    session_id: str
    started_at: datetime
    updated_at: datetime

    # Next actions
    next_action: str | None  # Recommended next action
    should_continue: bool  # Whether to continue research loop


def create_initial_state(
    query: str,
    effort_level: str,
    session_id: str,
    hitl_enabled: bool = False,
) -> ResearchState:
    """Create initial research state

    Args:
        query: Research question
        effort_level: Effort level (quick/standard/thorough/deep/extended_deep/ultrathink_deep)
        session_id: Unique session identifier
        hitl_enabled: Whether human-in-the-loop is enabled

    Returns:
        Initial ResearchState
    """
    from .effort_config import get_effort_config

    config = get_effort_config(effort_level)
    now = datetime.now()

    return ResearchState(
        # Core data
        query=query,
        clarified_query=None,
        final_report=None,

        # Search tracking
        search_results=[],
        search_count=0,

        # Citations
        citations=[],

        # Actions
        action_history=[],

        # Context
        context_summary=None,
        essential_findings=[],

        # Effort config
        effort_level=effort_level,
        min_searches_required=config.min_searches,
        max_iterations=config.max_iterations,

        # Progress
        iteration=0,
        phase="planning",

        # Quality
        quality_metrics=None,
        quality_threshold_met=False,

        # Loop detection
        query_history=[],
        novelty_scores=[],
        stuck_count=0,

        # User interaction
        user_feedback=None,
        approval_required=False,
        hitl_enabled=hitl_enabled,
        planning_approved=not hitl_enabled,  # Auto-approve if HITL disabled

        # KG state
        kg_entities_count=0,
        kg_relationships_count=0,

        # Vector DB state
        vector_docs_count=0,

        # Metadata
        session_id=session_id,
        started_at=now,
        updated_at=now,

        # Next actions
        next_action=None,
        should_continue=True,
    )


def trim_action_history(state: ResearchState, keep_recent: int = 5) -> ResearchState:
    """Trim action history to keep last N actions + essential context

    Args:
        state: Current state
        keep_recent: Number of recent actions to keep (default 5)

    Returns:
        State with trimmed action history
    """
    if len(state["action_history"]) <= keep_recent:
        return state

    # Keep last N actions
    trimmed_history = state["action_history"][-keep_recent:]

    state["action_history"] = trimmed_history
    state["updated_at"] = datetime.now()

    return state


def update_quality_metrics(
    state: ResearchState,
    completeness: float,
    accuracy: float,
    relevance: float,
    citation_quality: float,
) -> ResearchState:
    """Update quality metrics and check if threshold met

    Args:
        state: Current state
        completeness: Completeness score (0-1)
        accuracy: Accuracy score (0-1)
        relevance: Relevance score (0-1)
        citation_quality: Citation quality score (0-1)

    Returns:
        Updated state with quality metrics
    """
    from .effort_config import get_effort_config

    overall_score = (completeness + accuracy + relevance + citation_quality) / 4

    state["quality_metrics"] = QualityMetrics(
        completeness=completeness,
        accuracy=accuracy,
        relevance=relevance,
        citation_quality=citation_quality,
        overall_score=overall_score,
    )

    config = get_effort_config(state["effort_level"])
    state["quality_threshold_met"] = overall_score >= config.quality_threshold
    state["updated_at"] = datetime.now()

    return state
