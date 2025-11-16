"""
Subagent Event Emitter - Real-time execution visibility via WebSocket
=====================================================================

This module provides event emission functionality for subagent execution,
enabling real-time visibility into subagent activities (reasoning, tool calls,
results) that are normally invisible to the frontend.

Architecture:
- Emits WebSocket events for subagent execution steps
- Event types mirror supervisor's SSE events (llm_thinking, tool_call, tool_result)
- Broadcasts via existing WebSocket manager to /ws/plan endpoint
- Frontend receives events and displays in SubagentActivityPanel

Usage:
    from subagents.event_emitter import emit_subagent_event

    # Emit reasoning event
    await emit_subagent_event(
        parent_thread_id="main-thread-123",
        subagent_thread_id="main-thread-123/subagent-researcher-uuid",
        subagent_type="researcher",
        event_type="llm_thinking",
        data={"content": "I'll search for AI trends..."}
    )

    # Emit tool call event
    await emit_subagent_event(
        parent_thread_id="main-thread-123",
        subagent_thread_id="main-thread-123/subagent-researcher-uuid",
        subagent_type="researcher",
        event_type="tool_call",
        data={"tool_name": "tavily_search", "tool_args": {"query": "AI trends 2025"}}
    )
"""

import json
import time
import logging
from typing import Dict, Any, Literal
from enum import Enum

# Configure logger
logger = logging.getLogger(__name__)

# Event type definitions - mirror supervisor SSE event types
SubagentEventType = Literal[
    "llm_thinking",      # Agent reasoning/thinking
    "tool_call",         # Tool invocation
    "tool_result",       # Tool execution result
    "llm_response",      # Agent final response
    "progress_log",      # Custom progress message
    "error"              # Error during execution
]


class SubagentType(str, Enum):
    """Enum of supported subagent types."""
    RESEARCHER = "researcher"
    DATA_SCIENTIST = "data_scientist"
    EXPERT_ANALYST = "expert_analyst"
    WRITER = "writer"
    REVIEWER = "reviewer"


async def emit_subagent_event(
    parent_thread_id: str,
    subagent_thread_id: str,
    subagent_type: str,
    event_type: SubagentEventType,
    data: Dict[str, Any]
) -> None:
    """
    Emit subagent execution event via WebSocket.

    Broadcasts a subagent execution event to all connected WebSocket clients
    listening on the /ws/plan endpoint. Events are received by the frontend
    and displayed in the SubagentActivityPanel.

    Args:
        parent_thread_id: ID of parent supervisor thread
        subagent_thread_id: Unique ID of subagent thread (includes subagent type + UUID)
        subagent_type: Type of subagent (researcher, writer, etc.)
        event_type: Type of event being emitted
        data: Event-specific data payload

    Event Structure:
        {
            "type": "subagent_execution",
            "parent_thread_id": "main-thread-123",
            "subagent_thread_id": "main-thread-123/subagent-researcher-uuid",
            "subagent_type": "researcher",
            "event_type": "llm_thinking",
            "data": {"content": "I'll search for..."},
            "timestamp": 1699999999.123
        }

    Examples:
        # Thinking event
        await emit_subagent_event(
            "thread-123", "thread-123/subagent-researcher-001",
            "researcher", "llm_thinking",
            {"content": "I'll search for AI trends in 2025..."}
        )

        # Tool call event
        await emit_subagent_event(
            "thread-123", "thread-123/subagent-researcher-001",
            "researcher", "tool_call",
            {"tool_name": "tavily_search", "tool_args": {"query": "AI 2025"}}
        )

        # Tool result event
        await emit_subagent_event(
            "thread-123", "thread-123/subagent-researcher-001",
            "researcher", "tool_result",
            {"tool_name": "tavily_search", "result": "[7 sources found]"}
        )

        # Final response event
        await emit_subagent_event(
            "thread-123", "thread-123/subagent-researcher-001",
            "researcher", "llm_response",
            {"content": "Research completed. Report written to /workspace/trends.md"}
        )

        # Error event
        await emit_subagent_event(
            "thread-123", "thread-123/subagent-researcher-001",
            "researcher", "error",
            {"error": "API rate limit exceeded", "details": "..."}
        )
    """
    try:
        # Import here to avoid circular dependency
        from websocket_manager import manager

        # Construct event payload
        event = {
            "type": "subagent_execution",
            "parent_thread_id": parent_thread_id,
            "subagent_thread_id": subagent_thread_id,
            "subagent_type": subagent_type,
            "event_type": event_type,
            "data": data,
            "timestamp": time.time()
        }

        # Broadcast to all WebSocket clients
        await manager.broadcast(json.dumps(event))

        logger.debug(
            f"[SUBAGENT EVENT] {subagent_type} | {event_type} | "
            f"thread={subagent_thread_id[:40]}... | data_keys={list(data.keys())}"
        )

    except Exception as e:
        # Event emission should never break subagent execution
        # Log error and continue
        logger.error(
            f"[SUBAGENT EVENT ERROR] Failed to emit {event_type} for {subagent_type}: {e}",
            exc_info=True
        )


async def emit_subagent_thinking(
    parent_thread_id: str,
    subagent_thread_id: str,
    subagent_type: str,
    content: str
) -> None:
    """
    Convenience function to emit llm_thinking event.

    Args:
        parent_thread_id: Parent thread ID
        subagent_thread_id: Subagent thread ID
        subagent_type: Type of subagent
        content: Thinking/reasoning content
    """
    await emit_subagent_event(
        parent_thread_id,
        subagent_thread_id,
        subagent_type,
        "llm_thinking",
        {"content": content}
    )


async def emit_subagent_tool_call(
    parent_thread_id: str,
    subagent_thread_id: str,
    subagent_type: str,
    tool_name: str,
    tool_args: Dict[str, Any]
) -> None:
    """
    Convenience function to emit tool_call event.

    Args:
        parent_thread_id: Parent thread ID
        subagent_thread_id: Subagent thread ID
        subagent_type: Type of subagent
        tool_name: Name of tool being called
        tool_args: Arguments passed to tool
    """
    await emit_subagent_event(
        parent_thread_id,
        subagent_thread_id,
        subagent_type,
        "tool_call",
        {"tool_name": tool_name, "tool_args": tool_args}
    )


async def emit_subagent_tool_result(
    parent_thread_id: str,
    subagent_thread_id: str,
    subagent_type: str,
    tool_name: str,
    result: str
) -> None:
    """
    Convenience function to emit tool_result event.

    Args:
        parent_thread_id: Parent thread ID
        subagent_thread_id: Subagent thread ID
        subagent_type: Type of subagent
        tool_name: Name of tool that was called
        result: Tool execution result
    """
    await emit_subagent_event(
        parent_thread_id,
        subagent_thread_id,
        subagent_type,
        "tool_result",
        {"tool_name": tool_name, "result": result}
    )


async def emit_subagent_response(
    parent_thread_id: str,
    subagent_thread_id: str,
    subagent_type: str,
    content: str
) -> None:
    """
    Convenience function to emit llm_response event.

    Args:
        parent_thread_id: Parent thread ID
        subagent_thread_id: Subagent thread ID
        subagent_type: Type of subagent
        content: Final response content
    """
    await emit_subagent_event(
        parent_thread_id,
        subagent_thread_id,
        subagent_type,
        "llm_response",
        {"content": content}
    )


async def emit_subagent_progress(
    parent_thread_id: str,
    subagent_thread_id: str,
    subagent_type: str,
    message: str,
    done: bool = False
) -> None:
    """
    Convenience function to emit progress_log event.

    Args:
        parent_thread_id: Parent thread ID
        subagent_thread_id: Subagent thread ID
        subagent_type: Type of subagent
        message: Progress message
        done: Whether this is the final progress message
    """
    await emit_subagent_event(
        parent_thread_id,
        subagent_thread_id,
        subagent_type,
        "progress_log",
        {"message": message, "done": done}
    )


async def emit_subagent_error(
    parent_thread_id: str,
    subagent_thread_id: str,
    subagent_type: str,
    error: str,
    details: str = ""
) -> None:
    """
    Convenience function to emit error event.

    Args:
        parent_thread_id: Parent thread ID
        subagent_thread_id: Subagent thread ID
        subagent_type: Type of subagent
        error: Error message
        details: Additional error details
    """
    await emit_subagent_event(
        parent_thread_id,
        subagent_thread_id,
        subagent_type,
        "error",
        {"error": error, "details": details}
    )
