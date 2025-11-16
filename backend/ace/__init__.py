"""
ACE (Agentic Context Engineering) Module

This module implements ACE as LangChain middleware for managing evolving context playbooks
across 6 agents: supervisor, researcher, data_scientist, expert_analyst, writer, and reviewer.

Based on Stanford/SambaNova research: arXiv:2510.04618
"Evolving Contexts for Self-Improving Language Models"

Key Components:
- middleware.py: ACEMiddleware class (wraps agent nodes)
- playbook_store.py: PlaybookStore (LangGraph Store wrapper)
- reflector.py: Reflector (insight generation)
- curator.py: Curator (delta updates, de-duplication)
- config.py: ACEConfig (per-agent settings)
- schemas.py: Type definitions

Usage:
    from ace import ACEMiddleware, PlaybookStore, Reflector, Curator
    from ace.config import ACE_CONFIGS

    # Initialize components
    playbook_store = PlaybookStore()
    reflector = Reflector()
    curator = Curator()

    # Create middleware for agent
    ace_middleware = ACEMiddleware(
        agent_type="researcher",
        playbook_store=playbook_store,
        reflector=reflector,
        curator=curator,
        config=ACE_CONFIGS["researcher"]
    )

    # Wrap agent node
    wrapped_node = ace_middleware.wrap_node(original_node)
"""

from .middleware import ACEMiddleware
from .playbook_store import PlaybookStore
from .reflector import Reflector
from .curator import Curator
from .osmosis_extractor import OsmosisExtractor
from .config import ACEConfig, ACE_CONFIGS
from .schemas import (
    PlaybookEntry,
    PlaybookState,
    ReflectionInsight,
    ReflectionInsightList,
    PlaybookDelta,
    PlaybookUpdate,
    create_initial_playbook,
    format_playbook_for_prompt,
)

__all__ = [
    "ACEMiddleware",
    "PlaybookStore",
    "Reflector",
    "Curator",
    "OsmosisExtractor",
    "ACEConfig",
    "ACE_CONFIGS",
    "PlaybookEntry",
    "PlaybookState",
    "ReflectionInsight",
    "ReflectionInsightList",
    "PlaybookDelta",
    "PlaybookUpdate",
    "create_initial_playbook",
    "format_playbook_for_prompt",
]

__version__ = "1.0.0"
