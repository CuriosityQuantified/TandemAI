"""
Baseline Agent Wrapper for Test Config 1

This module provides a wrapper to integrate test_config_1_deepagent_supervisor_command.py
with the evaluation framework, making it compatible with the test suite's expected interface.

The test suite expects:
    agent_function(query: str) -> Dict[str, Any]

Where the returned dict contains:
    - messages: List of messages (final message has the response)
    - plan: Optional plan dict with steps
    - files: Optional list of files created

This wrapper adapts the test_config_1 graph to match this interface.

BASELINE CONFIGURATION (Researcher Agent):
    - Agent Type: Researcher
    - Config: test_config_1_deepagent_supervisor_command.py
    - Prompt: benchmark_researcher_prompt.py (Enhanced V3)
    - Model: Gemini 2.5 Flash
    - Temperature: 0.7
    - Pattern: DeepAgent-inspired supervisor with Command.goto routing

SUPPORTED AGENT TYPES:
    - "Researcher" - Research and information gathering agent (implemented)
    - "Supervisor" - Task orchestration and delegation agent (future)
    - "Data Scientist" - Data analysis and visualization agent (future)
    - "Writer" - Content generation and editing agent (future)
    - "Reviewer" - Quality assessment and feedback agent (future)
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Literal
from datetime import datetime

# Add necessary paths
main_path = Path(__file__).parent.parent
backend_path = main_path / "TandemAI" / "backend"
test_configs_path = backend_path / "test_configs"
prompts_path = main_path / "prompts"  # Add prompts directory
sys.path.insert(0, str(prompts_path))  # Add prompts for researcher prompt import
sys.path.insert(0, str(test_configs_path))  # Add test_configs for shared_tools import
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(main_path))

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# LangChain message types for processing
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# NOTE: test_config_1 import moved inside create_baseline_agent() function
# to ensure sys.path is configured before import attempts occur

# Type alias for supported agent types
AgentType = Literal["Researcher", "Supervisor", "Data Scientist", "Writer", "Reviewer"]


def extract_plan_from_messages(messages: list) -> Dict[str, Any] | None:
    """
    Extract research plan from tool messages if available.

    Looks for create_research_plan tool results in the message history.

    Args:
        messages: List of LangChain messages from graph execution

    Returns:
        Dict with plan structure if found, None otherwise
    """
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.name == "create_research_plan":
            # Parse plan from tool message content
            import json
            try:
                plan_data = json.loads(msg.content)
                return {
                    "steps": [
                        {
                            "step_index": i,
                            "description": step.get("description", ""),
                            "status": step.get("status", "pending")
                        }
                        for i, step in enumerate(plan_data.get("steps", []))
                    ],
                    "query": plan_data.get("query", ""),
                    "num_steps": plan_data.get("num_steps", 0)
                }
            except (json.JSONDecodeError, KeyError):
                # If parsing fails, return None
                return None
    return None


def extract_files_from_messages(messages: list) -> list[str]:
    """
    Extract any file paths from save_output or file-related tool calls.

    Args:
        messages: List of LangChain messages from graph execution

    Returns:
        List of file paths created during execution
    """
    files = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            if msg.name in ["save_output", "write_file", "create_file"]:
                # Try to extract file path from tool content
                import re
                content = str(msg.content)
                # Look for file path patterns
                path_match = re.search(r'(?:saved to|created|written to):\s*([^\s,]+)', content, re.IGNORECASE)
                if path_match:
                    files.append(path_match.group(1))
    return files


def create_baseline_agent(agent_type: AgentType) -> callable:
    """
    Create the baseline agent function compatible with the test suite.

    This function creates a wrapper around the baseline agent configuration that:
    1. Accepts a query string
    2. Executes the baseline agent configuration for the specified agent type
    3. Returns results in the format expected by the evaluation framework

    Args:
        agent_type: Type of agent to create baseline for ("Researcher", "Supervisor", etc.)

    Returns:
        Callable with signature: execute_research_query(query: str) -> Dict[str, Any]

    Raises:
        ValueError: If agent_type is not implemented yet

    BASELINE CONFIGURATION DETAILS (Researcher):
        - Configuration: test_config_1_deepagent_supervisor_command
        - Researcher Prompt: benchmark_researcher_prompt (Enhanced V3)
        - Model: Gemini 2.5 Flash (gemini-2.5-flash)
        - Architecture: Supervisor → Delegation Tools → Researcher (Command.goto routing)
        - Tools: Tavily search, planning tools, file operations
    """

    # Validate agent type is implemented
    if agent_type != "Researcher":
        raise ValueError(
            f"Agent type '{agent_type}' not yet implemented. "
            f"Currently only 'Researcher' is supported. "
            f"Future agent types: Supervisor, Data Scientist, Writer, Reviewer"
        )

    # Import test_config_1 graph AFTER sys.path is configured
    # (This import is at function level to ensure paths are set first)
    from TandemAI.backend.test_configs.test_config_1_deepagent_supervisor_command import graph

    def execute_research_query(query: str) -> Dict[str, Any]:
        """
        Execute a query using the baseline agent configuration.

        This function runs the baseline agent (currently test_config_1 for Researcher type)
        and returns results in the format expected by the evaluation framework.

        Agent Type: {agent_type}
        Configuration: test_config_1_deepagent_supervisor_command (Researcher)
        Prompt: benchmark_researcher_prompt V3

        Args:
            query: The query/question for the agent to process

        Returns:
            Dict containing:
                - messages: List of all messages from the graph execution
                  (includes HumanMessage, AIMessage, ToolMessage, SystemMessage)
                - plan: Extracted research plan if available (dict with steps, query, num_steps)
                - files: List of files created during execution (if any)

        Example:
            >>> agent = create_baseline_agent("Researcher")
            >>> result = agent("What are the latest developments in quantum computing?")
            >>> print(f"Messages: {len(result['messages'])}")
            >>> print(f"Plan steps: {result['plan']['num_steps'] if result['plan'] else 'No plan'}")
        """
        # Create unique thread ID for this evaluation
        thread_id = f"eval_{datetime.now().timestamp()}"

        # Configure graph execution
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 50  # Allow complex research flows with multiple tool calls
        }

        # Execute graph with streaming to collect all messages
        all_messages = []

        try:
            for event in graph.stream(
                {"messages": [HumanMessage(content=query)]},
                config=config,
                stream_mode="values"
            ):
                # Collect messages from each event
                messages = event.get("messages", [])
                all_messages = messages  # Update with latest state

            # Extract plan from messages (if researcher created one)
            plan = extract_plan_from_messages(all_messages)

            # Extract files from messages (if any were created)
            files = extract_files_from_messages(all_messages)

            # Return in expected format
            return {
                "messages": all_messages,
                "plan": plan,
                "files": files
            }

        except Exception as e:
            # If execution fails, return error message
            print(f"ERROR in baseline agent execution: {e}")
            import traceback
            traceback.print_exc()

            # Return minimal error response
            return {
                "messages": [
                    HumanMessage(content=query),
                    AIMessage(content=f"Error during execution: {str(e)}")
                ],
                "plan": None,
                "files": []
            }

    return execute_research_query


# Singleton instances for reuse across multiple test queries
# Separate instance for each agent type
_baseline_agent_instances: Dict[str, callable] = {}


def get_baseline_agent(agent_type: AgentType = "Researcher") -> callable:
    """
    Get or create the baseline agent instance for the specified agent type.

    Uses singleton pattern to avoid recreating the agent multiple times,
    which improves performance when running multiple test queries.

    Args:
        agent_type: Type of agent to get/create ("Researcher", "Supervisor", etc.)
                   Defaults to "Researcher" (currently the only implemented type)

    Returns:
        Callable baseline agent function (execute_research_query)

    Raises:
        ValueError: If agent_type is not implemented yet

    Examples:
        >>> # Get baseline researcher agent
        >>> researcher = get_baseline_agent("Researcher")
        >>> result = researcher("What is quantum computing?")

        >>> # Future: Get baseline supervisor agent
        >>> # supervisor = get_baseline_agent("Supervisor")
    """
    global _baseline_agent_instances

    # Check if we already have an instance for this agent type
    if agent_type not in _baseline_agent_instances:
        print(f"✓ Creating baseline {agent_type} agent...")
        print(f"  Config: test_config_1_deepagent_supervisor_command")
        print(f"  Prompt: benchmark_researcher_prompt V3")
        print(f"  Model: Gemini 2.5 Flash")

        _baseline_agent_instances[agent_type] = create_baseline_agent(agent_type)
        print(f"✓ Baseline {agent_type} agent initialized")

    return _baseline_agent_instances[agent_type]


if __name__ == "__main__":
    # Test the wrapper to verify it works correctly
    print("="*80)
    print("TESTING BASELINE AGENT WRAPPER")
    print("="*80)

    # Test Researcher agent (currently implemented)
    print("\n" + "="*80)
    print("TEST 1: Researcher Agent (Baseline)")
    print("="*80)
    print("\nBaseline Configuration:")
    print("  - Agent Type: Researcher")
    print("  - Config: test_config_1_deepagent_supervisor_command")
    print("  - Prompt: benchmark_researcher_prompt (Enhanced V3)")
    print("  - Model: Gemini 2.5 Flash")
    print("  - Pattern: DeepAgent supervisor + Command.goto routing")

    researcher_agent = get_baseline_agent("Researcher")

    test_query = "What are the key features of Python 3.12?"
    print(f"\nTest Query: {test_query}")
    print("\nExecuting...")

    result = researcher_agent(test_query)

    print("\n" + "="*80)
    print("RESULT")
    print("="*80)
    print(f"Messages: {len(result['messages'])}")
    print(f"Plan: {'Yes' if result['plan'] else 'No'}")
    if result['plan']:
        print(f"  Steps: {result['plan'].get('num_steps', 'N/A')}")
    print(f"Files: {len(result['files'])}")

    # Show final response
    final_msgs = [msg for msg in result['messages']
                  if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls]
    if final_msgs:
        print("\nFinal Response Preview:")
        print("-"*80)
        content = str(final_msgs[-1].content)
        preview = content[:500] + "..." if len(content) > 500 else content
        print(preview)
        print("-"*80)

    # Test that unimplemented agent types raise errors
    print("\n" + "="*80)
    print("TEST 2: Unimplemented Agent Type (Expected Error)")
    print("="*80)
    try:
        supervisor_agent = get_baseline_agent("Supervisor")
        print("❌ ERROR: Should have raised ValueError!")
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")
