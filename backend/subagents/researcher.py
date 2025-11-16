"""
Researcher Subagent - Objective Fact Gathering with Mandatory Citations
========================================================================

Specialized subagent for research tasks with strict citation requirements.

CRITICAL CITATION FORMAT:
- Every factual claim MUST be cited with [1] [2] [3] format
- Include exact quotes from sources (not summaries)
- Sources section at bottom with full references

Example Output:
    "The study found 45% improvement[1] in outcomes. Experts noted 'significant progress'[2].

    ## Sources
    [1] Smith et al. 2025. 'AI Healthcare Study'. Journal of Medicine. https://example.com.
        Quote: 'improvement of 45% observed in patient outcomes'
    [2] Johnson, Dr. 2025. 'Expert Commentary'. Medical News. https://example.com.
        Quote: 'significant progress in the field'"

Usage:
    researcher = create_researcher_subagent(checkpointer, workspace_dir)
    result = await researcher.ainvoke(
        {"messages": [{"role": "user", "content": "Research AI trends"}]},
        config={"configurable": {"thread_id": "researcher-123"}}
    )
"""

import re
from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langchain_google_genai import ChatGoogleGenerativeAI

# Import centralized prompt and date utility
# CRITICAL FIX #2: Use explicit import to avoid ambiguous get_researcher_prompt imports
# - benchmark_researcher_prompt.py: Production baseline (Enhanced V3)
# - challenger_researcher_prompt_1.py: Experimental template
# Using benchmark version (production baseline) for researcher subagent
from backend.prompts.prompts.researcher.benchmark_researcher_prompt import get_researcher_prompt as get_benchmark_prompt
from backend.utils.date_helper import get_current_date


def validate_researcher_output(file_path: str) -> dict:
    """
    Validate researcher output has proper [1] [2] [3] citations.

    STRICT VALIDATION - Blocks completion if citations missing.

    Args:
        file_path: Path to the output file to validate

    Returns:
        dict: Validation result with citation_count and validity

    Raises:
        ValueError: If citations are missing or improperly formatted
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        raise ValueError(f"Output file not found: {file_path}")

    # Check for Sources section first
    has_sources = bool(
        re.search(r'#+\s*Sources', content, re.IGNORECASE) or
        re.search(r'References:', content, re.IGNORECASE)
    )

    # Extract body text (before Sources section) for citation checking
    sources_match = re.search(r'#+\s*(Sources|References):?', content, re.IGNORECASE)
    if sources_match:
        body_text = content[:sources_match.start()]
    else:
        body_text = content

    # Check for citation markers [1] [2] [3] in body text only
    citations = re.findall(r'\[(\d+)\]', body_text)

    if not citations:
        raise ValueError(
            "❌ RESEARCHER OUTPUT INVALID: No citations found!\n\n"
            "REQUIRED FORMAT:\n"
            "- Cite every claim with [1] [2] [3] format\n"
            "- Include exact quotes (not summaries)\n"
            "- Add Sources section at bottom\n\n"
            "EXAMPLE:\n"
            "The study found 45% improvement[1]. Experts noted 'significant progress'[2].\n\n"
            "## Sources\n"
            "[1] Smith et al. (2025). 'Title'. Source. URL. Quote: 'exact text from source'\n"
            "[2] Johnson. (2025). 'Title'. Source. URL. Quote: 'exact text from source'"
        )

    if not has_sources:
        raise ValueError(
            "❌ RESEARCHER OUTPUT INVALID: No Sources section found!\n\n"
            "REQUIRED: Add '## Sources' or '# Sources' section at bottom with:\n"
            "[1] Author. (Year). 'Title'. Source. URL. Quote: 'exact text'\n"
            "[2] ..."
        )

    # Check if citations are sequential and start from 1
    citation_nums = sorted([int(c) for c in set(citations)])
    expected_nums = list(range(1, len(citation_nums) + 1))

    if citation_nums != expected_nums:
        raise ValueError(
            f"❌ RESEARCHER OUTPUT INVALID: Citations not sequential!\n"
            f"Found: {citation_nums}\n"
            f"Expected: {expected_nums}\n"
            f"Citations must start at [1] and increment sequentially."
        )

    # Validation passed
    return {
        "valid": True,
        "citation_count": len(set(citations)),
        "has_sources_section": has_sources,
        "sequential": True
    }


def create_researcher_subagent(checkpointer, workspace_dir: str):
    """
    Create researcher subagent specialized in fact gathering with citations.

    The researcher subagent is a full-featured autonomous agent with:
    - Tavily search for gathering sources
    - Write/edit file capabilities (with approval workflows)
    - Mandatory [1] [2] [3] citation format
    - Exact quote extraction (not summaries)

    Args:
        checkpointer: PostgreSQL checkpointer for state persistence
        workspace_dir: Base directory for file operations

    Returns:
        Configured researcher DeepAgent

    Example:
        researcher = create_researcher_subagent(checkpointer, "/workspace")

        config = {"configurable": {"thread_id": "researcher-abc123"}}

        result = await researcher.ainvoke({
            "messages": [{
                "role": "user",
                "content": '''Research AI trends in healthcare for 2025.

                Requirements:
                - Find at least 10 credible sources
                - Extract exact quotes for key statistics
                - Write findings to /workspace/research/ai_healthcare_2025.md
                - Use [1] [2] [3] citation format
                - Include Sources section with full references
                '''
            }]
        }, config)
    """
    # Import tools from parent module
    # NOTE: These imports are inside the function to avoid circular dependencies
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

    # Use Claude Haiku 4.5 for enhanced research
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0  # Deterministic for research accuracy
    )

    # Use centralized system prompt with enhanced citations and current date
    system_prompt = get_benchmark_prompt(get_current_date())

    # Create researcher agent with specialized tools
    return create_deep_agent(
        model=model,
        tools=[
            tavily_search,              # Primary research tool
            write_file_tool,            # Document creation (with approval)
            edit_file_with_approval,    # Document editing (with approval)
            read_current_plan_tool,     # Check main agent's plan for context
        ],
        backend=create_hybrid_backend,
        checkpointer=checkpointer,
        system_prompt=system_prompt
    )
