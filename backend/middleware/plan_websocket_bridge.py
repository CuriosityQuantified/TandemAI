"""
WebSocket Bridge for Planning Agent

This middleware intercepts LangGraph custom events and broadcasts them
via WebSocket to connected frontend clients for real-time plan updates.
"""

import time
import asyncio
from typing import AsyncGenerator, Any, Dict
from websocket_manager import manager


async def stream_agent_with_websocket_updates(
    agent_stream: AsyncGenerator,
    thread_id: str,
    request_id: str = None
) -> AsyncGenerator:
    """
    Wrap agent stream to automatically broadcast plan events via WebSocket.

    This function acts as middleware between the LangGraph agent and the client,
    intercepting custom events (plan updates) and broadcasting them to all
    connected WebSocket clients while still yielding events to the caller.

    Args:
        agent_stream: AsyncGenerator from LangGraph app.astream()
        thread_id: Unique thread ID for this conversation/plan
        request_id: Optional request ID for correlation

    Yields:
        Original events from agent_stream

    Example:
        async for event in stream_agent_with_websocket_updates(
            app.astream(inputs, config, stream_mode=["updates", "custom"]),
            thread_id="abc123"
        ):
            # Process event
            pass
    """
    async for event in agent_stream:
        # Check if this is a custom event (plan update)
        if isinstance(event, tuple) and len(event) >= 2:
            event_type, event_data = event[0], event[1]

            if event_type == "custom" and isinstance(event_data, dict):
                # Extract event details
                plan_event_type = event_data.get("type")

                # Build WebSocket message
                ws_message = {
                    "type": "agent_event",
                    "event_type": plan_event_type,
                    "thread_id": thread_id,
                    "data": event_data,
                    "timestamp": time.time()
                }

                # Add request ID if provided
                if request_id:
                    ws_message["request_id"] = request_id

                # Broadcast to all connected clients
                # Note: You could filter by file/room if needed
                try:
                    await manager.broadcast(ws_message)
                except Exception as e:
                    # Don't fail the stream if broadcast fails
                    print(f"WebSocket broadcast error: {e}")

        # Always yield the original event
        yield event


async def broadcast_plan_state(plan_state: Dict[str, Any], thread_id: str):
    """
    Broadcast current plan state to WebSocket clients.

    Useful for initial state sync or manual state updates.

    Args:
        plan_state: Dictionary containing plan, progress, etc.
        thread_id: Thread ID for this plan

    Example:
        await broadcast_plan_state({
            "plan_id": "xyz",
            "plan": ["step1", "step2"],
            "current_step": 0,
            "progress": 0.0
        }, thread_id="abc123")
    """
    message = {
        "type": "plan_state_update",
        "thread_id": thread_id,
        "state": plan_state,
        "timestamp": time.time()
    }

    try:
        await manager.broadcast(message)
    except Exception as e:
        print(f"Failed to broadcast plan state: {e}")


async def send_plan_error(error_message: str, thread_id: str, request_id: str = None):
    """
    Send plan error notification via WebSocket.

    Args:
        error_message: Human-readable error message
        thread_id: Thread ID where error occurred
        request_id: Optional request ID for correlation
    """
    message = {
        "type": "plan_error",
        "thread_id": thread_id,
        "error": error_message,
        "timestamp": time.time()
    }

    if request_id:
        message["request_id"] = request_id

    try:
        await manager.broadcast(message)
    except Exception as e:
        print(f"Failed to send plan error: {e}")
