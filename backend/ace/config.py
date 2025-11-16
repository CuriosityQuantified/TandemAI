"""
ACE Configuration

Defines ACEConfig and per-agent configurations for all 6 agents:
- supervisor
- researcher
- data_scientist
- expert_analyst
- writer
- reviewer
"""

from typing import Dict, Literal
from pydantic import BaseModel, Field


class ACEConfig(BaseModel):
    """
    Configuration for ACE middleware on a single agent.

    Controls all aspects of ACE behavior including feature flags,
    playbook settings, reflection parameters, and token budgets.

    Attributes:
        enabled: Master switch for ACE functionality
        reflection_mode: How reflection operates
            - "automatic": Reflect after every execution (production)
            - "observe": Reflect but don't update playbook (validation)
            - "disabled": No reflection (ACE off)

        playbook_id: Unique identifier for this agent's playbook
        max_playbook_entries: Maximum number of entries in playbook
        prune_threshold: Semantic similarity threshold for de-duplication (0-1)
        semantic_similarity_threshold: Cosine similarity for merging entries (0-1)

        max_reflection_iterations: How many rounds of reflection refinement
        reflector_model: LLM model for reflection (recommend Haiku for cost)
        reflector_temperature: Temperature for reflection LLM

        max_playbook_entries_in_prompt: How many entries to inject into prompt

        prune_every_n_executions: Trigger pruning every N executions

        max_tokens_per_execution: Token budget limit
    """

    # Feature flags
    enabled: bool = Field(
        default=False,
        description="Master switch for ACE (disabled by default for safe rollout)"
    )
    reflection_mode: Literal["automatic", "observe", "disabled"] = Field(
        default="automatic",
        description="Reflection behavior: automatic (update playbook), observe (read-only), disabled (no reflection)"
    )

    # Playbook settings
    playbook_id: str = Field(
        ...,
        description="Unique identifier for playbook (e.g., 'researcher_v1')"
    )
    max_playbook_entries: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Maximum playbook size before pruning"
    )
    prune_threshold: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for de-duplication during pruning"
    )
    semantic_similarity_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Threshold for merging similar insights"
    )

    # Reflection settings
    max_reflection_iterations: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum refinement rounds for insights"
    )
    reflector_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description="LLM model for reflection (Haiku 4.5 for enhanced reasoning)"
    )
    reflector_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Temperature for reflection LLM (lower = more focused)"
    )

    # Generator settings (playbook injection)
    max_playbook_entries_in_prompt: int = Field(
        default=10,
        ge=1,
        le=50,
        description="How many playbook entries to inject into system prompt"
    )

    # Curator settings
    prune_every_n_executions: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Trigger pruning every N executions"
    )

    # Token budget
    max_tokens_per_execution: int = Field(
        default=8000,
        ge=1000,
        le=100000,
        description="Token budget limit per execution (including reflection)"
    )


# ============================================================================
# Per-Agent Configurations
# ============================================================================

ACE_CONFIGS: Dict[str, ACEConfig] = {
    # Supervisor Agent
    # Orchestrates team, delegates tasks, coordinates outputs
    # Needs larger playbook to learn delegation patterns
    "supervisor": ACEConfig(
        enabled=True,  # ✅ RE-ENABLED - fixed SystemMessage check
        playbook_id="supervisor_v1",
        max_playbook_entries=200,  # Most complex, needs more knowledge
        max_playbook_entries_in_prompt=15,  # Show more strategies
        reflection_mode="automatic",
    ),

    # Researcher Agent (Fact-Finding)
    # Highest accuracy priority, extensive citation requirements
    # Needs large playbook to learn source tracking patterns
    "researcher": ACEConfig(
        enabled=False,  # Start disabled, enable in Phase 3 (first to enable)
        playbook_id="researcher_v1",
        max_playbook_entries=150,  # High knowledge accumulation for fact-finding
        max_playbook_entries_in_prompt=12,  # Show citation patterns
        prune_threshold=0.90,  # Keep more diverse insights for research
        reflection_mode="automatic",
    ),

    # Data Scientist Agent
    # Hypothesis testing, statistical analysis
    # Standard configuration
    "data_scientist": ACEConfig(
        enabled=False,  # Start disabled, enable in Phase 5 (day 5)
        playbook_id="data_scientist_v1",
        max_playbook_entries=100,  # Standard
        max_playbook_entries_in_prompt=10,
        reflection_mode="automatic",
    ),

    # Expert Analyst Agent
    # Deep insights, synthesis
    # Standard configuration
    "expert_analyst": ACEConfig(
        enabled=False,  # Start disabled, enable in Phase 5 (day 4)
        playbook_id="expert_analyst_v1",
        max_playbook_entries=100,  # Standard
        max_playbook_entries_in_prompt=10,
        reflection_mode="automatic",
    ),

    # Writer Agent
    # Report writing, documentation
    # Fewer but higher quality entries
    "writer": ACEConfig(
        enabled=False,  # Start disabled, enable in Phase 5 (day 2)
        playbook_id="writer_v1",
        max_playbook_entries=80,  # Fewer but higher quality
        max_playbook_entries_in_prompt=8,  # Focus on best writing patterns
        prune_threshold=0.95,  # More aggressive pruning
        reflection_mode="automatic",
    ),

    # Reviewer Agent
    # Quality assurance, gap identification
    # Fewer but higher quality entries
    "reviewer": ACEConfig(
        enabled=False,  # Start disabled, enable in Phase 5 (day 3)
        playbook_id="reviewer_v1",
        max_playbook_entries=80,  # Fewer but higher quality
        max_playbook_entries_in_prompt=8,  # Focus on best review patterns
        prune_threshold=0.95,  # More aggressive pruning
        reflection_mode="automatic",
    ),
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_agent_config(agent_type: str) -> ACEConfig:
    """
    Get ACE configuration for an agent.

    Args:
        agent_type: Agent type (supervisor, researcher, etc.)

    Returns:
        ACEConfig for that agent

    Raises:
        KeyError: If agent type not recognized
    """
    if agent_type not in ACE_CONFIGS:
        raise KeyError(
            f"Unknown agent type: {agent_type}. "
            f"Valid types: {list(ACE_CONFIGS.keys())}"
        )
    return ACE_CONFIGS[agent_type]


def enable_ace_for_agent(agent_type: str, mode: Literal["automatic", "observe"] = "automatic"):
    """
    Enable ACE for a specific agent.

    Args:
        agent_type: Agent to enable
        mode: Reflection mode (automatic or observe)

    Example:
        # Phase 2: Enable observe mode for all agents
        for agent in ACE_CONFIGS:
            enable_ace_for_agent(agent, mode="observe")

        # Phase 3: Enable automatic mode for researcher
        enable_ace_for_agent("researcher", mode="automatic")
    """
    config = get_agent_config(agent_type)
    config.enabled = True
    config.reflection_mode = mode


def disable_ace_for_agent(agent_type: str):
    """
    Disable ACE for a specific agent (rollback).

    Args:
        agent_type: Agent to disable
    """
    config = get_agent_config(agent_type)
    config.enabled = False


def get_enabled_agents() -> list[str]:
    """
    Get list of agents with ACE enabled.

    Returns:
        List of agent types with enabled=True
    """
    return [
        agent_type
        for agent_type, config in ACE_CONFIGS.items()
        if config.enabled
    ]


# ============================================================================
# Rollout Helpers for Phased Deployment
# ============================================================================

def enable_phase_2_observe_mode():
    """
    Phase 2: Enable observe mode for all 6 agents.

    This allows reflection to run but doesn't update playbooks.
    Used for validation before production rollout.
    """
    for agent_type in ACE_CONFIGS:
        enable_ace_for_agent(agent_type, mode="observe")


def enable_phase_3_researcher():
    """
    Phase 3: Enable automatic mode for researcher only.

    First production rollout with A/B testing.
    """
    disable_all_agents()  # Clear any previous config
    enable_ace_for_agent("researcher", mode="automatic")


def enable_phase_5_full_rollout():
    """
    Phase 5: Enable automatic mode for all agents in staggered order.

    Day 1: researcher (already validated)
    Day 2: writer
    Day 3: reviewer
    Day 4: expert_analyst
    Day 5: data_scientist
    Day 6: supervisor (last, highest risk)
    """
    rollout_order = [
        "researcher",      # Day 1 (already enabled from Phase 3)
        "writer",          # Day 2
        "reviewer",        # Day 3
        "expert_analyst",  # Day 4
        "data_scientist",  # Day 5
        "supervisor",      # Day 6 (last)
    ]

    for agent_type in rollout_order:
        enable_ace_for_agent(agent_type, mode="automatic")


def disable_all_agents():
    """
    Emergency rollback: Disable ACE for all agents.

    Use if issues occur during rollout.
    """
    for agent_type in ACE_CONFIGS:
        disable_ace_for_agent(agent_type)
