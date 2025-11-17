"""
Agent Invoker - Dynamic Graph Creation for Prompt Version Testing

Provides functions to invoke researcher agents with different prompt versions
for A/B testing and evaluation.

Based on test_config_1_deepagent_supervisor_command.py pattern but with
dynamic prompt injection instead of hardcoded benchmark_researcher_prompt.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Callable, Dict, Any
from datetime import datetime

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# LangGraph imports
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain.agents import create_agent
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

# Import shared tools
from evaluation.configs.shared_tools import get_subagent_tools

# ============================================================================
# CONFIGURATION
# ============================================================================

MODEL_NAME = "gemini-2.5-flash"
TEMPERATURE = 0.7
RECURSION_LIMIT = 50  # Match test_config_1 setting


def create_researcher_agent(
    prompt_func: Callable[[str], str],
    model_name: str = MODEL_NAME,
    temperature: float = TEMPERATURE
) -> StateGraph:
    """
    Create a researcher agent with a specific prompt version.

    This is a simplified version of test_config_1's create_researcher_subagent(),
    but it accepts the prompt function as a parameter instead of hardcoding
    benchmark_researcher_prompt.

    Args:
        prompt_func: Function that takes current_date and returns system prompt
                    (e.g., get_researcher_prompt from v3.0.py or v3.1.py)
        model_name: LLM model to use (default: gemini-2.5-flash)
        temperature: Sampling temperature (default: 0.7)

    Returns:
        Configured researcher agent graph (StateGraph)

    Example:
        >>> from backend.prompts.versions.researcher.v3_0 import get_researcher_prompt
        >>> agent = create_researcher_agent(get_researcher_prompt)
        >>> result = agent.invoke({"messages": [HumanMessage("Research AI trends")]})
    """
    # Get researcher tools (planning + research + files, NO delegation)
    researcher_tools = get_subagent_tools()

    # Get system prompt with current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    researcher_system_prompt = prompt_func(current_date)

    # Create the researcher agent graph with custom prompt
    researcher_graph = create_agent(
        model=ChatGoogleGenerativeAI(model=model_name, temperature=temperature),
        tools=researcher_tools,
        system_prompt=researcher_system_prompt  # ← Dynamic prompt injection
    )

    return researcher_graph


def invoke_researcher_with_prompt(
    prompt_func: Callable[[str], str],
    query: str,
    config: Dict[str, Any] = None
) -> str:
    """
    Invoke researcher agent with a specific prompt version on a single query.

    This is the main function used by compare_prompt_versions.py to evaluate
    different prompt versions on the same test queries.

    Args:
        prompt_func: Prompt function from versioned prompt file
                    (e.g., get_researcher_prompt from v3.0.py or v3.1.py)
        query: Research query string (e.g., "What are latest AI trends?")
        config: Optional LangGraph config dict with thread_id, recursion_limit, etc.

    Returns:
        Final response text from the researcher agent (string)

    Raises:
        Exception: If agent execution fails

    Example:
        >>> from backend.prompts.versions.researcher.v3_0 import get_researcher_prompt
        >>> response = invoke_researcher_with_prompt(
        ...     prompt_func=get_researcher_prompt,
        ...     query="What are the latest developments in quantum computing?",
        ...     config={"configurable": {"thread_id": "eval_v3.0_q001"}}
        ... )
        >>> print(response)
        "Quantum computing has seen significant advances in 2025..."
    """
    # Create researcher agent with specified prompt
    researcher_graph = create_researcher_agent(prompt_func)

    # Prepare config (use defaults if not provided)
    if config is None:
        config = {}

    # Ensure recursion limit is set
    if "recursion_limit" not in config:
        config["recursion_limit"] = RECURSION_LIMIT

    # Prepare input messages
    messages = [HumanMessage(content=query)]

    # Invoke agent
    try:
        result = researcher_graph.invoke(
            {"messages": messages},
            config=config
        )
    except Exception as e:
        raise Exception(f"Agent invocation failed for query '{query[:50]}...': {str(e)}")

    # Extract final response from messages
    agent_response = extract_final_response(result.get("messages", []))

    return agent_response


def extract_final_response(messages: list) -> str:
    """
    Extract final response text from agent messages.

    Handles both simple text messages and multimodal content (text blocks).
    Based on pattern from baseline_agent_wrapper.py.

    Args:
        messages: List of messages from graph execution

    Returns:
        Final response text (string)

    Example:
        >>> messages = [
        ...     HumanMessage(content="Query"),
        ...     AIMessage(content="Response text")
        ... ]
        >>> extract_final_response(messages)
        "Response text"
    """
    if not messages:
        return ""

    # Get last message (final response)
    final_msg = messages[-1]

    # Handle multimodal content (list of content blocks)
    if isinstance(final_msg.content, list):
        # Extract text from all blocks
        text_parts = []
        for block in final_msg.content:
            if isinstance(block, dict) and "text" in block:
                text_parts.append(block["text"])
            elif isinstance(block, str):
                text_parts.append(block)
            else:
                # Convert other types to string
                text_parts.append(str(block))

        response_text = " ".join(text_parts)
    else:
        # Simple text content
        response_text = str(final_msg.content)

    return response_text.strip()


# ============================================================================
# BATCH INVOCATION (for test suite evaluation)
# ============================================================================

def invoke_researcher_batch(
    prompt_func: Callable[[str], str],
    queries: list,
    model_name: str = MODEL_NAME,
    temperature: float = TEMPERATURE,
    verbose: bool = False
) -> list:
    """
    Invoke researcher on multiple queries (batch processing).

    More efficient than calling invoke_researcher_with_prompt() individually
    because it reuses the same agent graph.

    Args:
        prompt_func: Prompt function from versioned prompt file
        queries: List of query strings
        model_name: LLM model to use
        temperature: Sampling temperature
        verbose: Print progress messages

    Returns:
        List of response strings (same order as queries)

    Example:
        >>> from backend.prompts.versions.researcher.v3_0 import get_researcher_prompt
        >>> queries = ["Query 1", "Query 2", "Query 3"]
        >>> responses = invoke_researcher_batch(get_researcher_prompt, queries)
        >>> len(responses)
        3
    """
    # Create researcher agent once (reuse for all queries)
    researcher_graph = create_researcher_agent(prompt_func, model_name, temperature)

    responses = []

    for i, query in enumerate(queries):
        if verbose:
            print(f"[{i+1}/{len(queries)}] Processing: {query[:60]}...")

        # Prepare config with unique thread_id for each query
        config = {
            "configurable": {"thread_id": f"batch_{i}_{hash(query)}"},
            "recursion_limit": RECURSION_LIMIT
        }

        # Invoke agent
        try:
            result = researcher_graph.invoke(
                {"messages": [HumanMessage(content=query)]},
                config=config
            )
            response = extract_final_response(result.get("messages", []))
            responses.append(response)

            if verbose:
                print(f"  ✓ Response length: {len(response)} chars")

        except Exception as e:
            error_msg = f"ERROR: {str(e)}"
            responses.append(error_msg)

            if verbose:
                print(f"  ✗ Failed: {str(e)}")

    return responses


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_prompt_function(prompt_func: Callable[[str], str]) -> bool:
    """
    Validate that a prompt function has the expected signature and output.

    Args:
        prompt_func: Prompt function to validate

    Returns:
        True if valid, raises Exception otherwise

    Example:
        >>> from backend.prompts.versions.researcher.v3_0 import get_researcher_prompt
        >>> validate_prompt_function(get_researcher_prompt)
        True
    """
    # Test with sample date
    test_date = "2025-11-16"

    try:
        result = prompt_func(test_date)
    except Exception as e:
        raise Exception(f"Prompt function failed with error: {str(e)}")

    # Check result is a string
    if not isinstance(result, str):
        raise Exception(f"Prompt function must return string, got {type(result)}")

    # Check result is not empty
    if not result.strip():
        raise Exception("Prompt function returned empty string")

    # Check result contains expected date (basic sanity check)
    if test_date not in result:
        # Note: This is optional - some prompts might not include the date
        pass

    # Check minimum length (prompts should be substantial)
    if len(result) < 100:
        raise Exception(f"Prompt suspiciously short ({len(result)} chars) - expected >100")

    return True


if __name__ == "__main__":
    """
    Quick test of agent invocation with v3.0 baseline.
    Run: python evaluation/agent_invoker.py
    """
    print("="*80)
    print("AGENT INVOKER - Quick Validation Test")
    print("="*80)

    # Import v3.0 baseline prompt
    from backend.prompts.versions.researcher.v3_0 import get_researcher_prompt as get_v3_0_prompt

    # Validate prompt function
    print("\n1. Validating prompt function...")
    try:
        validate_prompt_function(get_v3_0_prompt)
        print("   ✓ Prompt function valid")
    except Exception as e:
        print(f"   ✗ Validation failed: {e}")
        exit(1)

    # Test single query
    print("\n2. Testing single query invocation...")
    test_query = "What are the latest developments in AI for 2025?"

    try:
        response = invoke_researcher_with_prompt(
            prompt_func=get_v3_0_prompt,
            query=test_query,
            config={"configurable": {"thread_id": "test_001"}}
        )
        print(f"   ✓ Query executed successfully")
        print(f"   ✓ Response length: {len(response)} chars")
        print(f"\n   Response preview:")
        print(f"   {response[:200]}...")
    except Exception as e:
        print(f"   ✗ Query failed: {e}")
        exit(1)

    print("\n" + "="*80)
    print("✓ Agent invoker validation complete!")
    print("="*80)
