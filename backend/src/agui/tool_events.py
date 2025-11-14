"""
Tool Event Broadcasting for AG-UI
Provides decorators and utilities for automatic tool execution tracking
"""

import asyncio
import functools
import json
import time
import traceback
from typing import Any, Dict, Optional, Callable, Awaitable
from datetime import datetime
import logging
import hashlib

from .events import AGUIEvent, AGUIEventType
from .server import AGUIConnectionManager

logger = logging.getLogger(__name__)


class ToolEventBroadcaster:
    """Manages tool event broadcasting to AG-UI clients."""

    def __init__(self, agui_manager: Optional[AGUIConnectionManager] = None):
        """
        Initialize the tool event broadcaster.

        Args:
            agui_manager: AG-UI connection manager for broadcasting events
        """
        self.agui_manager = agui_manager
        self.active_tools: Dict[str, Dict[str, Any]] = {}

    def set_agui_manager(self, agui_manager: AGUIConnectionManager):
        """Set or update the AG-UI connection manager."""
        self.agui_manager = agui_manager

    async def broadcast_tool_event(self,
                                  task_id: str,
                                  tool_name: str,
                                  event_type: str,
                                  data: Dict[str, Any],
                                  agent_id: Optional[str] = None):
        """
        Broadcast a tool event to AG-UI clients.

        Args:
            task_id: Task identifier
            tool_name: Name of the tool
            event_type: Type of event (started/progress/completed/failed)
            data: Event data
            agent_id: Optional agent identifier
        """
        if not self.agui_manager:
            logger.warning(f"AG-UI manager not set, cannot broadcast {event_type} for {tool_name}")
            return

        event = AGUIEvent(
            event_type=f"tool_{event_type}",
            task_id=task_id,
            agent_id=agent_id,
            data={
                "tool_name": tool_name,
                "timestamp": datetime.now().isoformat(),
                **data
            }
        )

        try:
            await self.agui_manager.broadcast_to_task(task_id, event)
            logger.debug(f"Broadcasted tool_{event_type} for {tool_name} on task {task_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast tool event: {e}")

    def track_tool(self,
                   tool_name: str,
                   task_id: Optional[str] = None,
                   agent_id: Optional[str] = None,
                   capture_result: bool = True,
                   capture_params: bool = True,
                   track_progress: bool = False):
        """
        Decorator for tracking tool execution with AG-UI events.

        Args:
            tool_name: Name of the tool being tracked
            task_id: Optional task ID (can be extracted from context)
            agent_id: Optional agent ID
            capture_result: Whether to include result in completion event
            capture_params: Whether to include parameters in start event
            track_progress: Whether to emit progress events

        Returns:
            Decorated function with automatic event broadcasting
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Extract task_id from kwargs if not provided
                effective_task_id = task_id or kwargs.get('task_id', 'default')
                tool_call_id = self._generate_tool_call_id(tool_name, effective_task_id)

                # Record start time
                start_time = time.time()

                # Prepare parameters for broadcasting
                params_data = {}
                if capture_params:
                    params_data = self._sanitize_params(kwargs)

                # Store active tool info
                self.active_tools[tool_call_id] = {
                    'tool_name': tool_name,
                    'task_id': effective_task_id,
                    'agent_id': agent_id,
                    'started_at': datetime.now().isoformat(),
                    'parameters': params_data
                }

                # Broadcast tool started event
                await self.broadcast_tool_event(
                    task_id=effective_task_id,
                    tool_name=tool_name,
                    event_type="started",
                    data={
                        "tool_call_id": tool_call_id,
                        "parameters": params_data
                    },
                    agent_id=agent_id
                )

                try:
                    # Execute the tool function
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                    # Calculate execution time
                    execution_time = time.time() - start_time

                    # Prepare result data
                    result_data = {
                        "tool_call_id": tool_call_id,
                        "execution_time_seconds": execution_time,
                        "status": "success"
                    }

                    if capture_result:
                        result_data["result"] = self._sanitize_result(result)

                    # Broadcast tool completed event
                    await self.broadcast_tool_event(
                        task_id=effective_task_id,
                        tool_name=tool_name,
                        event_type="completed",
                        data=result_data,
                        agent_id=agent_id
                    )

                    # Clean up active tool
                    self.active_tools.pop(tool_call_id, None)

                    return result

                except Exception as e:
                    # Calculate execution time
                    execution_time = time.time() - start_time

                    # Prepare error data
                    error_data = {
                        "tool_call_id": tool_call_id,
                        "execution_time_seconds": execution_time,
                        "status": "failed",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "traceback": traceback.format_exc()
                    }

                    # Broadcast tool failed event
                    await self.broadcast_tool_event(
                        task_id=effective_task_id,
                        tool_name=tool_name,
                        event_type="failed",
                        data=error_data,
                        agent_id=agent_id
                    )

                    # Clean up active tool
                    self.active_tools.pop(tool_call_id, None)

                    # Re-raise the exception
                    raise

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For synchronous functions, handle existing event loops
                try:
                    loop = asyncio.get_running_loop()
                    # If there's already a running loop (e.g., in pytest-asyncio),
                    # create a task instead of trying to run_until_complete
                    task = loop.create_task(async_wrapper(*args, **kwargs))
                    # Return a coroutine that can be awaited
                    return asyncio.ensure_future(task)
                except RuntimeError:
                    # No running loop, create one
                    loop = asyncio.get_event_loop()
                    return loop.run_until_complete(async_wrapper(*args, **kwargs))

            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def track_progress(self,
                      tool_call_id: str,
                      progress: float,
                      message: Optional[str] = None,
                      data: Optional[Dict[str, Any]] = None):
        """
        Emit a progress event for an active tool.

        Args:
            tool_call_id: Unique identifier for the tool call
            progress: Progress percentage (0-100)
            message: Optional progress message
            data: Optional additional data
        """
        if tool_call_id not in self.active_tools:
            logger.warning(f"Tool call {tool_call_id} not found in active tools")
            return

        tool_info = self.active_tools[tool_call_id]

        progress_data = {
            "tool_call_id": tool_call_id,
            "progress_percentage": min(100, max(0, progress)),
            "message": message
        }

        if data:
            progress_data.update(data)

        # Create async task for broadcasting
        asyncio.create_task(
            self.broadcast_tool_event(
                task_id=tool_info['task_id'],
                tool_name=tool_info['tool_name'],
                event_type="progress",
                data=progress_data,
                agent_id=tool_info.get('agent_id')
            )
        )

    def _generate_tool_call_id(self, tool_name: str, task_id: str) -> str:
        """Generate a unique identifier for a tool call."""
        timestamp = str(time.time())
        hash_input = f"{tool_name}_{task_id}_{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]

    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize parameters for broadcasting (remove sensitive data, large objects).

        Args:
            params: Raw parameters dictionary

        Returns:
            Sanitized parameters safe for broadcasting
        """
        sanitized = {}

        for key, value in params.items():
            # Skip sensitive keys
            if any(sensitive in key.lower() for sensitive in ['password', 'token', 'key', 'secret']):
                sanitized[key] = "***REDACTED***"
                continue

            # Handle different value types
            if isinstance(value, (str, int, float, bool, type(None))):
                sanitized[key] = value
            elif isinstance(value, (list, tuple)):
                # Limit array size
                if len(value) > 10:
                    sanitized[key] = f"[{len(value)} items]"
                else:
                    sanitized[key] = value[:10]
            elif isinstance(value, dict):
                # Recursively sanitize nested dicts
                if len(value) > 20:
                    sanitized[key] = f"{{dict with {len(value)} keys}}"
                else:
                    sanitized[key] = self._sanitize_params(value)
            else:
                # For other types, just use string representation
                sanitized[key] = str(type(value))

        return sanitized

    def _sanitize_result(self, result: Any) -> Any:
        """
        Sanitize result for broadcasting (truncate large responses).

        Args:
            result: Raw result from tool execution

        Returns:
            Sanitized result safe for broadcasting
        """
        if result is None:
            return None

        # Handle string results
        if isinstance(result, str):
            if len(result) > 5000:
                return f"{result[:5000]}... [truncated {len(result) - 5000} characters]"
            return result

        # Handle dict results
        if isinstance(result, dict):
            # Check for special keys that indicate large data
            if 'results' in result and isinstance(result['results'], list):
                if len(result['results']) > 10:
                    truncated = result.copy()
                    truncated['results'] = result['results'][:10]
                    truncated['_truncated'] = True
                    truncated['_total_results'] = len(result['results'])
                    return truncated

            # Recursively sanitize nested structures
            return {k: self._sanitize_result(v) for k, v in result.items()}

        # Handle list results
        if isinstance(result, (list, tuple)):
            if len(result) > 20:
                return list(result[:20]) + [f"... and {len(result) - 20} more items"]
            return result

        # For other types, convert to string if reasonable size
        result_str = str(result)
        if len(result_str) > 5000:
            return f"{result_str[:5000]}... [truncated]"

        return result


# Global tool event broadcaster instance
_tool_broadcaster = ToolEventBroadcaster()


def broadcast_tool_call(tool_name: str,
                        task_id: Optional[str] = None,
                        agent_id: Optional[str] = None,
                        **kwargs):
    """
    Convenience decorator for tracking tool calls.

    Usage:
        @broadcast_tool_call("web_search", capture_result=True)
        async def search_web(query: str, task_id: str):
            # Tool implementation
            return results
    """
    return _tool_broadcaster.track_tool(tool_name, task_id, agent_id, **kwargs)


def set_agui_manager(agui_manager: AGUIConnectionManager):
    """Set the global AG-UI manager for tool broadcasting."""
    _tool_broadcaster.set_agui_manager(agui_manager)


def emit_progress(tool_call_id: str, progress: float, message: Optional[str] = None):
    """
    Emit a progress event for the currently executing tool.

    Args:
        tool_call_id: Tool call identifier
        progress: Progress percentage (0-100)
        message: Optional status message
    """
    _tool_broadcaster.track_progress(tool_call_id, progress, message)


# Export public API
__all__ = [
    'ToolEventBroadcaster',
    'broadcast_tool_call',
    'set_agui_manager',
    'emit_progress'
]