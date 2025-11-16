"""
Expert Analyst Subagent - Structured Problem Solving and Strategic Thinking
============================================================================

Specialized subagent for strategic analysis, root cause investigation, and decision frameworks.

Capabilities:
- Root cause analysis (5 Whys, Fishbone diagrams)
- Strategic planning and frameworks (SWOT, Porter's Five Forces)
- Decision analysis and trade-off evaluation
- System thinking and complexity analysis
- Problem decomposition and solution design

Usage:
    expert_analyst = create_expert_analyst_subagent(checkpointer, workspace_dir)
    result = await expert_analyst.ainvoke(
        {"messages": [{"role": "user", "content": "Analyze problem..."}]},
        config={"configurable": {"thread_id": "analyst-123"}}
    )
"""

from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langchain_anthropic import ChatAnthropic

# Import centralized prompt and date utility
from backend.prompts.expert_analyst import get_expert_analyst_prompt
from backend.utils.date_helper import get_current_date


def create_expert_analyst_subagent(checkpointer, workspace_dir: str):
    """
    Create expert analyst subagent specialized in strategic problem solving.

    The expert analyst subagent is a full-featured autonomous agent with:
    - Tavily search for research on best practices and frameworks
    - Write/edit file capabilities for analysis documents
    - Focus on structured thinking and strategic analysis

    Args:
        checkpointer: PostgreSQL checkpointer for state persistence
        workspace_dir: Base directory for file operations

    Returns:
        Configured expert analyst DeepAgent

    Example:
        analyst = create_expert_analyst_subagent(checkpointer, "/workspace")

        config = {"configurable": {"thread_id": "analyst-abc123"}}

        result = await analyst.ainvoke({
            "messages": [{
                "role": "user",
                "content": '''Analyze the root causes of declining solar adoption in specific regions.

                Requirements:
                - Use structured problem-solving framework (5 Whys, Fishbone)
                - Identify key contributing factors
                - Evaluate potential solutions
                - Write comprehensive analysis to /workspace/analysis/solar_adoption_analysis.md
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

    # Use Claude Haiku 4.5 for enhanced strategic reasoning
    model = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0.3  # Slightly creative for innovative solutions
    )

    # Specialized system prompt for strategic analysis
    # Use centralized system prompt with date injection
    system_prompt = get_expert_analyst_prompt(get_current_date())


    # Create expert analyst agent with specialized tools
    return create_deep_agent(
        model=model,
        tools=[
            tavily_search,              # Research frameworks and best practices
            write_file_tool,            # Create analysis documents (with approval)
            edit_file_with_approval,    # Edit analysis documents (with approval)
            read_current_plan_tool,     # Check main agent's plan for context
        ],
        backend=create_hybrid_backend,
        checkpointer=checkpointer,
        system_prompt=system_prompt
    )
