"""
Agent Invoker - Dynamic Graph Creation for Prompt Version Testing

Provides functions to invoke researcher agents with different prompt versions
for A/B testing and evaluation.

Based on test_config_1_deepagent_supervisor_command.py pattern but with
dynamic prompt injection instead of hardcoded benchmark_researcher_prompt.
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from typing import Callable, Dict, Any, List
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
from langchain_groq import ChatGroq
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


def create_researcher_agent_groq(
    prompt_func: Callable[[str], str],
    model_name: str = "moonshotai/kimi-k2-instruct-0905",
    temperature: float = TEMPERATURE
) -> StateGraph:
    """
    Create a researcher agent using Groq (for Kimi K2 and other Groq models).

    Uses ChatGroq with system prompt prepended as SystemMessage since create_agent
    doesn't support system_prompt parameter with Groq models.

    Args:
        prompt_func: Function that takes current_date and returns system prompt
        model_name: Groq model to use (default: moonshotai/kimi-k2-instruct-0905)
        temperature: Sampling temperature (default: 0.7)

    Returns:
        Configured researcher agent graph (StateGraph)

    Example:
        >>> from backend.prompts.versions.researcher.v3_1 import get_researcher_prompt
        >>> agent = create_researcher_agent_groq(get_researcher_prompt)
        >>> result = agent.invoke({"messages": [HumanMessage("Research AI trends")]})
    """
    from langchain_core.messages import SystemMessage

    # Get researcher tools (planning + research + files, NO delegation)
    researcher_tools = get_subagent_tools()

    # Get system prompt with current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    researcher_system_prompt = prompt_func(current_date)

    # Create base researcher agent WITHOUT system_prompt parameter
    # (Groq doesn't support system_prompt in create_agent)
    base_researcher_graph = create_agent(
        model=ChatGroq(model=model_name, temperature=temperature),
        tools=researcher_tools
    )

    # Create wrapper that prepends system message
    class GroqAgentWrapper:
        """Wrapper to prepend SystemMessage for Groq models"""
        def __init__(self, graph, system_prompt):
            self.graph = graph
            self.system_message = SystemMessage(content=system_prompt)

        def invoke(self, input_dict, config=None):
            # Prepend system message to user messages
            messages = input_dict.get("messages", [])
            messages_with_system = [self.system_message] + messages
            return self.graph.invoke({"messages": messages_with_system}, config)

    return GroqAgentWrapper(base_researcher_graph, researcher_system_prompt)


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


def invoke_researcher_with_prompt_groq(
    prompt_func: Callable[[str], str],
    query: str,
    model_name: str = "moonshotai/kimi-k2-instruct-0905",
    config: Dict[str, Any] = None
) -> str:
    """
    Invoke researcher agent using Groq with a specific prompt version on a single query.

    Identical to invoke_researcher_with_prompt() but uses ChatGroq instead of ChatGoogleGenerativeAI.

    Args:
        prompt_func: Prompt function from versioned prompt file
        query: Research query string
        model_name: Groq model to use (default: moonshotai/kimi-k2-instruct-0905)
        config: Optional LangGraph config dict with thread_id, recursion_limit, etc.

    Returns:
        Final response text from the researcher agent (string)

    Raises:
        Exception: If agent execution fails

    Example:
        >>> from backend.prompts.versions.researcher.v3_1 import get_researcher_prompt
        >>> response = invoke_researcher_with_prompt_groq(
        ...     prompt_func=get_researcher_prompt,
        ...     query="What are the latest developments in quantum computing?",
        ...     model_name="moonshotai/kimi-k2-instruct-0905",
        ...     config={"configurable": {"thread_id": "eval_kimi_k2_q001"}}
        ... )
    """
    # Create researcher agent with specified prompt and Groq model
    researcher_graph = create_researcher_agent_groq(prompt_func, model_name)

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


# ==============================================================================
# ASYNC INVOCATION (for parallel execution with asyncio)
# ==============================================================================

async def async_invoke_researcher_with_prompt(
    prompt_func: Callable[[str], str],
    query: str,
    config: Dict[str, Any] = None,
    semaphore: asyncio.Semaphore = None
) -> str:
    """
    Async version of invoke_researcher_with_prompt for parallel execution.

    Uses thread pool executor to run synchronous LangGraph invoke() without blocking.

    Args:
        prompt_func: Prompt function from versioned prompt file
        query: Research query string
        config: Optional LangGraph config dict
        semaphore: Optional semaphore to limit concurrency

    Returns:
        Final response text from the researcher agent

    Example:
        >>> import asyncio
        >>> async def run_parallel():
        ...     tasks = [async_invoke_researcher_with_prompt(get_v3_0_prompt, q) for q in queries]
        ...     results = await asyncio.gather(*tasks)
        ...     return results
        >>> asyncio.run(run_parallel())
    """
    # Use semaphore to limit concurrency if provided
    if semaphore:
        async with semaphore:
            return await _async_invoke_researcher(prompt_func, query, config)
    else:
        return await _async_invoke_researcher(prompt_func, query, config)


async def _async_invoke_researcher(
    prompt_func: Callable[[str], str],
    query: str,
    config: Dict[str, Any] = None
) -> str:
    """Internal async invocation - runs sync function in executor to avoid blocking."""
    loop = asyncio.get_event_loop()

    def _sync_invoke():
        return invoke_researcher_with_prompt(prompt_func, query, config)

    # Run sync function in thread pool executor (non-blocking)
    result = await loop.run_in_executor(None, _sync_invoke)
    return result


async def async_invoke_researcher_batch(
    prompt_func: Callable[[str], str],
    queries: List[str],
    max_concurrency: int = 10,
    verbose: bool = False
) -> List[str]:
    """
    Invoke researcher on multiple queries in parallel using asyncio.

    Dramatically faster than sequential execution - processes all queries concurrently
    with configurable concurrency limit to avoid overwhelming the API.

    Args:
        prompt_func: Prompt function from versioned prompt file
        queries: List of query strings
        max_concurrency: Maximum number of concurrent requests (default: 10)
        verbose: Print progress messages

    Returns:
        List of response strings (same order as queries)

    Example:
        >>> import asyncio
        >>> from backend.prompts.versions.researcher.v3_0 import get_researcher_prompt
        >>> from evaluation.test_suite import get_test_suite
        >>>
        >>> async def main():
        ...     test_suite = get_test_suite()
        ...     queries = [q.query for q in test_suite]  # All 32 queries
        ...     responses = await async_invoke_researcher_batch(
        ...         get_researcher_prompt, queries, max_concurrency=10, verbose=True
        ...     )
        ...     print(f"Completed {len(responses)} queries")
        >>>
        >>> asyncio.run(main())
    """
    if verbose:
        print(f"\nRunning {len(queries)} queries in parallel (max concurrency: {max_concurrency})")
        print(f"{'='*80}\n")

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrency)

    # Create tasks for all queries
    tasks = []
    for i, query in enumerate(queries):
        config = {
            "configurable": {"thread_id": f"async_batch_{i}_{hash(query)}"},
            "recursion_limit": RECURSION_LIMIT
        }

        task = async_invoke_researcher_with_prompt(
            prompt_func=prompt_func,
            query=query,
            config=config,
            semaphore=semaphore
        )
        tasks.append(task)

    # Execute all tasks in parallel with gather (preserves order)
    try:
        if verbose:
            print("Starting parallel execution...")

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error strings
        responses_processed = []
        errors = 0
        for i, r in enumerate(responses):
            if isinstance(r, Exception):
                error_msg = f"ERROR: {str(r)}"
                responses_processed.append(error_msg)
                errors += 1
                if verbose:
                    print(f"  [{i+1}/{len(queries)}] ✗ Failed: {str(r)}")
            else:
                responses_processed.append(r)
                if verbose:
                    print(f"  [{i+1}/{len(queries)}] ✓ Completed ({len(r)} chars)")

        if verbose:
            print(f"\n{'='*80}")
            print(f"✓ Batch complete: {len(responses_processed)} responses")
            if errors > 0:
                print(f"⚠ {errors} queries failed")
            print(f"{'='*80}\n")

        return responses_processed

    except Exception as e:
        if verbose:
            print(f"\n✗ Batch failed: {str(e)}")
        raise


async def async_invoke_researcher_batch_groq(
    prompt_func: Callable[[str], str],
    queries: List[str],
    model_name: str = "moonshotai/kimi-k2-instruct-0905",
    max_concurrency: int = 10,
    verbose: bool = False
) -> List[str]:
    """
    Invoke researcher on multiple queries in parallel using asyncio with Groq (Kimi K2).

    Identical to async_invoke_researcher_batch() but uses ChatGroq instead of ChatGoogleGenerativeAI.

    Args:
        prompt_func: Prompt function from versioned prompt file
        queries: List of query strings
        model_name: Groq model to use (default: moonshotai/kimi-k2-instruct-0905)
        max_concurrency: Maximum number of concurrent requests (default: 10)
        verbose: Print progress messages

    Returns:
        List of response strings (same order as queries)

    Example:
        >>> import asyncio
        >>> from backend.prompts.versions.researcher.v3_1 import get_researcher_prompt
        >>> from evaluation.test_suite import get_test_suite
        >>>
        >>> async def main():
        ...     test_suite = get_test_suite()
        ...     queries = [q.query for q in test_suite]  # All 32 queries
        ...     responses = await async_invoke_researcher_batch_groq(
        ...         get_researcher_prompt, queries,
        ...         model_name="moonshotai/kimi-k2-instruct-0905",
        ...         max_concurrency=5, verbose=True
        ...     )
        ...     print(f"Completed {len(responses)} queries")
        >>>
        >>> asyncio.run(main())
    """
    if verbose:
        print(f"\nRunning {len(queries)} queries in parallel (max concurrency: {max_concurrency})")
        print(f"Model: {model_name}")
        print(f"{'='*80}\n")

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrency)

    # Create tasks for all queries
    async def _invoke_with_semaphore(query: str, index: int) -> str:
        """Wrapper to invoke with semaphore and model_name."""
        async with semaphore:
            loop = asyncio.get_event_loop()
            config = {
                "configurable": {"thread_id": f"async_groq_{index}_{hash(query)}"},
                "recursion_limit": RECURSION_LIMIT
            }

            def _sync_invoke():
                return invoke_researcher_with_prompt_groq(prompt_func, query, model_name, config)

            result = await loop.run_in_executor(None, _sync_invoke)
            return result

    tasks = [_invoke_with_semaphore(query, i) for i, query in enumerate(queries)]

    # Execute all tasks in parallel with gather (preserves order)
    try:
        if verbose:
            print("Starting parallel execution...")

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error strings
        responses_processed = []
        errors = 0
        for i, r in enumerate(responses):
            if isinstance(r, Exception):
                error_msg = f"ERROR: {str(r)}"
                responses_processed.append(error_msg)
                errors += 1
                if verbose:
                    print(f"  [{i+1}/{len(queries)}] ✗ Failed: {str(r)}")
            else:
                responses_processed.append(r)
                if verbose:
                    print(f"  [{i+1}/{len(queries)}] ✓ Completed ({len(r)} chars)")

        if verbose:
            print(f"\n{'='*80}")
            print(f"✓ Batch complete: {len(responses_processed)} responses")
            if errors > 0:
                print(f"⚠ {errors} queries failed")
            print(f"{'='*80}\n")

        return responses_processed

    except Exception as e:
        if verbose:
            print(f"\n✗ Batch failed: {str(e)}")
        raise


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
