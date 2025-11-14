"""
Supervisor Agent for ATLAS Multi-Agent System

The Supervisor class orchestrates task execution using LangChain/LangGraph architecture,
delegating work to specialized agents while maintaining overall coordination.

MIGRATION NOTE: This file now wraps the new LangChain implementation to maintain
backward compatibility with existing code that imports from this module.
"""

import logging
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from src.agents.langchain_supervisor import LangChainSupervisor
from src.agents.supervisor_graph import create_supervisor_graph, create_initial_state
from src.mlflow.tracking import ATLASMLflowTracker

logger = logging.getLogger(__name__)


class Supervisor:
    """
    ATLAS Supervisor Agent using LangChain/LangGraph architecture.

    The supervisor coordinates task execution by:
    - Planning and decomposing complex tasks into manageable sub-tasks
    - Managing todo items and tracking execution progress
    - Delegating specialized work to research, analysis, and writing agents
    - Maintaining session-scoped file operations for persistent outputs

    Uses LangChain for native tool execution and streaming, with LangGraph for
    state machine orchestration. This replaces the previous Letta-based implementation.
    """

    def __init__(
        self,
        task_id: str,
        mlflow_tracker: Optional[ATLASMLflowTracker] = None,
        agui_manager = None,
        model_name: str = "gpt-4o",
        temperature: float = 0.7
    ):
        """
        Initialize the Supervisor agent with LangChain backend.

        Args:
            task_id: Unique identifier for the task being supervised
            mlflow_tracker: Optional MLflow tracker for monitoring
            agui_manager: Optional AG-UI connection manager for frontend events
            model_name: OpenAI model to use (default: gpt-4o)
            temperature: Model temperature for response generation

        Raises:
            RuntimeError: If initialization fails
        """
        self.task_id = task_id
        self.mlflow_tracker = mlflow_tracker or ATLASMLflowTracker(f"ATLAS_Task_{task_id}")
        self.agui_manager = agui_manager

        # Create LangChain supervisor
        try:
            self.langchain_supervisor = LangChainSupervisor(
                task_id=task_id,
                mlflow_tracker=self.mlflow_tracker,
                agui_manager=agui_manager,
                model_name=model_name,
                temperature=temperature
            )

            # Create LangGraph state machine
            self.graph = create_supervisor_graph(
                supervisor=self.langchain_supervisor,
                checkpointer=None  # Can add SqliteSaver here for persistence
            )

            logger.info(f"Supervisor agent created successfully with LangChain/LangGraph: {task_id}")

        except Exception as e:
            logger.error(f"Failed to create supervisor agent: {e}")
            raise RuntimeError(f"Could not initialize supervisor agent: {e}")

    async def send_message(self, message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Send a message to the supervisor agent and stream the response.

        The agent will process the message using its available tools to:
        - Plan task execution and create sub-tasks
        - Update todo items and track progress
        - Save outputs and manage session files
        - Delegate work to specialized agents as needed

        Args:
            message: The user message or task instruction to process

        Yields:
            Dictionary chunks containing response data

        Raises:
            RuntimeError: If message sending fails or agent is unavailable
        """
        try:
            # Stream response from LangChain supervisor
            async for chunk in self.langchain_supervisor.send_message(message):
                yield chunk

        except Exception as e:
            logger.error(f"Failed to send message to supervisor: {e}")
            if self.mlflow_tracker:
                self.mlflow_tracker.log_metric("message_failures", 1)
            raise RuntimeError(f"Message processing failed: {e}")

    def send_message_sync(self, message: str) -> List[Dict[str, Any]]:
        """
        Synchronous wrapper for send_message for backward compatibility.

        Args:
            message: The user message or task instruction to process

        Returns:
            List of message dictionaries

        Raises:
            RuntimeError: If message sending fails
        """
        import asyncio

        try:
            # Collect all chunks
            chunks = []

            async def collect_chunks():
                async for chunk in self.send_message(message):
                    chunks.append(chunk)

            # Run async function in event loop
            asyncio.run(collect_chunks())

            # Extract content from chunks
            content_chunks = [c for c in chunks if c['type'] == 'content']
            if content_chunks:
                full_content = ''.join([c['data']['content'] for c in content_chunks])
                return [{"role": "assistant", "content": full_content}]

            return []

        except Exception as e:
            logger.error(f"Failed in synchronous message send: {e}")
            raise RuntimeError(f"Message processing failed: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status and state of the supervisor agent.

        Returns comprehensive status information including agent state,
        conversation history, and execution context for monitoring and debugging.

        Returns:
            Dictionary containing:
            - task_id: The associated task identifier
            - model: The LLM model being used
            - tool_count: Number of available tools
            - tools: List of registered tool names
            - message_count: Number of messages in conversation history
            - streaming_enabled: Whether streaming is enabled

        Raises:
            RuntimeError: If status retrieval fails
        """
        try:
            status = self.langchain_supervisor.get_status()
            logger.debug(f"Retrieved status for supervisor {self.task_id}")
            return status

        except Exception as e:
            logger.error(f"Failed to get supervisor status: {e}")
            raise RuntimeError(f"Status retrieval failed: {e}")

    async def cleanup(self) -> None:
        """
        Clean up the supervisor agent and release resources.

        Closes MLflow tracking and clears conversation memory.
        Should be called when the supervisor is no longer needed.

        Raises:
            RuntimeError: If cleanup operations fail
        """
        try:
            # Cleanup LangChain supervisor
            await self.langchain_supervisor.cleanup()

            logger.info(f"Supervisor {self.task_id} cleaned up successfully")

        except Exception as e:
            logger.error(f"Failed to cleanup supervisor agent: {e}")
            raise RuntimeError(f"Cleanup failed: {e}")