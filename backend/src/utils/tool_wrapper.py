"""
Tool wrapper utility for ensuring non-empty ToolMessage content.

This module provides defense-in-depth validation to prevent empty ToolMessage
content from being sent to LLMs (especially strict validators like Groq API).

The wrapper ensures that ALL tool returns (including Deep Agents built-in tools)
produce non-empty strings, preventing LangGraph's ToolNode from creating
ToolMessages with empty content.

All imports are ABSOLUTE.
"""

import logging
from typing import Any, Callable
from functools import wraps
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


def ensure_non_empty_return(tool_func: Callable) -> Callable:
    """
    Decorator to ensure tool functions never return empty strings.

    This wrapper validates tool return values and provides fallback content
    when tools return empty/None values. This prevents LangGraph's ToolNode
    from creating ToolMessages with empty content, which violates strict API
    requirements (e.g., Groq API).

    Args:
        tool_func: Tool function to wrap

    Returns:
        Wrapped function that guarantees non-empty return values

    Example:
        >>> @ensure_non_empty_return
        ... def my_tool(x: int) -> str:
        ...     return some_operation(x)
    """
    @wraps(tool_func)
    async def async_wrapper(*args, **kwargs):
        """Async wrapper for async tools"""
        try:
            result = await tool_func(*args, **kwargs)
            return _validate_result(result, tool_func.__name__)
        except Exception as e:
            logger.error(f"❌ Tool {tool_func.__name__} raised exception: {e}")
            return f"Error executing {tool_func.__name__}: {str(e) or 'Unknown error'}"

    @wraps(tool_func)
    def sync_wrapper(*args, **kwargs):
        """Sync wrapper for sync tools"""
        try:
            result = tool_func(*args, **kwargs)
            return _validate_result(result, tool_func.__name__)
        except Exception as e:
            logger.error(f"❌ Tool {tool_func.__name__} raised exception: {e}")
            return f"Error executing {tool_func.__name__}: {str(e) or 'Unknown error'}"

    # Return appropriate wrapper based on whether tool is async
    if hasattr(tool_func, '__call__') and hasattr(tool_func, '__code__'):
        import inspect
        if inspect.iscoroutinefunction(tool_func):
            return async_wrapper
    return sync_wrapper


def _validate_result(result: Any, tool_name: str) -> str:
    """
    Validate and fix tool result to ensure non-empty string.

    Args:
        result: Tool return value
        tool_name: Name of tool (for logging)

    Returns:
        Non-empty string result

    Validation Rules:
    1. If result is None → "Operation completed successfully"
    2. If result is empty string → "Operation completed successfully"
    3. If result is non-string → Convert to string
    4. If converted string is empty → "Operation returned: {type}"
    """
    # Handle None
    if result is None:
        logger.warning(f"⚠️  Tool {tool_name} returned None, using fallback")
        return f"Tool {tool_name} completed successfully"

    # Handle Command objects (from LangGraph)
    if hasattr(result, 'update'):
        # Command objects should not be stringified - return as-is
        return result

    # Convert to string if needed
    if not isinstance(result, str):
        result_str = str(result)
        logger.debug(f"Tool {tool_name} returned non-string ({type(result).__name__}), converted to string")
    else:
        result_str = result

    # Handle empty string
    if not result_str or result_str.strip() == "":
        logger.warning(f"⚠️  Tool {tool_name} returned empty string, using fallback")
        return f"Tool {tool_name} completed successfully"

    # Result is valid non-empty string
    return result_str


def wrap_tool(tool: BaseTool) -> BaseTool:
    """
    Wrap a LangChain tool to ensure non-empty returns.

    This function wraps the tool's internal function with validation logic.
    Use this for LangChain tools created with @tool decorator or Tool class.

    Args:
        tool: LangChain BaseTool instance

    Returns:
        Wrapped tool with validation

    Example:
        >>> from langchain_core.tools import tool
        >>> @tool
        ... def my_tool(x: int) -> str:
        ...     return process(x)
        >>>
        >>> wrapped_tool = wrap_tool(my_tool)
    """
    # Wrap the tool's _run and _arun methods
    if hasattr(tool, '_run'):
        original_run = tool._run
        tool._run = ensure_non_empty_return(original_run)

    if hasattr(tool, '_arun'):
        original_arun = tool._arun
        tool._arun = ensure_non_empty_return(original_arun)

    logger.debug(f"✅ Wrapped tool: {tool.name}")
    return tool


def wrap_tool_list(tools: list[BaseTool]) -> list[BaseTool]:
    """
    Wrap a list of tools to ensure non-empty returns.

    Convenience function for wrapping multiple tools at once.

    Args:
        tools: List of LangChain tools

    Returns:
        List of wrapped tools

    Example:
        >>> tools = [internet_search, execute_code, submit]
        >>> wrapped_tools = wrap_tool_list(tools)
    """
    logger.info(f"🔧 Wrapping {len(tools)} tools for non-empty validation")
    return [wrap_tool(tool) for tool in tools]


# Validation function for manual use
def validate_tool_output(output: Any, tool_name: str = "unknown") -> str:
    """
    Manually validate tool output (for use in tool implementations).

    Use this function inside tool implementations to validate return values
    before returning to LangGraph.

    Args:
        output: Tool output to validate
        tool_name: Name of tool (for logging)

    Returns:
        Validated non-empty string

    Example:
        >>> def my_tool(x: int) -> str:
        ...     result = process(x)
        ...     return validate_tool_output(result, "my_tool")
    """
    return _validate_result(output, tool_name)
