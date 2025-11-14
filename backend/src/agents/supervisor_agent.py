"""
ATLAS Supervisor Agent using Deep Agents library.

ASYNC by default for parallel execution.
All imports are ABSOLUTE.
"""

import sys
from pathlib import Path

# Add deepagents to Python path (editable install workaround)
deepagents_src = Path(__file__).parents[3] / "deepagents" / "src"
if deepagents_src.exists():
    sys.path.insert(0, str(deepagents_src))

import logging
from typing import Dict, Any, Optional
from deepagents import async_create_deep_agent

from backend.src.agents.model_config import get_claude_sonnet_4_5, get_claude_sonnet_4
from backend.src.agents.reviewer_agent import create_reviewer_agent
from backend.src.utils.prompt_loader import load_agent_prompt
from backend.src.tools.external_tools import internet_search, execute_python_code
from backend.src.tools.submit_tool import submit, set_reviewer_agent

logger = logging.getLogger(__name__)


async def create_supervisor_agent():
    """
    Create ATLAS supervisor agent using Deep Agents.

    ASYNC by default - supports parallel tool execution.

    The supervisor agent coordinates three specialized sub-agents:
    - Research Agent: Web search and information gathering
    - Analysis Agent: Python code execution and data analysis
    - Writing Agent: Professional document creation

    Built-in Tools (from Deep Agents):
    - write_todos: Task planning and tracking
    - write_file: Write to virtual filesystem
    - read_file: Read from virtual filesystem
    - ls: List virtual filesystem contents
    - edit_file: Edit virtual filesystem files

    External Tools:
    - internet_search: Tavily web search
    - execute_python_code: E2B sandboxed Python execution

    Sub-agent Delegation:
    - research-agent: Specialized for web research
    - analysis-agent: Specialized for data analysis and code
    - writing-agent: Specialized for document creation

    Returns:
        Async deep agent graph ready for task execution

    Example:
        >>> agent = await create_supervisor_agent()
        >>> result = await agent.ainvoke({
        ...     "messages": [{"role": "user", "content": "Research AI trends"}]
        ... })
        >>> print(result["messages"][-1].content)
    """
    try:
        # Load supervisor prompt from YAML
        logger.info("Loading supervisor prompt from global_supervisor.yaml")
        supervisor_prompt = load_agent_prompt("global_supervisor")

        # Get Claude Sonnet 4.5 with balanced temperature for supervisor
        logger.info("Configuring Claude Sonnet 4.5 (best orchestration, 30+ hour focus)")
        model = get_claude_sonnet_4_5(temperature=0.7)

        # Define sub-agents for specialized delegation
        logger.info("Configuring 3 specialized sub-agents (research, analysis, writing)")
        subagents = [
            {
                "name": "research-agent",
                "description": (
                    "Specialized agent for web research and information gathering. "
                    "Use this agent when you need to find information online, "
                    "gather data from multiple sources, research topics, or verify facts. "
                    "The research agent will conduct systematic searches and return "
                    "well-cited findings with source URLs."
                ),
                "prompt": load_agent_prompt("research_agent"),
                "tools": [internet_search, submit],  # Submit triggers automatic review
                "model": get_claude_sonnet_4_5(temperature=0.5),  # Factual, best performance
            },
            {
                "name": "analysis-agent",
                "description": (
                    "Specialized agent for data analysis and code execution. "
                    "Use this agent when you need to process data, run calculations, "
                    "perform statistical analysis, create visualizations, or execute "
                    "Python code in a safe sandbox environment. The analysis agent "
                    "will provide reproducible results with code documentation."
                ),
                "prompt": load_agent_prompt("analysis_agent"),
                "tools": [execute_python_code, submit],  # Submit triggers automatic review
                "model": get_claude_sonnet_4(temperature=0.3),  # Extended thinking mode
            },
            {
                "name": "writing-agent",
                "description": (
                    "Specialized agent for content creation and document writing. "
                    "Use this agent when you need to create final reports, synthesize "
                    "research findings into polished documents, write executive summaries, "
                    "or produce professional content. The writing agent will create "
                    "well-structured, audience-appropriate documents with proper citations."
                ),
                "prompt": load_agent_prompt("writing_agent"),
                "tools": [submit],  # Submit triggers automatic review (also has built-in file tools)
                "model": get_claude_sonnet_4_5(temperature=0.8),  # Creative, best quality
            },
        ]

        # Configure reviewer agent reference for submit tool
        # Create standalone LangChain ReAct reviewer agent
        logger.info("Creating standalone LangChain ReAct reviewer agent for submit() tool")
        reviewer_agent = create_reviewer_agent()
        set_reviewer_agent(reviewer_agent)
        logger.info("✅ Reviewer agent configured in submit() tool")

        # Create supervisor agent with async support
        # NOTE: Supervisor does NOT get direct access to internet_search or execute_python_code
        # It MUST delegate to sub-agents using the task tool
        logger.info("Creating supervisor agent with Deep Agents")
        agent = async_create_deep_agent(
            tools=[],  # No external tools - supervisor must delegate
            instructions=supervisor_prompt,
            model=model,
            subagents=subagents,
        )

        # Log successful creation
        logger.info("✅ Supervisor agent created successfully")
        logger.info("📦 Built-in tools: write_todos, write_file, read_file, ls, edit_file, task")
        logger.info("🚫 External tools: None (must delegate via task tool)")
        logger.info("🤖 Sub-agents: research-agent, analysis-agent, writing-agent")
        logger.info("✅ Submit tool: Added to all worker agents (triggers automatic review)")
        logger.info("🔍 Reviewer: Standalone LangChain ReAct agent (read_file, accept_submission, reject_submission)")
        logger.info("⚡ Async: Enabled for parallel tool execution")
        logger.info("🧠 Model: Claude Sonnet 4.5 (77.2% SWE-bench, 30+ hour focus)")

        return agent

    except FileNotFoundError as e:
        logger.error(f"❌ Prompt file not found: {e}")
        raise ValueError(
            f"Failed to load agent prompts. Ensure all YAML files exist in prompts/ directory. Error: {e}"
        )
    except Exception as e:
        logger.error(f"❌ Failed to create supervisor agent: {e}", exc_info=True)
        raise RuntimeError(f"Supervisor agent creation failed: {e}")


async def invoke_supervisor(
    message: str,
    session_id: Optional[str] = None,
    checkpointer = None,
) -> Dict[str, Any]:
    """
    Convenience function to create and invoke supervisor agent.

    This is a higher-level wrapper that handles agent creation,
    configuration, and invocation in a single call.

    Args:
        message: User message/task to execute
        session_id: Optional session ID for state persistence
        checkpointer: Optional LangGraph checkpointer for session state

    Returns:
        Dictionary containing:
        - messages: List of conversation messages
        - files: Virtual filesystem contents (created by agent)

    Example:
        >>> from langgraph.checkpoint.memory import InMemorySaver
        >>> checkpointer = InMemorySaver()
        >>> result = await invoke_supervisor(
        ...     "Research the top 3 Python frameworks",
        ...     session_id="test-session",
        ...     checkpointer=checkpointer
        ... )
        >>> print(result["messages"][-1].content)
    """
    # Create supervisor agent
    agent = await create_supervisor_agent()

    # Attach checkpointer if provided
    if checkpointer:
        agent.checkpointer = checkpointer

    # Create config with session ID
    config = {}
    if session_id:
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }

    # Invoke agent
    logger.info(f"🚀 Invoking supervisor for session: {session_id or 'default'}")
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config
    )

    logger.info(f"✅ Task completed: {len(result.get('messages', []))} messages")
    return result
