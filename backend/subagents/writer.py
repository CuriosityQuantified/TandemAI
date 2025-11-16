"""
Writer Subagent - Professional Writing for Reports and Documentation
====================================================================

Specialized subagent for expert writing across various formats and styles.

Capabilities:
- Technical documentation
- Business reports and proposals
- Executive summaries
- Research papers and articles
- Content editing and refinement

Usage:
    writer = create_writer_subagent(checkpointer, workspace_dir)
    result = await writer.ainvoke(
        {"messages": [{"role": "user", "content": "Write report..."}]},
        config={"configurable": {"thread_id": "writer-123"}}
    )
"""

from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langchain_anthropic import ChatAnthropic

# Import centralized prompt and date utility
from backend.prompts.writer import get_writer_prompt
from backend.utils.date_helper import get_current_date


def create_writer_subagent(checkpointer, workspace_dir: str):
    """
    Create writer subagent specialized in professional writing.

    The writer subagent is a full-featured autonomous agent with:
    - Tavily search for research on writing best practices
    - Write/edit file capabilities for creating polished documents
    - Expertise in multiple writing styles and formats

    Args:
        checkpointer: PostgreSQL checkpointer for state persistence
        workspace_dir: Base directory for file operations

    Returns:
        Configured writer DeepAgent

    Example:
        writer = create_writer_subagent(checkpointer, "/workspace")

        config = {"configurable": {"thread_id": "writer-abc123"}}

        result = await writer.ainvoke({
            "messages": [{
                "role": "user",
                "content": '''Create a comprehensive technical report on renewable energy trends.

                Source materials:
                - /workspace/research/findings.md
                - /workspace/analysis/statistical_trends.md

                Requirements:
                - Executive summary for stakeholders
                - Technical details for engineers
                - Clear visualizations descriptions
                - Professional formatting
                - Write to /workspace/reports/renewable_energy_report.md
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
        write_file_tool,
        edit_file_with_approval,
        read_current_plan_tool,
    )

    # Create hybrid backend for filesystem operations
    def create_hybrid_backend(runtime=None, state_dir=".state", workspace_dir=workspace_dir):
        return CompositeBackend(
            default=StateBackend(runtime),  # StateBackend requires runtime parameter
            routes={
                "/workspace/*": FilesystemBackend(root_dir=workspace_dir),  # Use root_dir not base_dir
            }
        )

    # Use Claude Haiku 4.5 for enhanced writing
    model = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0.5  # Balanced for creativity and precision
    )

    # Specialized system prompt for professional writing
    # Use centralized system prompt with date injection
    system_prompt = get_writer_prompt(get_current_date())


    # Create writer agent with specialized tools
    return create_deep_agent(
        model=model,
        tools=[
            tavily_search,              # Research writing best practices
            write_file_tool,            # Create documents (with approval)
            edit_file_with_approval,    # Refine documents (with approval)
            read_current_plan_tool,     # Check main agent's plan for context
        ],
        backend=create_hybrid_backend,
        checkpointer=checkpointer,
        system_prompt=system_prompt
    )
