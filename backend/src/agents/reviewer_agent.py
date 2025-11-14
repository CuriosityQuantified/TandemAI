"""
Reviewer Agent - LangChain ReAct agent for quality validation.

Uses LangChain's create_agent() with explicit tools:
- read_file: Deep Agents built-in tool (reads from state["files"])
- reject_submission: Custom tool for rejection feedback
- accept_submission: Custom tool for acceptance feedback

This is a standalone LangChain ReAct agent, not a Deep Agents sub-agent.
All imports are ABSOLUTE.
"""

import logging
from langchain.agents import create_agent
from deepagents.tools import read_file  # Import built-in tool from Deep Agents

from backend.src.agents.model_config import get_claude_sonnet_4_5
from backend.src.utils.prompt_loader import load_agent_prompt
from backend.src.tools.reviewer_tools import reject_submission, accept_submission

logger = logging.getLogger(__name__)


def create_reviewer_agent():
    """
    Create LangChain ReAct reviewer agent for validating sub-agent submissions.

    This agent is called automatically when sub-agents use submit() tool.
    It reviews outputs against universal standards:
    - Accuracy: Information is correct and factual
    - Completeness: All required elements included
    - Quality: Professional output, no placeholders
    - Citations: Sources provided when applicable

    Tools:
    - read_file: Deep Agents built-in tool (reads from virtual filesystem)
    - reject_submission: Custom tool for rejection with actionable feedback
    - accept_submission: Custom tool for acceptance and supervisor notification

    Returns:
        LangChain ReAct agent configured for review workflow

    Example:
        >>> reviewer = create_reviewer_agent()
        >>> result = reviewer.invoke({
        ...     "messages": [{
        ...         "role": "user",
        ...         "content": "Review submission: /workspace/output.txt"
        ...     }]
        ... })
    """
    try:
        # Load reviewer prompt from YAML
        logger.info("Loading reviewer prompt from reviewer_agent.yaml")
        reviewer_prompt = load_agent_prompt("reviewer_agent")

        # Get Claude Sonnet 4.5 (best code evaluation - 77.2% SWE-bench)
        logger.info("Configuring Claude Sonnet 4.5 for reviewer (best code evaluation)")
        model = get_claude_sonnet_4_5(temperature=0.3)

        # Create LangChain ReAct agent with explicit tools
        # NOTE: Must explicitly pass all tools, no auto-inheritance
        logger.info("Creating LangChain ReAct reviewer agent with 3 tools")
        reviewer_agent = create_agent(
            model=model,
            tools=[read_file, reject_submission, accept_submission],
            prompt=reviewer_prompt,
        )

        logger.info("✅ Reviewer agent created successfully")
        logger.info("🔧 Tools: read_file (built-in), reject_submission (custom), accept_submission (custom)")
        logger.info("🧠 Model: Claude Sonnet 4.5 (77.2% SWE-bench)")

        return reviewer_agent

    except FileNotFoundError as e:
        logger.error(f"❌ Reviewer prompt file not found: {e}")
        raise ValueError(
            f"Failed to load reviewer_agent.yaml. Ensure file exists in prompts/ directory. Error: {e}"
        )
    except Exception as e:
        logger.error(f"❌ Failed to create reviewer agent: {e}", exc_info=True)
        raise RuntimeError(f"Reviewer agent creation failed: {e}")
