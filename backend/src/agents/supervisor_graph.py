"""
LangGraph State Machine for ATLAS Supervisor Agent

Provides state-based workflow orchestration with checkpointing and conditional routing.
Integrates with LangChain supervisor for tool execution and conversation management.
"""

import logging
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage

# Optional import for checkpointing (not used yet)
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    SqliteSaver = None  # Checkpointing support optional

from .langchain_supervisor import LangChainSupervisor

logger = logging.getLogger(__name__)


# ============================================================================
# STATE DEFINITION
# ============================================================================

class SupervisorState(TypedDict):
    """
    State schema for the ATLAS supervisor workflow.

    This state is passed between nodes and updated at each step.
    Includes all information needed for task coordination and execution.
    """
    # Core identifiers
    task_id: str
    session_id: Optional[str]

    # Conversation
    messages: Annotated[List[BaseMessage], "Conversation history"]
    current_message: Optional[str]

    # Planning
    plan: Optional[Dict[str, Any]]
    plan_id: Optional[str]

    # Todo tracking
    todos: List[Dict[str, Any]]
    current_todo: Optional[str]

    # Execution state
    status: str  # "planning", "executing", "delegating", "finalizing", "complete", "error"
    current_phase: str  # "plan", "execute", "delegate", "finalize"

    # Session outputs
    session_outputs: List[Dict[str, Any]]

    # Agent coordination
    delegated_tasks: Dict[str, Dict[str, Any]]
    agent_responses: Dict[str, Any]

    # Error handling
    error: Optional[str]
    retry_count: int

    # Metadata
    created_at: str
    updated_at: str


# ============================================================================
# NODE FUNCTIONS
# ============================================================================

async def plan_node(state: SupervisorState, supervisor: LangChainSupervisor) -> SupervisorState:
    """
    Planning node: Analyzes the task and creates an execution plan.

    Uses the supervisor's plan_task tool to decompose the task into manageable sub-tasks.
    Creates initial todos for tracking execution progress.
    """
    logger.info(f"Entering plan_node for task {state['task_id']}")

    try:
        message = state['current_message']

        # Generate plan using supervisor
        # The supervisor will automatically call plan_task tool
        planning_prompt = f"""Analyze this task and create a detailed execution plan:

{message}

Use the plan_task tool to decompose this into 3-5 actionable sub-tasks with clear dependencies.
Then use create_todo for each sub-task to track execution."""

        # Send message to supervisor and collect full response
        full_response = ""
        plan_data = None
        todos = []

        async for chunk in supervisor.send_message(planning_prompt):
            if chunk['type'] == 'tool_result':
                tool_result = chunk['data']
                if tool_result['tool_name'] == 'plan_task':
                    plan_data = tool_result['result']
                elif tool_result['tool_name'] == 'create_todo':
                    todos.append(tool_result['result'])
            elif chunk['type'] == 'content':
                full_response += chunk['data']['content']

        # Update state
        state['plan'] = plan_data
        state['plan_id'] = plan_data.get('plan_id') if plan_data else None
        state['todos'] = todos
        state['status'] = 'executing'
        state['current_phase'] = 'execute'
        state['updated_at'] = datetime.now().isoformat()

        logger.info(f"Planning complete: {len(todos)} todos created")

        return state

    except Exception as e:
        logger.error(f"Error in plan_node: {e}", exc_info=True)
        state['status'] = 'error'
        state['error'] = str(e)
        return state


async def execute_node(state: SupervisorState, supervisor: LangChainSupervisor) -> SupervisorState:
    """
    Execution node: Executes tasks according to the plan.

    Processes todos in dependency order, delegates to specialized agents when needed,
    and saves outputs to the session directory.
    """
    logger.info(f"Entering execute_node for task {state['task_id']}")

    try:
        # Find pending todos with no incomplete dependencies
        pending_todos = [
            todo for todo in state['todos']
            if todo['status'] == 'pending' and
            all(
                any(t['task_id'] == dep and t['status'] == 'completed' for t in state['todos'])
                for dep in todo.get('dependencies', [])
            )
        ]

        if not pending_todos:
            # No more work to do
            state['status'] = 'finalizing'
            state['current_phase'] = 'finalize'
            state['updated_at'] = datetime.now().isoformat()
            return state

        # Process the first ready todo
        current_todo = pending_todos[0]
        state['current_todo'] = current_todo['task_id']

        # Determine if delegation is needed
        task_type = current_todo.get('task_type', '')

        if task_type in ['research', 'analysis', 'writing']:
            # Delegate to specialized agent
            delegation_prompt = f"""Execute the following task by delegating to a specialized {task_type} agent:

Task: {current_todo['description']}

Context from plan: {state['plan'].get('reasoning', '')}

Use the delegate_{task_type} tool to assign this task to the appropriate agent.
Provide clear context and specific instructions."""

            # Send message and collect response
            async for chunk in supervisor.send_message(delegation_prompt):
                if chunk['type'] == 'tool_result' and chunk['data']['tool_name'] == f'delegate_{task_type}':
                    delegation_result = chunk['data']['result']
                    state['delegated_tasks'][current_todo['task_id']] = delegation_result

        else:
            # Execute directly with supervisor
            execution_prompt = f"""Execute this task:

{current_todo['description']}

Save any important outputs using the save_output tool."""

            async for chunk in supervisor.send_message(execution_prompt):
                if chunk['type'] == 'tool_result' and chunk['data']['tool_name'] == 'save_output':
                    output = chunk['data']['result']
                    state['session_outputs'].append(output)

        # Update todo status
        for todo in state['todos']:
            if todo['task_id'] == current_todo['task_id']:
                todo['status'] = 'completed'
                break

        state['updated_at'] = datetime.now().isoformat()

        return state

    except Exception as e:
        logger.error(f"Error in execute_node: {e}", exc_info=True)
        state['status'] = 'error'
        state['error'] = str(e)
        return state


async def finalize_node(state: SupervisorState, supervisor: LangChainSupervisor) -> SupervisorState:
    """
    Finalization node: Synthesizes results and creates final output.

    Reviews all completed work, synthesizes findings from sub-agents,
    and creates a comprehensive final report.
    """
    logger.info(f"Entering finalize_node for task {state['task_id']}")

    try:
        # Gather all results
        completed_todos = [t for t in state['todos'] if t['status'] == 'completed']

        finalization_prompt = f"""All tasks are complete. Create a final comprehensive summary:

Completed tasks:
{[todo['description'] for todo in completed_todos]}

Session outputs:
{state['session_outputs']}

Delegated agent responses:
{state['agent_responses']}

Please:
1. Synthesize all findings into a coherent report
2. Save the final report using save_output tool
3. Provide clear next steps or recommendations"""

        final_output = None
        async for chunk in supervisor.send_message(finalization_prompt):
            if chunk['type'] == 'tool_result' and chunk['data']['tool_name'] == 'save_output':
                final_output = chunk['data']['result']

        state['status'] = 'complete'
        state['current_phase'] = 'complete'
        if final_output:
            state['session_outputs'].append(final_output)
        state['updated_at'] = datetime.now().isoformat()

        logger.info(f"Finalization complete for task {state['task_id']}")

        return state

    except Exception as e:
        logger.error(f"Error in finalize_node: {e}", exc_info=True)
        state['status'] = 'error'
        state['error'] = str(e)
        return state


# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================

def route_from_plan(state: SupervisorState) -> str:
    """Determine next step after planning."""
    if state['status'] == 'error':
        return "error"
    return "execute"


def route_from_execute(state: SupervisorState) -> str:
    """Determine next step after execution."""
    if state['status'] == 'error':
        return "error"

    # Check if there are more pending todos
    pending = [t for t in state['todos'] if t['status'] == 'pending']
    if pending:
        return "execute"  # Loop back to execute more

    return "finalize"


def route_from_finalize(state: SupervisorState) -> str:
    """Determine next step after finalization."""
    if state['status'] == 'error':
        return "error"
    return END


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_supervisor_graph(
    supervisor: LangChainSupervisor,
    checkpointer: Optional[SqliteSaver] = None
) -> StateGraph:
    """
    Create the LangGraph state machine for the supervisor agent.

    Args:
        supervisor: The LangChain supervisor instance
        checkpointer: Optional checkpointer for persistence

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph
    workflow = StateGraph(SupervisorState)

    # Add nodes (pass supervisor to each node function)
    workflow.add_node("plan", lambda state: plan_node(state, supervisor))
    workflow.add_node("execute", lambda state: execute_node(state, supervisor))
    workflow.add_node("finalize", lambda state: finalize_node(state, supervisor))

    # Set entry point
    workflow.set_entry_point("plan")

    # Add conditional edges
    workflow.add_conditional_edges(
        "plan",
        route_from_plan,
        {
            "execute": "execute",
            "error": END
        }
    )

    workflow.add_conditional_edges(
        "execute",
        route_from_execute,
        {
            "execute": "execute",  # Loop back for more todos
            "finalize": "finalize",
            "error": END
        }
    )

    workflow.add_conditional_edges(
        "finalize",
        route_from_finalize,
        {
            END: END,
            "error": END
        }
    )

    # Compile graph
    if checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
    else:
        app = workflow.compile()

    logger.info("Supervisor graph compiled successfully")

    return app


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_initial_state(task_id: str, message: str, session_id: Optional[str] = None) -> SupervisorState:
    """
    Create initial state for a new task.

    Args:
        task_id: Unique task identifier
        message: Initial user message
        session_id: Optional session identifier

    Returns:
        Initial SupervisorState
    """
    return SupervisorState(
        task_id=task_id,
        session_id=session_id,
        messages=[],
        current_message=message,
        plan=None,
        plan_id=None,
        todos=[],
        current_todo=None,
        status="planning",
        current_phase="plan",
        session_outputs=[],
        delegated_tasks={},
        agent_responses={},
        error=None,
        retry_count=0,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )