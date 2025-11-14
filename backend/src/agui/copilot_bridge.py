# AG-UI to CopilotKit Bridge

import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import asyncio
from datetime import datetime

from .events import AGUIEvent, AGUIEventType
from .server import AGUIConnectionManager
from .tool_events import set_agui_manager
from ..agents.supervisor import Supervisor as GlobalSupervisorAgent
from ..mlflow.tracking import ATLASMLflowTracker
from ..tools.file_tool import initialize_session

logger = logging.getLogger(__name__)

class CopilotKitBridge:
    """Bridge between CopilotKit GraphQL runtime and AG-UI event system."""

    def __init__(self, agui_manager: AGUIConnectionManager):
        self.agui_manager = agui_manager
        self.active_agents: Dict[str, GlobalSupervisorAgent] = {}
        self.mlflow_tracker = ATLASMLflowTracker()

        # Set the global AG-UI manager for tool event broadcasting
        set_agui_manager(agui_manager)

    async def handle_copilot_action(self, request: Request) -> Response:
        """Handle CopilotKit action requests and translate to AG-UI events."""

        try:
            # Parse the CopilotKit request
            body = await request.json()

            # Extract action details
            action_name = body.get("action", "")
            parameters = body.get("parameters", {})
            task_id = request.headers.get("X-Task-ID", "default")

            logger.info(f"Received CopilotKit action: {action_name} for task {task_id}")

            # Handle different action types
            if action_name == "execute_task":
                return await self.execute_task(task_id, parameters)
            elif action_name == "execute_with_tools":
                return await self.execute_with_tools(task_id, parameters)
            elif action_name == "get_agent_status":
                return await self.get_agent_status(task_id)
            elif action_name == "cancel_task":
                return await self.cancel_task(task_id)
            else:
                return Response(
                    content=json.dumps({"error": f"Unknown action: {action_name}"}),
                    status_code=400
                )

        except Exception as e:
            logger.error(f"Error handling CopilotKit action: {e}")
            return Response(
                content=json.dumps({"error": str(e)}),
                status_code=500
            )

    async def execute_task(self, task_id: str, parameters: Dict[str, Any]) -> Response:
        """Execute a task through the agent hierarchy with streaming support."""

        query = parameters.get("query", "")

        if not query:
            return Response(
                content=json.dumps({"error": "Query is required"}),
                status_code=400
            )

        # Initialize session directory for file operations
        session_path = initialize_session(task_id)
        logger.info(f"Initialized session directory: {session_path}")

        # Create or get the supervisor agent
        if task_id not in self.active_agents:
            self.active_agents[task_id] = GlobalSupervisorAgent(
                task_id=task_id,
                mlflow_tracker=self.mlflow_tracker,
                agui_manager=self.agui_manager
            )

        supervisor = self.active_agents[task_id]

        # Start MLflow run
        self.mlflow_tracker.start_run(run_name=f"task_{task_id}")

        # Broadcast task started event
        await self.agui_manager.broadcast_to_task(
            task_id,
            AGUIEvent(
                event_type=AGUIEventType.TASK_STARTED,
                task_id=task_id,
                data={"query": query, "started_at": datetime.now().isoformat()}
            )
        )

        # Stream the response
        async def generate_response():
            try:
                # Stream from supervisor
                full_result = {"content": "", "tool_results": []}

                async for chunk in supervisor.send_message(query):
                    # Forward chunk to frontend
                    yield f"data: {json.dumps(chunk)}\n\n"

                    # Accumulate results
                    if chunk['type'] == 'content':
                        full_result['content'] += chunk['data']['content']
                    elif chunk['type'] == 'tool_result':
                        full_result['tool_results'].append(chunk['data'])

                # Broadcast completion
                await self.agui_manager.broadcast_to_task(
                    task_id,
                    AGUIEvent(
                        event_type=AGUIEventType.TASK_COMPLETED,
                        task_id=task_id,
                        data=full_result
                    )
                )

            except Exception as e:
                logger.error(f"Error executing task: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

                # Broadcast failure
                await self.agui_manager.broadcast_to_task(
                    task_id,
                    AGUIEvent(
                        event_type=AGUIEventType.TASK_FAILED,
                        task_id=task_id,
                        data={"error": str(e)}
                    )
                )
            finally:
                # End MLflow run
                self.mlflow_tracker.end_run()

        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    async def get_agent_status(self, task_id: str) -> Response:
        """Get the status of agents for a task."""

        if task_id not in self.active_agents:
            return Response(
                content=json.dumps({"status": "no_agents", "task_id": task_id}),
                status_code=200
            )

        supervisor = self.active_agents[task_id]

        # Get agent status from LangChain supervisor
        status = supervisor.get_status()

        return Response(
            content=json.dumps(status),
            status_code=200
        )

    async def execute_with_tools(self, task_id: str, parameters: Dict[str, Any]) -> Response:
        """Execute a task with specific tools and stream tool events."""

        query = parameters.get("query", "")
        preferred_tools = parameters.get("tools", [])

        if not query:
            return Response(
                content=json.dumps({"error": "Query is required"}),
                status_code=400
            )

        # Initialize session directory
        session_path = initialize_session(task_id)

        # Create or get the supervisor agent
        if task_id not in self.active_agents:
            self.active_agents[task_id] = GlobalSupervisorAgent(
                task_id=task_id,
                mlflow_tracker=self.mlflow_tracker,
                agui_manager=self.agui_manager
            )

        supervisor = self.active_agents[task_id]

        # Start MLflow run
        self.mlflow_tracker.start_run(run_name=f"task_{task_id}_tools")

        # Broadcast task started event with tool preferences
        await self.agui_manager.broadcast_to_task(
            task_id,
            AGUIEvent(
                event_type=AGUIEventType.TASK_STARTED,
                task_id=task_id,
                data={
                    "query": query,
                    "preferred_tools": preferred_tools,
                    "started_at": datetime.now().isoformat()
                }
            )
        )

        # Stream the response with tool events
        async def generate_response():
            try:
                # Note: Tool preferences are handled by the LLM's tool selection
                # The supervisor automatically calls the most appropriate tools

                # Stream from supervisor
                full_result = {"content": "", "tool_results": []}

                async for chunk in supervisor.send_message(query):
                    # Forward chunk to frontend
                    yield f"data: {json.dumps(chunk)}\n\n"

                    # Accumulate results
                    if chunk['type'] == 'content':
                        full_result['content'] += chunk['data']['content']
                    elif chunk['type'] == 'tool_result':
                        full_result['tool_results'].append(chunk['data'])

                # Broadcast completion
                await self.agui_manager.broadcast_to_task(
                    task_id,
                    AGUIEvent(
                        event_type=AGUIEventType.TASK_COMPLETED,
                        task_id=task_id,
                        data=full_result
                    )
                )

            except Exception as e:
                logger.error(f"Error executing task with tools: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

                # Broadcast failure
                await self.agui_manager.broadcast_to_task(
                    task_id,
                    AGUIEvent(
                        event_type=AGUIEventType.TASK_FAILED,
                        task_id=task_id,
                        data={"error": str(e)}
                    )
                )
            finally:
                # End MLflow run
                self.mlflow_tracker.end_run()

        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    async def cancel_task(self, task_id: str) -> Response:
        """Cancel a running task and clean up agents."""

        if task_id not in self.active_agents:
            return Response(
                content=json.dumps({"error": "Task not found"}),
                status_code=404
            )

        supervisor = self.active_agents[task_id]

        # Clean up agents (async)
        await supervisor.cleanup()

        # Remove from active agents
        del self.active_agents[task_id]

        # Broadcast cancellation
        await self.agui_manager.broadcast_to_task(
            task_id,
            AGUIEvent(
                event_type=AGUIEventType.TASK_CANCELLED,
                task_id=task_id,
                data={"cancelled_at": datetime.now().isoformat()}
            )
        )

        return Response(
            content=json.dumps({"status": "cancelled", "task_id": task_id}),
            status_code=200
        )

def setup_copilot_routes(app: FastAPI, agui_manager: AGUIConnectionManager):
    """Set up CopilotKit bridge routes on the FastAPI app."""

    bridge = CopilotKitBridge(agui_manager)

    @app.post("/api/copilotkit")
    async def copilot_endpoint(request: Request):
        """Main CopilotKit endpoint for GraphQL runtime."""
        return await bridge.handle_copilot_action(request)

    @app.get("/api/copilotkit/status/{task_id}")
    async def copilot_status(task_id: str):
        """Get agent status for a task."""
        return await bridge.get_agent_status(task_id)

    @app.post("/api/copilotkit/cancel/{task_id}")
    async def copilot_cancel(task_id: str):
        """Cancel a running task."""
        return await bridge.cancel_task(task_id)

    logger.info("CopilotKit bridge routes configured")