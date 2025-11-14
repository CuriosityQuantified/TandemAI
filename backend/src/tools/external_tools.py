"""
External tools for ATLAS agents.
All tools are ASYNC by default for parallel execution.

All imports are ABSOLUTE.
"""

import os
import asyncio
from typing import Literal, Dict, Any
from tavily import AsyncTavilyClient
from e2b_code_interpreter import Sandbox
from langchain_core.tools import tool


# Lazy initialize Tavily client (will be created when needed)
tavily_client = None


def _get_tavily_client() -> AsyncTavilyClient:
    """Get or create Tavily client instance."""
    global tavily_client
    if tavily_client is None:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        tavily_client = AsyncTavilyClient(api_key=api_key)
    return tavily_client


@tool
async def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
) -> str:
    """
    Search the web for current information using Tavily API.

    ⚠️  REQUIRED FIELD: query
        You MUST provide the `query` parameter or the tool will fail.

        Correct:   internet_search(query="renewable energy benefits")
        Incorrect: internet_search("renewable energy benefits")
        Incorrect: internet_search()

    WHEN TO USE:
    - Finding current events, facts, statistics, or data
    - Researching topics with multiple sources
    - Verifying information from authoritative sources

    WHEN NOT TO USE:
    - After you have sufficient information
    - DO NOT repeat similar queries
    - STOP once you have enough data

    USAGE:
    internet_search(query="climate change impacts 2024")
    internet_search(query="Python async tutorial", max_results=10)
    internet_search(query="AI news", topic="news")

    PARAMETERS:
    - query (str): REQUIRED - your search query (must use parameter name)
    - max_results (int): results to return (default: 5, max: 20)
    - topic (str): "general" (default), "news", or "finance"
    - include_raw_content (bool): include full page text (default: False)

    RETURNS:
    Formatted string with search results including direct answer and source citations.

    CORRECT USAGE EXAMPLES:
    ✅ internet_search(query="S&P 500 return October 2025")
    ✅ internet_search(query="climate change", max_results=10)
    ✅ internet_search(query="tech news", topic="news")

    INCORRECT USAGE (WILL FAIL):
    ❌ internet_search("S&P 500")  # Missing query= parameter name
    ❌ internet_search()  # No query provided
    ❌ internet_search(search="climate")  # Wrong parameter name

    TERMINATION: Once you have sufficient information, stop searching and provide your final answer with citations.
    """
    if not os.environ.get("TAVILY_API_KEY"):
        return f"ERROR: TAVILY_API_KEY not configured. Please add TAVILY_API_KEY to your .env file.\n\nQuery: {query}"

    try:
        client = _get_tavily_client()
        results = await client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic,
        )

        # Format as readable string
        output = f"Search Results for: '{query}'\n"
        output += "=" * 60 + "\n\n"

        # Add direct answer if available
        answer = results.get("answer", "")
        if answer:
            output += f"DIRECT ANSWER:\n{answer}\n\n"

        # Add sources
        sources = results.get("results", [])
        if sources:
            output += f"SOURCES ({len(sources)} results):\n\n"
            for i, source in enumerate(sources, 1):
                title = source.get("title", "Untitled")
                url = source.get("url", "")
                content = source.get("content", "")[:200]  # First 200 chars

                output += f"{i}. {title}\n"
                output += f"   URL: {url}\n"
                if content:
                    output += f"   Preview: {content}...\n"
                output += "\n"
        else:
            output += "No sources found.\n"

        return output

    except Exception as e:
        return f"ERROR: Search failed for query '{query}'\n\nError details: {str(e)}"


@tool
async def execute_python_code(code: str, timeout: int = 30) -> str:
    """
    Execute Python code safely in isolated E2B sandbox.

    ⚠️  REQUIRED: `code` parameter - Python code as string

    WHEN TO USE:
    - Data analysis, calculations, visualizations
    - Processing data, running algorithms
    - Testing code snippets

    WHEN NOT TO USE:
    - Simple arithmetic
    - Web scraping (use internet_search)

    ENVIRONMENT:
    - Jupyter-like notebook (cell-based execution)
    - Isolated sandbox (no access to user filesystem)
    - Pre-installed: pandas, numpy, matplotlib, scikit-learn, scipy
    - Timeout: default 30s, max 300s

    USAGE:
    code = "import math; math.factorial(10)"
    result = await execute_python_code(code)

    Multi-line code:
    code = '''
    import pandas as pd
    data = pd.DataFrame({'x': [1,2,3], 'y': [4,5,6]})
    data.describe()  # Last expression is returned
    '''
    result = await execute_python_code(code, timeout=60)

    PARAMETERS:
    - code (str): REQUIRED - Python code to execute (last expression returned)
    - timeout (int): max execution time in seconds (default: 30, max: 300)

    RETURNS:
    Formatted string with execution results including status, output, and result value.

    NOTES:
    - Each execution is independent (no state persists)
    - Use print() for intermediate output, last line for final result
    - Include all related computations in one code block
    """
    if not os.environ.get("E2B_API_KEY"):
        return "ERROR: E2B_API_KEY not configured. Please add E2B_API_KEY to your .env file."

    # Validate timeout
    if timeout > 300:
        return "ERROR: Timeout exceeds maximum of 300 seconds"

    try:
        # Run in thread pool to avoid blocking event loop
        result_dict = await asyncio.to_thread(_execute_code_sync, code, timeout)

        # Format as readable string
        output = "Python Code Execution Results\n"
        output += "=" * 60 + "\n\n"

        status = result_dict.get("status", "unknown")
        output += f"STATUS: {status.upper()}\n\n"

        # Add stdout if present
        stdout = result_dict.get("stdout", "")
        if stdout:
            output += "STDOUT:\n"
            output += stdout + "\n\n"

        # Add stderr if present
        stderr = result_dict.get("stderr", "")
        if stderr:
            output += "STDERR:\n"
            output += stderr + "\n\n"

        # Add result if present
        result_value = result_dict.get("result")
        if result_value:
            output += "RESULT:\n"
            output += str(result_value) + "\n\n"

        # Add error if present
        error = result_dict.get("error")
        if error:
            output += "ERROR:\n"
            output += error + "\n"

        return output.strip()

    except Exception as e:
        return f"ERROR: Execution failed\n\nError details: {str(e)}"


def _execute_code_sync(code: str, timeout: int) -> Dict[str, Any]:
    """
    Synchronous helper for code execution.

    Called from async context via asyncio.to_thread to prevent
    blocking the event loop during code execution.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds

    Returns:
        Dictionary with execution results
    """
    try:
        with Sandbox(api_key=os.environ["E2B_API_KEY"], template="base") as sandbox:
            # Execute code in Jupyter-like notebook cell
            execution = sandbox.notebook.exec_cell(code, timeout=timeout)

            # Extract results
            stdout = execution.logs.stdout if execution.logs else ""
            stderr = execution.logs.stderr if execution.logs else ""
            results = execution.results if execution.results else []
            error = execution.error if execution.error else None

            # Format results
            result_str = None
            if results:
                # Get last result (mimics Jupyter behavior)
                result_str = str(results[-1])

            return {
                "status": "error" if error else "success",
                "stdout": stdout,
                "stderr": stderr,
                "result": result_str,
                "error": str(error) if error else None,
                "logs": f"{stdout}\n{stderr}".strip(),
            }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Sandbox execution failed: {str(e)}",
            "stdout": "",
            "stderr": "",
            "result": None,
            "logs": "",
        }
