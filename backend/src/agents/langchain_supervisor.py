"""
LangChain-based Supervisor Agent for ATLAS

Replaces Letta-based supervisor with native LangChain implementation.
Provides proper tool registration, streaming, and AG-UI integration.
"""

import logging
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory

from .langchain_tools import ALL_SUPERVISOR_TOOLS
from ..mlflow.tracking import ATLASMLflowTracker
from ..agui.events import AGUIEvent, AGUIEventType

logger = logging.getLogger(__name__)


class LangChainSupervisor:
    """
    LangChain-based supervisor agent for ATLAS multi-agent system.

    Replaces Letta with native LangChain implementation for:
    - Proper tool schema generation (no type annotation issues)
    - Native streaming support for real-time frontend updates
    - Simpler deployment (no separate server process)
    - Better error handling and debugging
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
        Initialize the LangChain supervisor agent.

        Args:
            task_id: Unique identifier for the task being supervised
            mlflow_tracker: Optional MLflow tracker for monitoring
            agui_manager: Optional AG-UI connection manager for frontend events
            model_name: OpenAI model to use (default: gpt-4o)
            temperature: Model temperature for response generation
        """
        self.task_id = task_id
        self.mlflow_tracker = mlflow_tracker or ATLASMLflowTracker(f"ATLAS_Task_{task_id}")
        self.agui_manager = agui_manager

        # Initialize ChatOpenAI with tools bound
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            streaming=True,
            verbose=True
        )

        # Bind all supervisor tools to the model
        # Note: strict=True conflicts with optional parameters (defaults in Pydantic)
        # We rely on the validation layer in _execute_tools() to prevent hallucination
        self.llm_with_tools = self.llm.bind_tools(
            ALL_SUPERVISOR_TOOLS,
            strict=False  # Allow optional parameters with defaults
        )

        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history"
        )

        # System prompt for supervisor agent with strict tool enforcement
        self.system_prompt = """You are the ATLAS Supervisor Agent - a task orchestration coordinator.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 CRITICAL RULES - ABSOLUTELY NO EXCEPTIONS 🚨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. YOU MUST ONLY USE THESE 11 TOOLS (NO OTHER TOOLS EXIST):
   ✅ Planning: plan_task, update_plan
   ✅ Todo Management: create_todo, update_todo_status
   ✅ File Operations: save_output, load_file, list_outputs, append_content
   ✅ Delegation: delegate_research, delegate_analysis, delegate_writing

2. NEVER INVENT TOOLS. Examples of FORBIDDEN invented tools:
   ❌ getMonthlyReturn() - DOESN'T EXIST
   ❌ fetchStockData() - DOESN'T EXIST
   ❌ calculateReturn() - DOESN'T EXIST
   ❌ searchDatabase() - DOESN'T EXIST
   If you try to use ANY tool not in the list above, the system will FAIL.

3. YOU ARE A COORDINATOR, NOT AN EXECUTOR:
   - You don't fetch data (use delegate_research)
   - You don't analyze data (use delegate_analysis)
   - You don't write content (use delegate_writing)
   - You ONLY plan, track, delegate, and save results

4. MANDATORY WORKFLOW FOR ALL USER REQUESTS:
   Step 1: plan_task("Break down user request into subtasks")
   Step 2: create_todo for each subtask with dependencies
   Step 3: delegate_research/analysis/writing for actual work
   Step 4: save_output to persist results
   Step 5: Synthesize final response

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE - User asks: "What's the S&P 500 return this month?"

✅ CORRECT APPROACH:
1. plan_task(task_description="Find S&P 500 monthly return", ...)
2. create_todo(description="Get S&P 500 prices", task_type="research")
3. delegate_research(
     context="User wants S&P 500 monthly return",
     task_description="Find current S&P 500 price and price at start of month from reliable financial sources",
     restrictions="Use official market data sources only"
   )
4. delegate_analysis(
     context="We have S&P 500 prices, need to calculate return",
     task_description="Calculate percentage return from start to end of month",
     restrictions="Show calculation steps clearly"
   )
5. save_output(filename="sp500_monthly_return.json", content=results)
6. Respond to user with clear summary

❌ WRONG APPROACH (WILL FAIL):
getMonthlyReturn("S&P 500")  ← THIS TOOL DOESN'T EXIST!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Remember: You coordinate specialized agents. You never do the actual work yourself."""

        # Track initialization in MLflow
        if self.mlflow_tracker:
            self._track_initialization()

        logger.info(f"LangChain supervisor initialized for task {task_id} with {len(ALL_SUPERVISOR_TOOLS)} tools")

    def _track_initialization(self) -> None:
        """Track agent initialization in MLflow."""
        try:
            model_config = {
                "model": self.llm.model_name,
                "temperature": self.llm.temperature,
                "streaming": self.llm.streaming,
                "tool_count": len(ALL_SUPERVISOR_TOOLS)
            }

            self.mlflow_tracker.track_agent_creation(
                agent_id=self.task_id,
                agent_type="langchain_supervisor",
                tools=[tool.name for tool in ALL_SUPERVISOR_TOOLS],
                model_config=model_config
            )
        except Exception as e:
            logger.warning(f"Failed to track initialization in MLflow: {e}")

    async def _broadcast_event(self, event_type: AGUIEventType, data: Dict[str, Any]) -> None:
        """Broadcast an event to the AG-UI frontend."""
        if self.agui_manager:
            try:
                event = AGUIEvent(
                    event_type=event_type,
                    task_id=self.task_id,
                    data=data,
                    timestamp=datetime.now().isoformat()
                )
                await self.agui_manager.broadcast_to_task(self.task_id, event)
            except Exception as e:
                logger.error(f"Failed to broadcast AG-UI event: {e}")

    async def send_message(self, message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Send a message to the supervisor and stream the response.

        This is the main entry point for interacting with the supervisor.
        Supports streaming for real-time frontend updates and proper tool execution.

        Args:
            message: The user message or task instruction

        Yields:
            Dictionary chunks containing:
            - type: "content", "tool_call", "tool_result", or "complete"
            - data: Relevant data for the chunk type
        """
        start_time = datetime.now()

        try:
            # Broadcast task started
            await self._broadcast_event(
                AGUIEventType.AGENT_MESSAGE_SENT,
                {"message": message, "sender": "user"}
            )

            # Get conversation history
            history = self.memory.chat_memory.messages

            # Create messages list
            messages = [
                SystemMessage(content=self.system_prompt),
                *history,
                HumanMessage(content=message)
            ]

            # Stream the response
            full_response = ""
            tool_calls = []

            async for chunk in self.llm_with_tools.astream(messages):
                # Handle content chunks
                if chunk.content:
                    full_response += chunk.content
                    yield {
                        "type": "content",
                        "data": {"content": chunk.content}
                    }

                # Handle tool call chunks
                if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                    for tool_chunk in chunk.tool_call_chunks:
                        if tool_chunk.get('name'):
                            # New tool call started
                            await self._broadcast_event(
                                AGUIEventType.TOOL_CALL_INITIATED,
                                {
                                    "tool_name": tool_chunk['name'],
                                    "tool_call_id": tool_chunk.get('id', ''),
                                    "agent_id": self.task_id
                                }
                            )

                        yield {
                            "type": "tool_call_chunk",
                            "data": tool_chunk
                        }

                # Accumulate complete tool calls (only update if non-empty names)
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    # Check if this chunk has valid tool names before overwriting
                    has_valid_names = False
                    for tc in chunk.tool_calls:
                        name = tc.get('name', '') if isinstance(tc, dict) else getattr(tc, 'name', '')
                        if name and name.strip():
                            has_valid_names = True
                            break

                    # Only update if we have valid tool names
                    if has_valid_names:
                        logger.info(f"Chunk has {len(chunk.tool_calls)} valid tool calls")
                        tool_calls = chunk.tool_calls
                    else:
                        logger.debug(f"Skipping chunk with empty tool names")

            # Execute tool calls if present
            logger.info(f"After streaming loop, tool_calls has {len(tool_calls) if tool_calls else 0} items")
            if tool_calls:
                # Convert ToolCall objects to dictionaries
                tool_call_dicts = []
                for tc in tool_calls:
                    # Handle both dict and object formats
                    if isinstance(tc, dict):
                        tool_call_dicts.append(tc)
                    else:
                        # Convert ToolCall object to dict
                        tool_call_dicts.append({
                            'name': getattr(tc, 'name', ''),
                            'args': getattr(tc, 'args', {}),
                            'id': getattr(tc, 'id', '')
                        })

                # Filter out incomplete tool calls (empty names)
                complete_calls = [tc for tc in tool_call_dicts if tc.get('name', '').strip()]

                if complete_calls:
                    tool_results = await self._execute_tools(complete_calls)
                else:
                    tool_results = []

                for result in tool_results:
                    yield {
                        "type": "tool_result",
                        "data": result
                    }

            # Save to memory
            self.memory.chat_memory.add_user_message(message)
            self.memory.chat_memory.add_ai_message(full_response)

            # Track in MLflow
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            if self.mlflow_tracker:
                self.mlflow_tracker.log_metric("message_processing_ms", duration_ms)

            # Broadcast completion
            await self._broadcast_event(
                AGUIEventType.AGENT_MESSAGE_SENT,
                {
                    "message": full_response,
                    "sender": "assistant",
                    "duration_ms": duration_ms
                }
            )

            # Yield completion
            yield {
                "type": "complete",
                "data": {
                    "full_response": full_response,
                    "tool_calls": tool_calls,
                    "duration_ms": duration_ms
                }
            }

        except Exception as e:
            logger.error(f"Error in send_message: {e}", exc_info=True)

            # Broadcast error
            await self._broadcast_event(
                AGUIEventType.AGENT_ERROR,
                {"error": str(e), "agent_id": self.task_id}
            )

            yield {
                "type": "error",
                "data": {"error": str(e)}
            }

    async def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute tool calls and return results.

        Includes strict validation to prevent tool hallucination.

        Args:
            tool_calls: List of tool call dictionaries from LangChain

        Returns:
            List of tool result dictionaries
        """
        results = []

        # Get valid tool names for validation
        valid_tool_names = {t.name for t in ALL_SUPERVISOR_TOOLS}

        for tool_call in tool_calls:
            # Extract and validate tool name
            tool_name = tool_call.get('name', '').strip()
            tool_args = tool_call.get('args', {})
            tool_id = tool_call.get('id', '')

            # ═══════════════════════════════════════════════════════════
            # VALIDATION LAYER - Hard stop for hallucinated tools
            # ═══════════════════════════════════════════════════════════

            # Check for empty tool name
            if not tool_name:
                error_msg = f"Tool call has empty name. Full call: {tool_call}"
                logger.error(f"Empty tool name received from LLM. Tool call structure: {tool_call}")

                await self._broadcast_event(
                    AGUIEventType.ERROR_OCCURRED,
                    {
                        "error_type": "EMPTY_TOOL_NAME",
                        "tool_call_id": tool_id,
                        "message": error_msg
                    }
                )

                results.append({
                    "tool_name": "",
                    "tool_id": tool_id,
                    "result": f"ERROR: {error_msg}",
                    "success": False,
                    "duration_ms": 0
                })
                continue

            # Check if tool exists in our registered set
            if tool_name not in valid_tool_names:
                error_msg = f"TOOL HALLUCINATION DETECTED: '{tool_name}' is not a valid tool"
                logger.error(f"{error_msg}. Valid tools: {sorted(valid_tool_names)}")

                await self._broadcast_event(
                    AGUIEventType.ERROR_OCCURRED,
                    {
                        "error_type": "TOOL_HALLUCINATION",
                        "attempted_tool": tool_name,
                        "valid_tools": sorted(valid_tool_names),
                        "message": error_msg
                    }
                )

                results.append({
                    "tool_name": tool_name,
                    "tool_id": tool_id,
                    "result": f"ERROR: {error_msg}. Use one of: {', '.join(sorted(valid_tool_names))}",
                    "success": False,
                    "duration_ms": 0
                })
                continue

            try:
                # Find the tool (we know it exists from validation above)
                tool = None
                for t in ALL_SUPERVISOR_TOOLS:
                    if t.name == tool_name:
                        tool = t
                        break

                if not tool:
                    # This should never happen due to validation above,
                    # but keeping for defensive programming
                    raise ValueError(f"Tool {tool_name} not found in registry")

                # Execute tool
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                start_time = datetime.now()

                # Invoke the tool
                result = await tool.ainvoke(tool_args)

                duration_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Track in MLflow
                if self.mlflow_tracker:
                    self.mlflow_tracker.track_tool_invocation(
                        agent_id=self.task_id,
                        tool_name=tool_name,
                        parameters=tool_args,
                        result=result,
                        success=True,
                        duration_ms=duration_ms
                    )

                # Broadcast tool completion
                await self._broadcast_event(
                    AGUIEventType.TOOL_CALL_COMPLETED,
                    {
                        "tool_name": tool_name,
                        "tool_call_id": tool_id,
                        "result": result,
                        "duration_ms": duration_ms,
                        "agent_id": self.task_id
                    }
                )

                results.append({
                    "tool_name": tool_name,
                    "tool_id": tool_id,
                    "result": result,
                    "success": True,
                    "duration_ms": duration_ms
                })

            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)

                # Track failure in MLflow
                if self.mlflow_tracker:
                    self.mlflow_tracker.track_tool_invocation(
                        agent_id=self.task_id,
                        tool_name=tool_name,
                        parameters=tool_args,
                        result=str(e),
                        success=False,
                        duration_ms=0
                    )

                # Broadcast tool error
                await self._broadcast_event(
                    AGUIEventType.TOOL_CALL_FAILED,
                    {
                        "tool_name": tool_name,
                        "tool_call_id": tool_id,
                        "error": str(e),
                        "agent_id": self.task_id
                    }
                )

                results.append({
                    "tool_name": tool_name,
                    "tool_id": tool_id,
                    "error": str(e),
                    "success": False
                })

        return results

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Get the conversation history.

        Returns:
            List of message dictionaries with role and content
        """
        history = []
        for message in self.memory.chat_memory.messages:
            if isinstance(message, HumanMessage):
                history.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                history.append({"role": "assistant", "content": message.content})
            elif isinstance(message, SystemMessage):
                history.append({"role": "system", "content": message.content})

        return history

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the supervisor agent.

        Returns:
            Dictionary containing agent state information
        """
        return {
            "task_id": self.task_id,
            "model": self.llm.model_name,
            "temperature": self.llm.temperature,
            "tool_count": len(ALL_SUPERVISOR_TOOLS),
            "tools": [tool.name for tool in ALL_SUPERVISOR_TOOLS],
            "message_count": len(self.memory.chat_memory.messages),
            "streaming_enabled": self.llm.streaming
        }

    async def cleanup(self) -> None:
        """
        Clean up resources and close connections.
        """
        try:
            # Close MLflow tracking
            if self.mlflow_tracker:
                self.mlflow_tracker.close()
                logger.info("MLflow tracking closed")

            # Clear memory
            self.memory.clear()

            logger.info(f"LangChain supervisor {self.task_id} cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)