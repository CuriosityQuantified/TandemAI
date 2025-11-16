"""
Planning Agent with LangGraph State Persistence

This module implements a plan-and-execute agent pattern with:
- State persistence using PostgreSQL via AsyncPostgresSaver
- Real-time plan updates via WebSocket
- Plan tracking with progress indicators
- Re-planning capabilities
"""

import uuid
import operator
from typing import TypedDict, List, Tuple, Annotated, Optional
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # Updated from SQLite to PostgreSQL
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field, field_validator


# ============================
# Global Planning Agent State
# ============================

# Global checkpointer instance (initialized by main.py's lifespan)
_planning_checkpointer = None
_planning_app = None


# ============================
# State Schema Definition
# ============================

class PlanExecuteState(TypedDict):
    """
    State schema for plan-and-execute workflow with persistence.

    Attributes:
        input: Original user query
        plan: List of plan steps to execute
        past_steps: History of completed steps with results
        current_step_index: Index of currently executing step
        progress: Completion progress (0.0 to 1.0)
        plan_id: Unique identifier for this plan
        response: Final response to user
        messages: Conversation history
    """
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple[str, str]], operator.add]  # (step, result)
    current_step_index: int
    progress: float
    plan_id: str
    response: Optional[str]
    messages: List[BaseMessage]


# ============================
# Planning Models
# ============================

class Plan(BaseModel):
    """Plan model for LLM output"""
    steps: List[str] = Field(
        ...,  # Required
        min_length=1,  # At least 1 step
        max_length=7,  # At most 7 steps
        description="List of research steps to execute"
    )

    @field_validator('steps')
    @classmethod
    def validate_steps_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Plan must contain at least one step")
        if any(not step.strip() for step in v):
            raise ValueError("Plan steps cannot be empty strings")
        return v


class Response(BaseModel):
    """Final response model"""
    response: str


class ReplanAction(BaseModel):
    """Re-plan action with updated steps"""
    steps: List[str]


# ============================
# Planning Logic (Extracted for Tool Use)
# ============================

def create_plan_logic(query: str, num_steps: int = 5) -> Plan:
    """
    Generate a research plan (extracted from create_plan node).

    This is a pure function that can be called by tools without state dependencies.
    No WebSocket broadcasting - that's handled by the calling tool.

    Args:
        query: Research query to plan for
        num_steps: Number of steps to generate (1-10, default 5)

    Returns:
        Plan object with validated steps

    Example:
        >>> plan = create_plan_logic("AI trends in healthcare", num_steps=5)
        >>> print(plan.steps)
        ['Search for AI healthcare trends', ...]
    """
    import logging
    logger = logging.getLogger(__name__)

    # Validate num_steps
    num_steps = max(1, min(num_steps, 10))  # Clamp to 1-10

    # Initialize LLM
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)

    # Create planning prompt
    planning_prompt = f"""You are a research planning assistant. Create a step-by-step research plan.

Research Query: {query}

Create a detailed plan with {num_steps} specific, actionable steps.

IMPORTANT: You must respond with ONLY a JSON object in this exact format:
{{
  "steps": [
    "Step 1: Clear, specific action",
    "Step 2: Clear, specific action",
    "Step 3: Clear, specific action"
  ]
}}

Do not include any explanation or commentary, only the JSON object."""

    # Generate plan
    messages = [
        SystemMessage(content="You are a research planning assistant. You must always respond with valid JSON objects containing a 'steps' array."),
        HumanMessage(content=planning_prompt)
    ]

    try:
        # Use synchronous invoke for simplicity
        plan_response = llm.with_structured_output(Plan).invoke(messages)

        # Validate steps are not empty
        if not plan_response.steps or len(plan_response.steps) == 0:
            raise ValueError("LLM returned empty plan")

    except Exception as e:
        # Fallback to simple single-step plan
        logger.error(f"[Planning] Failed to generate plan: {e}")
        logger.info("[Planning] Using fallback single-step plan")

        plan_response = Plan(steps=[
            f"Research and analyze: {query}"
        ])

    return plan_response


# ============================
# Planning Nodes (DEPRECATED - Use create_plan_logic instead)
# ============================
# These async functions are kept for backwards compatibility with existing
# planning agent workflow. New code should use create_plan_logic() above.

async def create_plan(state: PlanExecuteState) -> dict:
    """
    Create initial plan from user input.

    Emits 'plan_created' event via WebSocket.
    """
    writer = get_stream_writer()

    # Initialize LLM
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)

    # Create planning prompt
    planning_prompt = f"""You are a research planning assistant. Create a step-by-step research plan.

Research Query: {state['input']}

Create a detailed plan with 3-7 specific, actionable steps.

IMPORTANT: You must respond with ONLY a JSON object in this exact format:
{{
  "steps": [
    "Step 1: Clear, specific action",
    "Step 2: Clear, specific action",
    "Step 3: Clear, specific action"
  ]
}}

Do not include any explanation or commentary, only the JSON object."""

    # Generate plan
    messages = [
        SystemMessage(content="You are a research planning assistant. You must always respond with valid JSON objects containing a 'steps' array."),
        HumanMessage(content=planning_prompt)
    ]

    try:
        plan_response = await llm.with_structured_output(Plan).ainvoke(messages)

        # Validate steps are not empty
        if not plan_response.steps or len(plan_response.steps) == 0:
            raise ValueError("LLM returned empty plan")

    except Exception as e:
        # Fallback to simple single-step plan
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[Planning] Failed to generate plan: {e}")
        logger.info("[Planning] Using fallback single-step plan")

        plan_response = Plan(steps=[
            f"Research and analyze: {state['input']}"
        ])

    # Generate unique plan ID
    plan_id = str(uuid.uuid4())

    # Broadcast plan creation via WebSocket
    writer({
        "type": "plan_created",
        "plan_id": plan_id,
        "steps": plan_response.steps,
        "progress": 0.0,
        "timestamp": None  # Will be added by middleware
    })

    return {
        "plan": plan_response.steps,
        "plan_id": plan_id,
        "current_step_index": 0,
        "progress": 0.0,
        "past_steps": []
    }


async def execute_step(state: PlanExecuteState) -> dict:
    """
    Execute the current step in the plan.

    Emits 'step_started' and 'step_completed' events via WebSocket.
    """
    writer = get_stream_writer()

    # Get current step
    current_step = state["plan"][state["current_step_index"]]

    # Calculate progress
    progress = state["current_step_index"] / len(state["plan"])

    # Emit step started event
    writer({
        "type": "step_started",
        "plan_id": state["plan_id"],
        "step_index": state["current_step_index"],
        "step_text": current_step,
        "progress": progress
    })

    # Initialize LLM (using existing agent from module_2_2_simple.py would be better)
    # For now, using simple Claude call as placeholder
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.5)

    # Execute step
    messages = [
        SystemMessage(content=f"You are executing step {state['current_step_index'] + 1} of a research plan."),
        HumanMessage(content=current_step)
    ]

    result = await llm.ainvoke(messages)
    result_content = result.content

    # Emit step completed event
    writer({
        "type": "step_completed",
        "plan_id": state["plan_id"],
        "step_index": state["current_step_index"],
        "result": result_content[:200]  # Truncate for WebSocket
    })

    # Calculate new progress
    new_progress = (state["current_step_index"] + 1) / len(state["plan"])

    return {
        "past_steps": [(current_step, result_content)],
        "current_step_index": state["current_step_index"] + 1,
        "progress": new_progress
    }


async def replan_step(state: PlanExecuteState) -> dict:
    """
    Decide whether to continue, re-plan, or finish.

    Emits 'plan_updated' event if re-planning occurs.
    """
    writer = get_stream_writer()

    # Initialize LLM
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)

    # Create re-planning prompt
    replanning_prompt = f"""You are reviewing progress on a research task.

Original Query: {state['input']}
Original Plan: {state['plan']}
Completed Steps: {state['past_steps']}

Based on the progress, should we:
1. Continue with the plan (if there are more steps)
2. Re-plan (if we need to adjust)
3. Finish (if we have enough information)

If finishing, provide a final response summarizing findings.
If re-planning, provide updated steps.

Return either a Response object with the final answer, or a ReplanAction with new steps."""

    messages = [HumanMessage(content=replanning_prompt)]

    # Try to get a response (finish)
    try:
        response = await llm.with_structured_output(Response).ainvoke(messages)

        # Emit plan completion event via WebSocket
        writer({
            "type": "plan_complete",
            "plan_id": state["plan_id"],
            "response": response.response,
            "progress": 1.0
        })

        return {"response": response.response}
    except:
        # If not finishing, try to re-plan
        try:
            replan = await llm.with_structured_output(ReplanAction).ainvoke(messages)

            # Emit plan update event
            writer({
                "type": "plan_updated",
                "plan_id": state["plan_id"],
                "steps": replan.steps,
                "current_step": state["current_step_index"]
            })

            return {
                "plan": replan.steps,
                "current_step_index": state["current_step_index"]
            }
        except:
            # If both fail, just continue with existing plan
            return {}


# ============================
# Conditional Logic
# ============================

def should_continue(state: PlanExecuteState) -> str:
    """Determine next node based on current state."""
    # If we have a final response, end
    if state.get("response"):
        return "end"

    # If all steps completed, go to replanner
    if state["current_step_index"] >= len(state["plan"]):
        return "replan"

    # Otherwise, execute next step
    return "execute"


# ============================
# Graph Construction
# ============================

def create_planning_graph():
    """
    Create the plan-and-execute LangGraph workflow.

    Returns:
        StateGraph: Compiled graph ready for execution
    """
    workflow = StateGraph(PlanExecuteState)

    # Add nodes
    workflow.add_node("planner", create_plan)
    workflow.add_node("executor", execute_step)
    workflow.add_node("replanner", replan_step)

    # Add edges
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "executor")

    # Conditional edges from executor
    workflow.add_conditional_edges(
        "executor",
        should_continue,
        {
            "execute": "executor",  # Continue executing
            "replan": "replanner",  # Re-plan
            "end": END  # Finish
        }
    )

    # Conditional edges from replanner
    workflow.add_conditional_edges(
        "replanner",
        should_continue,
        {
            "execute": "executor",  # Execute new plan
            "end": END  # Finish
        }
    )

    return workflow


# ============================
# Database Initialization
# ============================

def initialize_planning_agent(checkpointer):
    """
    Initialize planning agent with a shared checkpointer.

    This function should be called from main.py's lifespan context
    with the same checkpointer used by the supervisor agent.

    Args:
        checkpointer: AsyncPostgresSaver instance from setup_checkpointer()
    """
    global _planning_checkpointer, _planning_app

    _planning_checkpointer = checkpointer
    workflow = create_planning_graph()
    _planning_app = workflow.compile(checkpointer=checkpointer)

    print("✅ Planning agent initialized with shared PostgreSQL checkpointer")


def get_planning_agent():
    """
    Get the initialized planning agent.

    Returns:
        Tuple of (app, checkpointer)

    Raises:
        RuntimeError: If agent not initialized
    """
    if _planning_app is None or _planning_checkpointer is None:
        raise RuntimeError(
            "Planning agent not initialized. "
            "Call initialize_planning_agent() from main.py lifespan first."
        )

    return _planning_app, _planning_checkpointer


# ============================
# Helper Functions
# ============================

async def start_research_with_plan(query: str, thread_id: str = None):
    """
    Start a research task with plan tracking.

    Args:
        query: User research query
        thread_id: Optional thread ID for session persistence

    Returns:
        Generator yielding plan events and results
    """
    if thread_id is None:
        thread_id = str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    inputs = {
        "input": query,
        "plan": [],
        "past_steps": [],
        "current_step_index": 0,
        "progress": 0.0,
        "plan_id": "",
        "response": None,
        "messages": []
    }

    # Use shared checkpointer (no connection creation/closing)
    app, checkpointer = get_planning_agent()

    # Stream execution with custom events
    async for event in app.astream(
        inputs,
        config=config,
        stream_mode=["updates", "custom"]
    ):
        yield event


async def get_plan_state(thread_id: str):
    """
    Retrieve current plan state from database.

    Args:
        thread_id: Session thread ID

    Returns:
        dict: Current state with plan, progress, etc.
    """
    # Use shared checkpointer (no connection creation/closing)
    app, checkpointer = get_planning_agent()

    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)

    if state and state.values:
        return {
            "plan_id": state.values.get("plan_id"),
            "plan": state.values.get("plan", []),
            "current_step": state.values.get("current_step_index", 0),
            "past_steps": state.values.get("past_steps", []),
            "progress": state.values.get("progress", 0.0),
            "response": state.values.get("response")
        }

    return None


async def create_plan_only(query: str, thread_id: str = None, num_steps: int = 5):
    """
    Create a research plan WITHOUT executing it.

    This function is used by Plan Mode to generate a structured plan that will be
    passed to the main research agent for execution. The main agent will then:
    1. Receive the plan in its context window
    2. Execute each step using its full toolset
    3. Update plan progress via edit_plan tool

    Args:
        query: User research query
        thread_id: Optional thread ID for session persistence
        num_steps: Number of steps to generate (1-10, default 5)

    Returns:
        dict: Plan structure with plan_id, steps, and metadata

    Example:
        >>> plan = await create_plan_only("AI trends in healthcare")
        >>> print(plan["steps"])
        ['Search for AI healthcare trends', 'Analyze recent papers', ...]
    """
    import time
    import logging

    logger = logging.getLogger(__name__)

    # Import WebSocket manager
    try:
        from websocket_manager import manager
    except ImportError:
        manager = None
        logger.warning("WebSocket manager not available - plan broadcasting disabled")

    # Generate plan using existing logic
    plan_response = create_plan_logic(query, num_steps)

    # Generate unique plan ID
    plan_id = str(uuid.uuid4())

    # Broadcast plan_created event via WebSocket
    if manager and thread_id:
        try:
            await manager.broadcast({
                "type": "agent_event",
                "event_type": "plan_created",
                "thread_id": thread_id,
                "data": {
                    "type": "plan_created",
                    "plan_id": plan_id,
                    "steps": plan_response.steps,
                    "progress": 0.0,
                },
                "timestamp": time.time()
            })
            logger.info(f"📡 Broadcast plan_created event with {len(plan_response.steps)} steps")
        except Exception as e:
            logger.warning(f"⚠️ WebSocket broadcast failed: {e}")

    # Return plan structure for main agent context
    return {
        "plan_id": plan_id,
        "steps": plan_response.steps,
        "current_step_index": 0,
        "progress": 0.0,
        "query": query,
        "total_steps": len(plan_response.steps)
    }
