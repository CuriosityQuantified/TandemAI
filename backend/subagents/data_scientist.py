"""
Data Scientist Subagent - Statistical Analysis and Data Interpretation
=======================================================================

Specialized subagent for quantitative analysis, statistical testing, and data visualization.

Capabilities:
- Statistical analysis of datasets
- Hypothesis testing and significance calculations
- Data pattern identification
- Quantitative research methodologies
- Visualization recommendations

Usage:
    data_scientist = create_data_scientist_subagent(checkpointer, workspace_dir)
    result = await data_scientist.ainvoke(
        {"messages": [{"role": "user", "content": "Analyze dataset..."}]},
        config={"configurable": {"thread_id": "data-scientist-123"}}
    )
"""

from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langchain_anthropic import ChatAnthropic

# Import centralized prompt and date utility
from backend.prompts.data_scientist import get_data_scientist_prompt
from backend.utils.date_helper import get_current_date


def create_data_scientist_subagent(checkpointer, workspace_dir: str):
    """
    Create data scientist subagent specialized in statistical analysis.

    The data scientist subagent is a full-featured autonomous agent with:
    - Tavily search for research on statistical methods
    - Write/edit file capabilities for analysis reports
    - Focus on quantitative analysis and data interpretation

    Args:
        checkpointer: PostgreSQL checkpointer for state persistence
        workspace_dir: Base directory for file operations

    Returns:
        Configured data scientist DeepAgent

    Example:
        data_scientist = create_data_scientist_subagent(checkpointer, "/workspace")

        config = {"configurable": {"thread_id": "ds-abc123"}}

        result = await data_scientist.ainvoke({
            "messages": [{
                "role": "user",
                "content": '''Analyze the renewable energy dataset in /workspace/data/energy_stats.csv.

                Tasks:
                - Perform statistical analysis on growth trends
                - Calculate year-over-year growth rates
                - Identify significant patterns or anomalies
                - Create visualizations (describe what should be visualized)
                - Write comprehensive analysis to /workspace/analysis/energy_trends.md
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

    # Use Claude Haiku 4.5 for enhanced analytical reasoning
    model = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0  # Deterministic for analytical precision
    )

    # Use centralized system prompt with date injection
    system_prompt = get_data_scientist_prompt(get_current_date())


    # Create data scientist agent with specialized tools
    return create_deep_agent(
        model=model,
        tools=[
            tavily_search,              # Research statistical methods
            write_file_tool,            # Create analysis reports (with approval)
            edit_file_with_approval,    # Edit analysis documents (with approval)
            read_current_plan_tool,     # Check main agent's plan for context
        ],
        backend=create_hybrid_backend,
        checkpointer=checkpointer,
        system_prompt=system_prompt
    )
