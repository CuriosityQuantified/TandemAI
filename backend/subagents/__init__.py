"""
Subagent Module - Deep Subagent Delegation System
================================================

This module provides specialized autonomous subagents for complex research tasks.

Available Subagents:
- researcher: Research with mandatory [1] [2] [3] source citations
- data_scientist: Statistical analysis and data interpretation
- expert_analyst: Structured problem solving and strategic thinking
- writer: Professional writing for reports and documentation
- reviewer: Quality assurance and comprehensiveness checking

Each subagent is a full-featured autonomous agent with:
- Planning capability
- File modification tools (write_file, edit_file with approval)
- Tool access (tavily_search, file operations)
- Autonomous execution
- Hierarchical delegation capability

Usage:
    from subagents import create_researcher_subagent

    researcher = create_researcher_subagent(checkpointer, workspace_dir)
    result = await researcher.ainvoke({"messages": [...]}, config)
"""

from .researcher import create_researcher_subagent
from .data_scientist import create_data_scientist_subagent
from .expert_analyst import create_expert_analyst_subagent
from .writer import create_writer_subagent
from .reviewer import create_reviewer_subagent

__all__ = [
    'create_researcher_subagent',
    'create_data_scientist_subagent',
    'create_expert_analyst_subagent',
    'create_writer_subagent',
    'create_reviewer_subagent',
]
