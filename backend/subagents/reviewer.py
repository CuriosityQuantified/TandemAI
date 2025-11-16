"""
Reviewer Subagent - Quality Assurance and Comprehensiveness Checking
====================================================================

Specialized subagent for document review, quality assurance, and completeness verification.

Capabilities:
- Comprehensive document review
- Quality assessment and scoring
- Gap identification
- Clarity and readability improvement
- Consistency checking

Usage:
    reviewer = create_reviewer_subagent(checkpointer, workspace_dir)
    result = await reviewer.ainvoke(
        {"messages": [{"role": "user", "content": "Review document..."}]},
        config={"configurable": {"thread_id": "reviewer-123"}}
    )
"""

from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langchain_anthropic import ChatAnthropic

# Import centralized prompt and date utility
from backend.prompts.reviewer import get_reviewer_prompt
from backend.utils.date_helper import get_current_date


def create_reviewer_subagent(checkpointer, workspace_dir: str):
    """
    Create reviewer subagent specialized in quality assurance.

    The reviewer subagent is a full-featured autonomous agent with:
    - Tavily search for quality standards and best practices
    - Write/edit file capabilities for creating review reports
    - Focus on thoroughness, clarity, and quality

    Args:
        checkpointer: PostgreSQL checkpointer for state persistence
        workspace_dir: Base directory for file operations

    Returns:
        Configured reviewer DeepAgent

    Example:
        reviewer = create_reviewer_subagent(checkpointer, "/workspace")

        config = {"configurable": {"thread_id": "reviewer-abc123"}}

        result = await reviewer.ainvoke({
            "messages": [{
                "role": "user",
                "content": '''Review the renewable energy report for quality and completeness.

                Target document:
                - /workspace/reports/renewable_energy_report.md

                Review criteria:
                - Comprehensiveness: All aspects covered?
                - Clarity: Easy to understand?
                - Accuracy: Facts and data correct?
                - Readability: Well-structured and engaging?
                - Actionability: Clear recommendations?

                Write review to /workspace/reviews/renewable_energy_review.md
                '''
            }]
        }, config)
    """
    # Import tools from parent module
    import sys
    from pathlib import Path
    backend_dir = str(Path(__file__).parent.parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from module_2_2_simple import (
        tavily_search,
        read_file_tool,
        write_file_tool,
        edit_file_with_approval,
        read_current_plan_tool,
    )

    # Use StateBackend only (filesystem operations handled by custom tools)
    def create_backend(runtime=None, state_dir=".state"):
        return StateBackend(runtime)

    # Use Claude Haiku 4.5 for enhanced critical analysis
    model = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0.2  # Balanced for objective evaluation
    )

    # Specialized system prompt for quality review
    # Use centralized system prompt with date injection
    system_prompt = get_reviewer_prompt(get_current_date())


    # Create reviewer agent with specialized tools
    # All filesystem operations use custom workspace-scoped tools
    return create_deep_agent(
        model=model,
        tools=[
            tavily_search,              # Research quality standards
            read_file_tool,             # Read files from /workspace/ directory
            write_file_tool,            # Create review reports (with approval workflow)
            edit_file_with_approval,    # Edit review documents (with approval workflow)
            read_current_plan_tool,     # Check main agent's plan for context
        ],
        backend=create_backend,
        checkpointer=checkpointer,
        system_prompt=system_prompt
    )
