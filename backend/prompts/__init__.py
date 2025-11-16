"""
System Prompts Module

Research-backed system prompts for all 6 agents, synthesized from:
- arXiv papers (2025) on multi-agent systems
- Production GitHub repositories with proven accuracy

Agents:
- supervisor: AgentOrchestra pattern (plan → delegate → coordinate → verify)
- researcher: Fact-finding with extensive citation requirements (HIGHEST ACCURACY PRIORITY)
- data_scientist: Hypothesis-driven with statistical validation
- expert_analyst: Decision → Plan → Execute → Judge
- writer: Multi-stage with revision loops
- reviewer: Explicit criteria with gap identification

Usage:
    from prompts import get_supervisor_prompt, get_researcher_prompt
    from datetime import datetime

    current_date = datetime.now().strftime("%Y-%m-%d")
    researcher_prompt = get_researcher_prompt(current_date)
"""

from .supervisor import get_supervisor_prompt, SUPERVISOR_SYSTEM_PROMPT
from .researcher import get_researcher_prompt, RESEARCHER_SYSTEM_PROMPT
from .data_scientist import get_data_scientist_prompt, DATA_SCIENTIST_SYSTEM_PROMPT
from .expert_analyst import get_expert_analyst_prompt, EXPERT_ANALYST_SYSTEM_PROMPT
from .writer import get_writer_prompt, WRITER_SYSTEM_PROMPT
from .reviewer import get_reviewer_prompt, REVIEWER_SYSTEM_PROMPT

__all__ = [
    # Supervisor
    "get_supervisor_prompt",
    "SUPERVISOR_SYSTEM_PROMPT",
    # Researcher (Fact-Finding)
    "get_researcher_prompt",
    "RESEARCHER_SYSTEM_PROMPT",
    # Data Scientist
    "get_data_scientist_prompt",
    "DATA_SCIENTIST_SYSTEM_PROMPT",
    # Expert Analyst
    "get_expert_analyst_prompt",
    "EXPERT_ANALYST_SYSTEM_PROMPT",
    # Writer
    "get_writer_prompt",
    "WRITER_SYSTEM_PROMPT",
    # Reviewer
    "get_reviewer_prompt",
    "REVIEWER_SYSTEM_PROMPT",
]

__version__ = "1.0.0"
