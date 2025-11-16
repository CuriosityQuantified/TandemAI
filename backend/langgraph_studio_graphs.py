"""
LangGraph Studio Visualization Graphs - MVP

Provides StateGraph wrappers for Studio visualization:
- Main graph: Orchestration with agent/tools/subagents routing
- Researcher graph: Template subagent (agent→tools→end pattern)

Architecture:
- Main graph separates delegation tools from regular tools
- Subagent graphs follow consistent agent→tools→end structure
- Hierarchical thread IDs maintain parent-child relationships
"""

from langgraph.graph import StateGraph, END, add_messages, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
import typing
from typing import Literal, Optional
from langchain_core.messages import ToolMessage, SystemMessage, AIMessage, HumanMessage
from datetime import datetime

# Import from existing system (will use these for actual execution)
from module_2_2_simple import (
    model,
    production_tools,
    # Delegation tools
    delegate_to_researcher,
    delegate_to_data_scientist,
    delegate_to_expert_analyst,
    delegate_to_writer,
    delegate_to_reviewer,
    # Production tools
    tavily_search,
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,  # Added for subagent tools nodes
    create_research_plan_tool,
    update_plan_progress_tool,
    read_current_plan_tool,
    edit_plan_tool,
)

try:
    from module_2_2_simple import checkpointer
except ImportError:
    # If checkpointer not exported, we'll use a simple memory checkpointer for MVP
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()

# ============================================================================
# ACE FRAMEWORK AND OPTIMIZED PROMPTS
# ============================================================================

# ACE Framework imports
from ace import ACEMiddleware, ACE_CONFIGS
from ace.schemas import format_playbook_for_prompt

# Optimized Prompts imports (research-backed system prompts)
from prompts import (
    get_supervisor_prompt,
    get_researcher_prompt,
    get_data_scientist_prompt,
    get_expert_analyst_prompt,
    get_writer_prompt,
    get_reviewer_prompt,
)

# ============================================================================
# ACE MIDDLEWARE INITIALIZATION
# ============================================================================

# Initialize ACE middleware for all agents
# Uses local Ollama (zero cost) for Osmosis-Structure-0.6B extraction
# Configs control per-agent ACE behavior (enable/disable, reflection mode, etc.)
ace_middleware = ACEMiddleware(
    store=checkpointer.store if hasattr(checkpointer, 'store') else None,
    configs=ACE_CONFIGS,
    osmosis_mode="ollama"  # Use local Ollama (free, fast)
)

import logging
logger = logging.getLogger(__name__)
logger.info(f"ACE Middleware initialized with {len(ACE_CONFIGS)} agent configs (osmosis_mode=ollama)")

# ============================================================================
# STATE DEFINITIONS
# ============================================================================


class SupervisorAgentState(MessagesState):
    """State for supervisor orchestration agent - extends MessagesState for Studio compatibility"""

    thread_id: str
    parent_thread_id: Optional[str] = None  # For subagent execution context
    subagent_thread_id: Optional[str] = None  # For subagent execution context
    subagent_type: Optional[str] = None  # Type of subagent (researcher, writer, etc.)
    # Note: messages field automatically inherited from MessagesState with proper add_messages reducer


class SubagentState(MessagesState):
    """State for subagent execution - extends MessagesState for Studio compatibility"""

    parent_thread_id: str
    subagent_type: str
    # Note: messages field automatically inherited from MessagesState with proper add_messages reducer


# ============================================================================
# MAIN GRAPH: NODES
# ============================================================================


def agent_node(state: SupervisorAgentState):
    """
    Main reasoning node - invokes Claude with all tools available

    Returns: Updated state with agent's response (may include tool calls)
    """
    messages = state["messages"]

    # Use optimized supervisor prompt (450 lines, research-backed AgentOrchestra pattern)
    current_date = datetime.now().strftime("%Y-%m-%d")
    system_prompt = get_supervisor_prompt(current_date=current_date)

    messages_with_system = [SystemMessage(content=system_prompt)] + list(messages)
    # Bind all production tools to the model for this invocation
    model_with_tools = model.bind_tools(production_tools)
    response = model_with_tools.invoke(messages_with_system)
    return {"messages": [response]}


# ============================================================================
# SEPARATE TOOL NODES: DELEGATION vs PRODUCTION
# ============================================================================
# Phase 1.1: Create separate ToolNode instances for delegation and production tools
# This allows Command.goto routing from delegation tools to work properly

# Delegation tools - return Command.goto to route to subagent nodes
delegation_tools = [
    delegate_to_researcher,
    delegate_to_data_scientist,
    delegate_to_expert_analyst,
    delegate_to_writer,
    delegate_to_reviewer,
]

# Production tools - regular tools that loop back to agent
supervisor_production_tools = [
    tavily_search,
    write_file_tool,
    edit_file_with_approval,
    create_research_plan_tool,
    update_plan_progress_tool,
    read_current_plan_tool,
    edit_plan_tool,
]

# Create separate ToolNode executors
delegation_tool_node = ToolNode(delegation_tools)
supervisor_production_tool_node = ToolNode(supervisor_production_tools)


async def delegation_tools_node(state: SupervisorAgentState):
    """
    Delegation tool execution node using prebuilt ToolNode.

    Executes ONLY delegation tools which return Command.goto objects.
    ToolNode automatically handles Command.goto routing to subagent nodes.

    No edge back to agent - Command.goto handles routing dynamically.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.debug(f"🔧 delegation_tools_node invoked")
    logger.debug(f"   Messages in state: {len(state.get('messages', []))}")

    result = await delegation_tool_node.ainvoke(state)

    logger.debug(f"🔧 delegation_tools_node result type: {type(result)}")
    if isinstance(result, Command):
        logger.debug(f"   ✅ Returned Command(goto={result.goto})")
        logger.debug(f"   Update keys: {list(result.update.keys()) if hasattr(result, 'update') and result.update else 'None'}")
    elif isinstance(result, dict):
        logger.debug(f"   Result keys: {list(result.keys())}")
    else:
        logger.debug(f"   Unexpected result type: {type(result)}")

    return result


async def supervisor_production_tools_node(state: SupervisorAgentState):
    """
    Production tool execution node using prebuilt ToolNode.

    Executes regular production tools (tavily_search, write_file, etc.).
    Returns ToolMessages and loops back to agent for continued reasoning.
    """
    return await supervisor_production_tool_node.ainvoke(state)


# ============================================================================
# SUBAGENT TOOLS NODES: PHASE 1.2
# ============================================================================
# Each subagent gets its own dedicated tools node with appropriate tools
# This allows subagents to have their own reasoning loops without routing conflicts

# Researcher Tools Node - includes search and file operations
researcher_tools_list = [
    tavily_search,
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,
]
researcher_tool_node_executor = ToolNode(researcher_tools_list)

async def researcher_tools_node_unified(state: SupervisorAgentState):
    """Execute Researcher's tools and return to researcher for continued reasoning"""
    return await researcher_tool_node_executor.ainvoke(state)


# Data Scientist Tools Node - includes search and file operations
data_scientist_tools_list = [
    tavily_search,
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,
]
data_scientist_tool_node_executor = ToolNode(data_scientist_tools_list)

async def data_scientist_tools_node_unified(state: SupervisorAgentState):
    """Execute Data Scientist's tools and return to data scientist for continued reasoning"""
    return await data_scientist_tool_node_executor.ainvoke(state)


# Expert Analyst Tools Node - includes search and file operations
expert_analyst_tools_list = [
    tavily_search,
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,
]
expert_analyst_tool_node_executor = ToolNode(expert_analyst_tools_list)

async def expert_analyst_tools_node_unified(state: SupervisorAgentState):
    """Execute Expert Analyst's tools and return to expert analyst for continued reasoning"""
    return await expert_analyst_tool_node_executor.ainvoke(state)


# Writer Tools Node - primarily file operations (writers don't typically search)
writer_tools_list = [
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,
]
writer_tool_node_executor = ToolNode(writer_tools_list)

async def writer_tools_node_unified(state: SupervisorAgentState):
    """Execute Writer's tools and return to writer for continued reasoning"""
    return await writer_tool_node_executor.ainvoke(state)


# Reviewer Tools Node - file operations for review
reviewer_tools_list = [
    write_file_tool,
    edit_file_with_approval,
    read_file_tool,
]
reviewer_tool_node_executor = ToolNode(reviewer_tools_list)

async def reviewer_tools_node_unified(state: SupervisorAgentState):
    """Execute Reviewer's tools and return to reviewer for continued reasoning"""
    return await reviewer_tool_node_executor.ainvoke(state)


def subagents_node(state: SupervisorAgentState):
    """
    Delegation node - handles all subagent delegation

    Filters tool calls to only execute delegation tools.
    Creates child threads with hierarchical IDs for each delegation.

    Returns: Delegation results
    """
    last_message = state["messages"][-1]

    # Check if message has tool calls
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {"messages": []}

    # Define delegation tool names
    delegation_tool_names = {
        "delegate_to_researcher",
        "delegate_to_data_scientist",
        "delegate_to_expert_analyst",
        "delegate_to_writer",
        "delegate_to_reviewer",
    }

    # Filter to only delegation tools
    delegation_calls = [
        tc for tc in last_message.tool_calls if tc["name"] in delegation_tool_names
    ]

    # Execute delegations (simplified for MVP)
    results = []
    for delegation in delegation_calls:
        # In full implementation, this would invoke actual subagent
        # For MVP, we'll just create a message indicating delegation occurred
        result_message = ToolMessage(
            content=f"Delegation {delegation['name']} executed",
            tool_call_id=delegation.get("id", "unknown"),
        )
        results.append(result_message)

    return {"messages": results}


# ============================================================================
# MAIN GRAPH: ROUTING
# ============================================================================


def should_continue_supervisor(state: SupervisorAgentState) -> Literal["delegation_tools", "supervisor_production_tools", "end"]:
    """
    Route supervisor agent to appropriate tools node or end.

    - delegation_tools: For delegate_to_* tools (Command.goto routing to subagents)
    - supervisor_production_tools: For tavily_search, file operations, plan tools (loop back to supervisor)
    - end: No tool calls, finish execution

    Logic:
    1. Check for tool calls in last message
    2. If delegation tool (starts with "delegate_to_") → route to "delegation_tools"
    3. If other tool → route to "supervisor_production_tools"
    4. No tool calls → route to "end"

    Returns: "delegation_tools", "supervisor_production_tools", or "end"
    """
    import logging
    logger = logging.getLogger(__name__)

    messages = state.get("messages", [])
    if not messages:
        logger.debug("⚠️ should_continue_supervisor: No messages, routing to END")
        return "end"

    last_message = messages[-1]
    logger.debug(f"📨 should_continue_supervisor: Last message type: {type(last_message).__name__}")

    # Check if last message has tool calls
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        logger.debug("⚠️ should_continue_supervisor: No tool calls, routing to END")
        return "end"

    logger.debug(f"🔧 should_continue_supervisor: {len(last_message.tool_calls)} tool call(s) detected")

    # Detect delegation tools by name pattern
    for tool_call in last_message.tool_calls:
        tool_name = tool_call.get("name", "")
        logger.debug(f"   - Tool: {tool_name}")
        if tool_name.startswith("delegate_to_"):
            logger.debug(f"✅ DELEGATION DETECTED → routing to 'delegation_tools'")
            return "delegation_tools"

    # All other tools are production tools
    logger.debug(f"✅ PRODUCTION TOOLS → routing to 'supervisor_production_tools'")
    return "supervisor_production_tools"


def route_after_tools(state: SupervisorAgentState) -> Literal["agent", "continue"]:
    """
    Router function for tools node - respects Command.goto for delegation

    This function solves the delegation routing issue where the unconditional
    edge "tools" → "agent" was overriding Command.goto routing from delegation tools.

    Logic:
    1. Check if the last tool execution was a delegation tool
    2. If delegation → return "continue" (allows Command.goto to route to subagent)
    3. If normal tool → return "agent" (loop back to supervisor)

    Delegation tools: delegate_to_researcher, delegate_to_data_scientist, etc.

    Returns: "agent" for normal loop-back, "continue" for delegation routing
    """
    messages = state.get("messages", [])

    # Need at least 2 messages: AIMessage with tool_calls + ToolMessage with result
    if len(messages) < 2:
        return "agent"

    last_msg = messages[-1]  # ToolMessage
    prev_msg = messages[-2]  # AIMessage with tool_calls

    # Check if previous message had tool calls
    if hasattr(prev_msg, 'tool_calls') and prev_msg.tool_calls:
        for tool_call in prev_msg.tool_calls:
            tool_name = tool_call.get('name', '')
            # Delegation tools start with 'delegate_to_'
            if tool_name.startswith('delegate_to_'):
                # Delegation detected - let Command.goto handle routing
                return "continue"

    # Normal tool execution - loop back to agent
    return "agent"


# ============================================================================
# MAIN GRAPH: BUILD
# ============================================================================


def create_supervisor_agent_graph():
    """
    Build main orchestration graph

    Structure:
    __start__ → agent → routing →
      ├─ delegation_tools (delegation with Command.goto)
      ├─ supervisor_production_tools (regular tool execution)
      ├─ subagents (legacy delegation node - deprecated)
      └─ end

    Phase 1.1: Separated tools nodes for proper Command.goto routing
    """
    workflow = StateGraph(SupervisorAgentState)

    # Wrap agent node with ACE middleware for reflection and playbook injection
    wrapped_agent_node = ace_middleware.wrap_node(agent_node, agent_type="supervisor")

    # Add nodes (use ACE-wrapped version for main agent)
    workflow.add_node("agent", wrapped_agent_node)
    # Phase 1.1: Separate tools nodes
    workflow.add_node("delegation_tools", delegation_tools_node)
    workflow.add_node("supervisor_production_tools", supervisor_production_tools_node)
    workflow.add_node("subagents", subagents_node)  # Keep for backward compatibility

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional routing from agent
    # Phase 1.3: Route to separate tools nodes based on tool type
    workflow.add_conditional_edges(
        "agent",
        should_continue_supervisor,
        {
            "delegation_tools": "delegation_tools",
            "supervisor_production_tools": "supervisor_production_tools",
            "end": END,
        },
    )

    # Phase 1.1: Edge configuration for separate tools nodes
    # Production tools loop back to agent
    workflow.add_edge("supervisor_production_tools", "agent")
    # Delegation tools have NO edge - Command.goto handles routing
    # Legacy subagents node loops back
    workflow.add_edge("subagents", "agent")

    return workflow.compile(checkpointer=checkpointer)


# Compile supervisor graph
supervisor_graph = create_supervisor_agent_graph()


# ============================================================================
# SUBAGENT GRAPH TEMPLATE: RESEARCHER (MVP)
# ============================================================================


def create_researcher_graph():
    """
    Build researcher subagent graph

    Structure (same for ALL subagents):
    __start__ → agent → routing →
      ├─ tools (subagent-specific tools)
      └─ end

    tools → routing →
      ├─ agent (continue reasoning)
      └─ end (task complete)

    Note: In MVP, we use simplified tool execution.
    In full implementation, this would use actual researcher tools.
    """

    # Researcher-specific nodes
    def researcher_agent_node(state: SubagentState):
        """Researcher reasoning node with optimized prompt"""
        messages = state["messages"]

        # Use optimized researcher prompt (350 lines with extensive citation requirements)
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = get_researcher_prompt(current_date=current_date)

        messages_with_system = [SystemMessage(content=system_prompt)] + list(messages)
        model_with_tools = model.bind_tools(production_tools)
        response = model_with_tools.invoke(messages_with_system)
        return {"messages": [response]}

    def researcher_tools_node(state: SubagentState):
        """Researcher tool execution node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        # Execute researcher tools (simplified for MVP)
        results = []
        for idx, tool_call in enumerate(last_message.tool_calls):
            try:
                # Extract tool_call_id with defensive None handling
                tool_call_id = tool_call.get("id")
                tool_name = tool_call.get('name', 'unknown_tool')

                # Generate fallback ID if missing or None
                if not tool_call_id:
                    tool_call_id = f"fallback_{tool_name}_{idx}"
                    logger.warning(f"[Researcher Tools] Missing tool_call_id for {tool_name}. Generated fallback: {tool_call_id}")

                result_message = ToolMessage(
                    content=f"Researcher tool {tool_name} executed",
                    tool_call_id=tool_call_id,
                )
                results.append(result_message)

            except Exception as e:
                logger.error(f"[Researcher Tools] Error creating ToolMessage for tool_call {idx}: {e}")
                logger.error(f"[Researcher Tools] Problematic tool_call: {tool_call}")
                # Continue to next tool call instead of crashing
                continue

        return {"messages": results}

    # Routing functions
    def should_continue_researcher(state: SubagentState) -> Literal["tools", "end"]:
        """Router from agent node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "end"

        return "tools"

    def should_continue_after_tools(state: SubagentState) -> Literal["agent", "end"]:
        """Router from tools node"""
        # Could add logic here to determine if task is complete
        # For MVP, always go back to agent for next reasoning step
        # Agent will decide to end on next iteration
        return "agent"

    # Build workflow
    workflow = StateGraph(SubagentState)

    # Wrap agent node with ACE middleware
    wrapped_researcher = ace_middleware.wrap_node(researcher_agent_node, agent_type="researcher")

    # Add nodes (use ACE-wrapped version for agent)
    workflow.add_node("agent", wrapped_researcher)
    workflow.add_node("tools", researcher_tools_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Conditional edges from agent
    workflow.add_conditional_edges(
        "agent", should_continue_researcher, {"tools": "tools", "end": END}
    )

    # Conditional edges from tools
    workflow.add_conditional_edges(
        "tools", should_continue_after_tools, {"agent": "agent", "end": END}
    )

    return workflow.compile(checkpointer=checkpointer)


# Compile researcher graph
researcher_graph = create_researcher_graph()


# ============================================================================
# SUBAGENT GRAPH: DATA SCIENTIST
# ============================================================================


def create_data_scientist_graph():
    """
    Build data scientist subagent graph

    Structure (same as all subagents):
    __start__ → agent → routing →
      ├─ tools (subagent-specific tools)
      └─ end

    tools → routing →
      ├─ agent (continue reasoning)
      └─ end (task complete)
    """

    # Data scientist-specific nodes
    def data_scientist_agent_node(state: SubagentState):
        """Data scientist reasoning node with optimized prompt"""
        messages = state["messages"]

        # Use optimized data scientist prompt (250 lines, hypothesis-driven analysis)
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = get_data_scientist_prompt(current_date=current_date)

        messages_with_system = [SystemMessage(content=system_prompt)] + list(messages)
        model_with_tools = model.bind_tools(production_tools)
        response = model_with_tools.invoke(messages_with_system)
        return {"messages": [response]}

    def data_scientist_tools_node(state: SubagentState):
        """Data scientist tool execution node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        # Execute data scientist tools (simplified for MVP)
        results = []
        for idx, tool_call in enumerate(last_message.tool_calls):
            try:
                tool_call_id = tool_call.get("id")
                tool_name = tool_call.get('name', 'unknown_tool')
                if not tool_call_id:
                    tool_call_id = f"fallback_{tool_name}_{idx}"
                    logger.warning(f"[Data Scientist Tools] Missing tool_call_id for {tool_name}. Generated fallback: {tool_call_id}")
                result_message = ToolMessage(
                    content=f"Data scientist tool {tool_name} executed",
                    tool_call_id=tool_call_id,
                )
                results.append(result_message)
            except Exception as e:
                logger.error(f"[Data Scientist Tools] Error creating ToolMessage for tool_call {idx}: {e}")
                continue

        return {"messages": results}

    # Routing functions
    def should_continue_data_scientist(state: SubagentState) -> Literal["tools", "end"]:
        """Router from agent node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "end"

        return "tools"

    def should_continue_after_tools(state: SubagentState) -> Literal["agent", "end"]:
        """Router from tools node"""
        return "agent"

    # Build workflow
    workflow = StateGraph(SubagentState)

    # Wrap agent node with ACE middleware
    wrapped_data_scientist = ace_middleware.wrap_node(data_scientist_agent_node, agent_type="data_scientist")

    # Add nodes (use ACE-wrapped version for agent)
    workflow.add_node("agent", wrapped_data_scientist)
    workflow.add_node("tools", data_scientist_tools_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Conditional edges from agent
    workflow.add_conditional_edges(
        "agent", should_continue_data_scientist, {"tools": "tools", "end": END}
    )

    # Conditional edges from tools
    workflow.add_conditional_edges(
        "tools", should_continue_after_tools, {"agent": "agent", "end": END}
    )

    return workflow.compile(checkpointer=checkpointer)


# Compile data scientist graph
data_scientist_graph = create_data_scientist_graph()


# ============================================================================
# SUBAGENT GRAPH: EXPERT ANALYST
# ============================================================================


def create_expert_analyst_graph():
    """
    Build expert analyst subagent graph

    Structure (same as all subagents):
    __start__ → agent → routing →
      ├─ tools (subagent-specific tools)
      └─ end

    tools → routing →
      ├─ agent (continue reasoning)
      └─ end (task complete)
    """

    # Expert analyst-specific nodes
    def expert_analyst_agent_node(state: SubagentState):
        """Expert analyst reasoning node with optimized prompt"""
        messages = state["messages"]

        # Use optimized expert analyst prompt (250 lines, Decision→Plan→Execute→Judge workflow)
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = get_expert_analyst_prompt(current_date=current_date)

        messages_with_system = [SystemMessage(content=system_prompt)] + list(messages)
        model_with_tools = model.bind_tools(production_tools)
        response = model_with_tools.invoke(messages_with_system)
        return {"messages": [response]}

    def expert_analyst_tools_node(state: SubagentState):
        """Expert analyst tool execution node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        # Execute expert analyst tools (simplified for MVP)
        results = []
        for idx, tool_call in enumerate(last_message.tool_calls):

            try:

                tool_call_id = tool_call.get("id")

                tool_name = tool_call.get('name', 'unknown_tool')

                if not tool_call_id:

                    tool_call_id = f"fallback_{tool_name}_{idx}"

                    logger.warning(f"[Expert analyst Tools] Missing tool_call_id for {tool_name}. Generated fallback: {tool_call_id}")

                result_message = ToolMessage(

                    content=f"Expert analyst tool {tool_name} executed",

                    tool_call_id=tool_call_id,

                )

                results.append(result_message)

            except Exception as e:

                logger.error(f"[Expert analyst Tools] Error creating ToolMessage for tool_call {idx}: {e}")

                continue

        return {"messages": results}

    # Routing functions
    def should_continue_expert_analyst(state: SubagentState) -> Literal["tools", "end"]:
        """Router from agent node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "end"

        return "tools"

    def should_continue_after_tools(state: SubagentState) -> Literal["agent", "end"]:
        """Router from tools node"""
        return "agent"

    # Build workflow
    workflow = StateGraph(SubagentState)

    # Wrap agent node with ACE middleware
    wrapped_expert_analyst = ace_middleware.wrap_node(expert_analyst_agent_node, agent_type="expert_analyst")

    # Add nodes (use ACE-wrapped version for agent)
    workflow.add_node("agent", wrapped_expert_analyst)
    workflow.add_node("tools", expert_analyst_tools_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Conditional edges from agent
    workflow.add_conditional_edges(
        "agent", should_continue_expert_analyst, {"tools": "tools", "end": END}
    )

    # Conditional edges from tools
    workflow.add_conditional_edges(
        "tools", should_continue_after_tools, {"agent": "agent", "end": END}
    )

    return workflow.compile(checkpointer=checkpointer)


# Compile expert analyst graph
expert_analyst_graph = create_expert_analyst_graph()


# ============================================================================
# SUBAGENT GRAPH: WRITER
# ============================================================================


def create_writer_graph():
    """
    Build writer subagent graph

    Structure (same as all subagents):
    __start__ → agent → routing →
      ├─ tools (subagent-specific tools)
      └─ end

    tools → routing →
      ├─ agent (continue reasoning)
      └─ end (task complete)
    """

    # Writer-specific nodes
    def writer_agent_node(state: SubagentState):
        """Writer reasoning node with optimized prompt"""
        messages = state["messages"]

        # Use optimized writer prompt (300 lines, multi-stage writing workflow)
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = get_writer_prompt(current_date=current_date)

        messages_with_system = [SystemMessage(content=system_prompt)] + list(messages)
        model_with_tools = model.bind_tools(production_tools)
        response = model_with_tools.invoke(messages_with_system)
        return {"messages": [response]}

    def writer_tools_node(state: SubagentState):
        """Writer tool execution node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        # Execute writer tools (simplified for MVP)
        results = []
        for idx, tool_call in enumerate(last_message.tool_calls):

            try:

                tool_call_id = tool_call.get("id")

                tool_name = tool_call.get('name', 'unknown_tool')

                if not tool_call_id:

                    tool_call_id = f"fallback_{tool_name}_{idx}"

                    logger.warning(f"[Writer Tools] Missing tool_call_id for {tool_name}. Generated fallback: {tool_call_id}")

                result_message = ToolMessage(

                    content=f"Writer tool {tool_name} executed",

                    tool_call_id=tool_call_id,

                )

                results.append(result_message)

            except Exception as e:

                logger.error(f"[Writer Tools] Error creating ToolMessage for tool_call {idx}: {e}")

                continue

        return {"messages": results}

    # Routing functions
    def should_continue_writer(state: SubagentState) -> Literal["tools", "end"]:
        """Router from agent node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "end"

        return "tools"

    def should_continue_after_tools(state: SubagentState) -> Literal["agent", "end"]:
        """Router from tools node"""
        return "agent"

    # Build workflow
    workflow = StateGraph(SubagentState)

    # Wrap agent node with ACE middleware
    wrapped_writer = ace_middleware.wrap_node(writer_agent_node, agent_type="writer")

    # Add nodes (use ACE-wrapped version for agent)
    workflow.add_node("agent", wrapped_writer)
    workflow.add_node("tools", writer_tools_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Conditional edges from agent
    workflow.add_conditional_edges(
        "agent", should_continue_writer, {"tools": "tools", "end": END}
    )

    # Conditional edges from tools
    workflow.add_conditional_edges(
        "tools", should_continue_after_tools, {"agent": "agent", "end": END}
    )

    return workflow.compile(checkpointer=checkpointer)


# Compile writer graph
writer_graph = create_writer_graph()


# ============================================================================
# SUBAGENT GRAPH: REVIEWER
# ============================================================================


def create_reviewer_graph():
    """
    Build reviewer subagent graph

    Structure (same as all subagents):
    __start__ → agent → routing →
      ├─ tools (subagent-specific tools)
      └─ end

    tools → routing →
      ├─ agent (continue reasoning)
      └─ end (task complete)
    """

    # Reviewer-specific nodes
    def reviewer_agent_node(state: SubagentState):
        """Reviewer reasoning node with optimized prompt"""
        messages = state["messages"]

        # Use optimized reviewer prompt (300 lines, quality criteria & gap identification)
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = get_reviewer_prompt(current_date=current_date)

        messages_with_system = [SystemMessage(content=system_prompt)] + list(messages)
        model_with_tools = model.bind_tools(production_tools)
        response = model_with_tools.invoke(messages_with_system)
        return {"messages": [response]}

    def reviewer_tools_node(state: SubagentState):
        """Reviewer tool execution node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        # Execute reviewer tools (simplified for MVP)
        results = []
        for idx, tool_call in enumerate(last_message.tool_calls):

            try:

                tool_call_id = tool_call.get("id")

                tool_name = tool_call.get('name', 'unknown_tool')

                if not tool_call_id:

                    tool_call_id = f"fallback_{tool_name}_{idx}"

                    logger.warning(f"[Reviewer Tools] Missing tool_call_id for {tool_name}. Generated fallback: {tool_call_id}")

                result_message = ToolMessage(

                    content=f"Reviewer tool {tool_name} executed",

                    tool_call_id=tool_call_id,

                )

                results.append(result_message)

            except Exception as e:

                logger.error(f"[Reviewer Tools] Error creating ToolMessage for tool_call {idx}: {e}")

                continue

        return {"messages": results}

    # Routing functions
    def should_continue_reviewer(state: SubagentState) -> Literal["tools", "end"]:
        """Router from agent node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "end"

        return "tools"

    def should_continue_after_tools(state: SubagentState) -> Literal["agent", "end"]:
        """Router from tools node"""
        return "agent"

    # Build workflow
    workflow = StateGraph(SubagentState)

    # Wrap agent node with ACE middleware
    wrapped_reviewer = ace_middleware.wrap_node(reviewer_agent_node, agent_type="reviewer")

    # Add nodes (use ACE-wrapped version for agent)
    workflow.add_node("agent", wrapped_reviewer)
    workflow.add_node("tools", reviewer_tools_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Conditional edges from agent
    workflow.add_conditional_edges(
        "agent", should_continue_reviewer, {"tools": "tools", "end": END}
    )

    # Conditional edges from tools
    workflow.add_conditional_edges(
        "tools", should_continue_after_tools, {"agent": "agent", "end": END}
    )

    return workflow.compile(checkpointer=checkpointer)


# Compile reviewer graph
reviewer_graph = create_reviewer_graph()


# ============================================================================
# UNIFIED GRAPH: ALL SUBAGENTS AS INDIVIDUAL NODES
# ============================================================================


def create_unified_graph(custom_checkpointer=None):
    """
    Build unified graph showing all subagents as individual nodes

    Structure:
    __start__ → agent → routing →
      ├─ tools (regular tool execution)
      ├─ subagents_router → [researcher_agent, data_scientist_agent, expert_analyst_agent, writer_agent, reviewer_agent]
      └─ end

    Each subagent has:
      subagent_agent → subagent_tools → agent (back to main)

    This provides a single-page view of the entire system with all 13+ nodes visible.

    Args:
        custom_checkpointer: Optional PostgreSQL checkpointer to use instead of module-level one
    """
    # Use custom checkpointer if provided, otherwise fall back to module-level
    active_checkpointer = custom_checkpointer if custom_checkpointer is not None else checkpointer

    # ========================================================================
    # SUBAGENT NODES: RESEARCHER
    # ========================================================================

    async def researcher_agent_node(state: SupervisorAgentState):
        """Researcher subagent reasoning node with optimized prompt and real-time event emission"""
        messages = state["messages"]

        # Get thread context from state for event emission
        parent_thread_id = state.get("parent_thread_id")
        subagent_thread_id = state.get("subagent_thread_id")
        subagent_type = state.get("subagent_type", "researcher")

        # Extract task from delegation tool call
        task_content = None
        for msg in reversed(messages):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get("name") == "delegate_to_researcher":
                        task_content = tc.get("args", {}).get("task")
                        break
            if task_content:
                break

        # Use optimized researcher prompt (350 lines with extensive citation requirements)
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = get_researcher_prompt(current_date=current_date)

        context_messages = [SystemMessage(content=system_prompt)]

        # Add task as HumanMessage with explicit completion instructions
        if task_content:
            context_messages.append(HumanMessage(content=f"""{task_content}

IMPORTANT COMPLETION INSTRUCTIONS:
- After gathering information and writing findings, provide a final summary
- When you are done, respond WITHOUT making any tool calls
- Do not continue searching after writing your research findings
- A simple summary response with no tool calls will complete the task"""))
        else:
            # Fallback if no task found
            context_messages.append(HumanMessage(content="Please proceed with the research task."))

        # Import event emitter
        from subagents.event_emitter import emit_subagent_event

        # Use ainvoke to get complete response with valid tool_call_ids
        # Streaming was causing incomplete tool_call objects without proper 'id' fields
        model_with_tools = model.bind_tools(production_tools)
        response = await model_with_tools.ainvoke(context_messages)

        # Emit response event for frontend visibility
        if parent_thread_id and subagent_thread_id and response.content:
            await emit_subagent_event(
                parent_thread_id=parent_thread_id,
                subagent_thread_id=subagent_thread_id,
                subagent_type=subagent_type,
                event_type="llm_response",
                data={"content": response.content}
            )

        # Emit tool call events if any
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                if parent_thread_id and subagent_thread_id:
                    await emit_subagent_event(
                        parent_thread_id=parent_thread_id,
                        subagent_thread_id=subagent_thread_id,
                        subagent_type=subagent_type,
                        event_type="tool_call",
                        data={
                            "tool_name": tool_call.get("name", "unknown"),
                            "tool_args": tool_call.get("args", {})
                        }
                    )

        return {"messages": [response]}

    def researcher_tools_node(state: SupervisorAgentState):
        """Researcher subagent tool execution node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        results = []
        for idx, tool_call in enumerate(last_message.tool_calls):
            try:
                # Extract tool_call_id with defensive None handling
                tool_call_id = tool_call.get("id")
                tool_name = tool_call.get('name', 'unknown_tool')

                # Generate fallback ID if missing or None
                if not tool_call_id:
                    tool_call_id = f"fallback_{tool_name}_{idx}"
                    logger.warning(f"[Researcher Tools] Missing tool_call_id for {tool_name}. Generated fallback: {tool_call_id}")

                result_message = ToolMessage(
                    content=f"Researcher tool {tool_name} executed",
                    tool_call_id=tool_call_id,
                )
                results.append(result_message)

            except Exception as e:
                logger.error(f"[Researcher Tools] Error creating ToolMessage for tool_call {idx}: {e}")
                logger.error(f"[Researcher Tools] Problematic tool_call: {tool_call}")
                # Continue to next tool call instead of crashing
                continue

        return {"messages": results}

    # ========================================================================
    # SUBAGENT NODES: DATA SCIENTIST
    # ========================================================================

    async def data_scientist_agent_node(state: SupervisorAgentState):
        """Data scientist subagent reasoning node with optimized prompt"""
        messages = state["messages"]

        # Extract task from delegation tool call
        task_content = None
        for msg in reversed(messages):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get("name") == "delegate_to_data_scientist":
                        task_content = tc.get("args", {}).get("task")
                        break
            if task_content:
                break

        # Use optimized data scientist prompt (250 lines, hypothesis-driven analysis)
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = get_data_scientist_prompt(current_date=current_date)

        context_messages = [SystemMessage(content=system_prompt)]

        # Add task as HumanMessage with completion instructions
        if task_content:
            context_messages.append(HumanMessage(content=f"""{task_content}

IMPORTANT COMPLETION INSTRUCTIONS:
- After analyzing data and writing findings, provide a final summary
- When you are done, respond WITHOUT making any tool calls
- Do not continue analyzing after writing your analysis
- A simple summary response with no tool calls will complete the task"""))
        else:
            context_messages.append(HumanMessage(content="Please proceed with the data analysis task."))

        # Use ainvoke to get complete response with valid tool_call_ids
        model_with_tools = model.bind_tools(production_tools)
        response = await model_with_tools.ainvoke(context_messages)
        return {"messages": [response]}

    def data_scientist_tools_node(state: SupervisorAgentState):
        """Data scientist subagent tool execution node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        results = []
        for idx, tool_call in enumerate(last_message.tool_calls):

            try:

                tool_call_id = tool_call.get("id")

                tool_name = tool_call.get('name', 'unknown_tool')

                if not tool_call_id:

                    tool_call_id = f"fallback_{tool_name}_{idx}"

                    logger.warning(f"[Data scientist Tools] Missing tool_call_id for {tool_name}. Generated fallback: {tool_call_id}")

                result_message = ToolMessage(

                    content=f"Data scientist tool {tool_name} executed",

                    tool_call_id=tool_call_id,

                )

                results.append(result_message)

            except Exception as e:

                logger.error(f"[Data scientist Tools] Error creating ToolMessage for tool_call {idx}: {e}")

                continue

        return {"messages": results}

    # ========================================================================
    # SUBAGENT NODES: EXPERT ANALYST
    # ========================================================================

    async def expert_analyst_agent_node(state: SupervisorAgentState):
        """Expert analyst subagent reasoning node with optimized prompt"""
        messages = state["messages"]

        # Extract task from delegation tool call
        task_content = None
        for msg in reversed(messages):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get("name") == "delegate_to_expert_analyst":
                        task_content = tc.get("args", {}).get("task")
                        break
            if task_content:
                break

        # Use optimized expert analyst prompt (250 lines, Decision→Plan→Execute→Judge workflow)
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = get_expert_analyst_prompt(current_date=current_date)

        context_messages = [SystemMessage(content=system_prompt)]

        # Add task as HumanMessage with completion instructions
        if task_content:
            context_messages.append(HumanMessage(content=f"""{task_content}

IMPORTANT COMPLETION INSTRUCTIONS:
- After completing strategic analysis and writing findings, provide a final summary
- When you are done, respond WITHOUT making any tool calls
- Do not continue analyzing after writing your analysis document
- A simple summary response with no tool calls will complete the task"""))
        else:
            context_messages.append(HumanMessage(content="Please proceed with the analysis task."))

        # Use ainvoke to get complete response with valid tool_call_ids
        model_with_tools = model.bind_tools(production_tools)
        response = await model_with_tools.ainvoke(context_messages)
        return {"messages": [response]}

    def expert_analyst_tools_node(state: SupervisorAgentState):
        """Expert analyst subagent tool execution node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        results = []
        for idx, tool_call in enumerate(last_message.tool_calls):

            try:

                tool_call_id = tool_call.get("id")

                tool_name = tool_call.get('name', 'unknown_tool')

                if not tool_call_id:

                    tool_call_id = f"fallback_{tool_name}_{idx}"

                    logger.warning(f"[Expert analyst Tools] Missing tool_call_id for {tool_name}. Generated fallback: {tool_call_id}")

                result_message = ToolMessage(

                    content=f"Expert analyst tool {tool_name} executed",

                    tool_call_id=tool_call_id,

                )

                results.append(result_message)

            except Exception as e:

                logger.error(f"[Expert analyst Tools] Error creating ToolMessage for tool_call {idx}: {e}")

                continue

        return {"messages": results}

    # ========================================================================
    # SUBAGENT NODES: WRITER
    # ========================================================================

    async def writer_agent_node(state: SupervisorAgentState):
        """Writer subagent reasoning node with optimized prompt"""
        messages = state["messages"]

        # Extract task from delegation tool call
        task_content = None
        for msg in reversed(messages):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get("name") == "delegate_to_writer":
                        task_content = tc.get("args", {}).get("task")
                        break
            if task_content:
                break

        # Use optimized writer prompt (300 lines, multi-stage writing workflow)
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = get_writer_prompt(current_date=current_date)

        context_messages = [SystemMessage(content=system_prompt)]

        # Add task as HumanMessage with completion instructions
        if task_content:
            context_messages.append(HumanMessage(content=f"""{task_content}

IMPORTANT COMPLETION INSTRUCTIONS:
- After completing the writing and saving the document, provide a final summary
- When you are done, respond WITHOUT making any tool calls
- Do not continue writing or revising after completing the document
- A simple summary response with no tool calls will complete the task"""))
        else:
            context_messages.append(HumanMessage(content="Please proceed with the writing task."))

        # Use ainvoke to get complete response with valid tool_call_ids
        model_with_tools = model.bind_tools(production_tools)
        response = await model_with_tools.ainvoke(context_messages)
        return {"messages": [response]}

    def writer_tools_node(state: SupervisorAgentState):
        """Writer subagent tool execution node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        results = []
        for idx, tool_call in enumerate(last_message.tool_calls):

            try:

                tool_call_id = tool_call.get("id")

                tool_name = tool_call.get('name', 'unknown_tool')

                if not tool_call_id:

                    tool_call_id = f"fallback_{tool_name}_{idx}"

                    logger.warning(f"[Writer Tools] Missing tool_call_id for {tool_name}. Generated fallback: {tool_call_id}")

                result_message = ToolMessage(

                    content=f"Writer tool {tool_name} executed",

                    tool_call_id=tool_call_id,

                )

                results.append(result_message)

            except Exception as e:

                logger.error(f"[Writer Tools] Error creating ToolMessage for tool_call {idx}: {e}")

                continue

        return {"messages": results}

    # ========================================================================
    # SUBAGENT NODES: REVIEWER
    # ========================================================================

    async def reviewer_agent_node(state: SupervisorAgentState):
        """Reviewer subagent reasoning node with optimized prompt"""
        messages = state["messages"]

        # Extract task from delegation tool call
        task_content = None
        for msg in reversed(messages):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get("name") == "delegate_to_reviewer":
                        task_content = tc.get("args", {}).get("task")
                        break
            if task_content:
                break

        # Use optimized reviewer prompt (300 lines, quality criteria & gap identification)
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = get_reviewer_prompt(current_date=current_date)

        context_messages = [SystemMessage(content=system_prompt)]

        # Add task as HumanMessage with completion instructions
        if task_content:
            context_messages.append(HumanMessage(content=f"""{task_content}

IMPORTANT COMPLETION INSTRUCTIONS:
- After completing the review and writing your findings, provide a final summary
- When you are done, respond WITHOUT making any tool calls
- Do not continue reviewing after writing your review document
- A simple summary response with no tool calls will complete the task"""))
        else:
            context_messages.append(HumanMessage(content="Please proceed with the review task."))

        # Use ainvoke to get complete response with valid tool_call_ids
        model_with_tools = model.bind_tools(production_tools)
        response = await model_with_tools.ainvoke(context_messages)
        return {"messages": [response]}

    def reviewer_tools_node(state: SupervisorAgentState):
        """Reviewer subagent tool execution node"""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        results = []
        for idx, tool_call in enumerate(last_message.tool_calls):

            try:

                tool_call_id = tool_call.get("id")

                tool_name = tool_call.get('name', 'unknown_tool')

                if not tool_call_id:

                    tool_call_id = f"fallback_{tool_name}_{idx}"

                    logger.warning(f"[Reviewer Tools] Missing tool_call_id for {tool_name}. Generated fallback: {tool_call_id}")

                result_message = ToolMessage(

                    content=f"Reviewer tool {tool_name} executed",

                    tool_call_id=tool_call_id,

                )

                results.append(result_message)

            except Exception as e:

                logger.error(f"[Reviewer Tools] Error creating ToolMessage for tool_call {idx}: {e}")

                continue

        return {"messages": results}

    # ========================================================================
    # ROUTING FUNCTIONS
    # ========================================================================

    def should_continue_researcher(state: SupervisorAgentState) -> Literal["researcher_tools", "end"]:
        """
        Route Researcher agent to tools or end.

        - researcher_tools: Researcher made tool calls (execute tools, loop back)
        - end: No tool calls, research complete
        """
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_message = messages[-1]

        # Check if last message has tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "researcher_tools"

        return "end"


    def should_continue_data_scientist(state: SupervisorAgentState) -> Literal["data_scientist_tools", "end"]:
        """
        Route Data Scientist agent to tools or end.

        - data_scientist_tools: Data Scientist made tool calls (execute tools, loop back)
        - end: No tool calls, analysis complete
        """
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_message = messages[-1]

        # Check if last message has tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "data_scientist_tools"

        return "end"


    def should_continue_expert_analyst(state: SupervisorAgentState) -> Literal["expert_analyst_tools", "end"]:
        """
        Route Expert Analyst agent to tools or end.

        - expert_analyst_tools: Expert Analyst made tool calls (execute tools, loop back)
        - end: No tool calls, analysis complete
        """
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_message = messages[-1]

        # Check if last message has tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "expert_analyst_tools"

        return "end"


    def should_continue_writer(state: SupervisorAgentState) -> Literal["writer_tools", "end"]:
        """
        Route Writer agent to tools or end.

        - writer_tools: Writer made tool calls (execute tools, loop back)
        - end: No tool calls, writing complete
        """
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_message = messages[-1]

        # Check if last message has tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "writer_tools"

        return "end"


    def should_continue_reviewer(state: SupervisorAgentState) -> Literal["reviewer_tools", "end"]:
        """
        Route Reviewer agent to tools or end.

        - reviewer_tools: Reviewer made tool calls (execute tools, loop back)
        - end: No tool calls, review complete
        """
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_message = messages[-1]

        # Check if last message has tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "reviewer_tools"

        return "end"


    def should_continue_after_delegation(state: SupervisorAgentState) -> Literal[
        "researcher_agent",
        "data_scientist_agent",
        "expert_analyst_agent",
        "writer_agent",
        "reviewer_agent",
        "end"
    ]:
        """
        Route to appropriate subagent based on which delegation tool was called.

        Checks the second-to-last message for the delegation tool call name,
        then routes to the corresponding subagent node.

        This function provides explicit routing for delegation tools, enabling
        reliable multi-agent delegation without relying on Command.goto pattern.
        """
        messages = state.get("messages", [])
        if len(messages) < 2:
            return "end"

        # Check second-to-last message (before ToolMessage) for tool call
        prev_msg = messages[-2]
        if hasattr(prev_msg, "tool_calls") and prev_msg.tool_calls:
            tool_name = prev_msg.tool_calls[0].get("name", "")

            # Route based on delegation tool called
            if tool_name == "delegate_to_researcher":
                return "researcher_agent"
            elif tool_name == "delegate_to_data_scientist":
                return "data_scientist_agent"
            elif tool_name == "delegate_to_expert_analyst":
                return "expert_analyst_agent"
            elif tool_name == "delegate_to_writer":
                return "writer_agent"
            elif tool_name == "delegate_to_reviewer":
                return "reviewer_agent"

        return "end"

    # ========================================================================
    # BUILD UNIFIED WORKFLOW
    # ========================================================================

    workflow = StateGraph(SupervisorAgentState)

    # Wrap all agent nodes with ACE middleware for reflection and playbook injection
    wrapped_supervisor = ace_middleware.wrap_node(agent_node, agent_type="supervisor")
    wrapped_researcher_unified = ace_middleware.wrap_node(researcher_agent_node, agent_type="researcher")
    wrapped_data_scientist_unified = ace_middleware.wrap_node(data_scientist_agent_node, agent_type="data_scientist")
    wrapped_expert_analyst_unified = ace_middleware.wrap_node(expert_analyst_agent_node, agent_type="expert_analyst")
    wrapped_writer_unified = ace_middleware.wrap_node(writer_agent_node, agent_type="writer")
    wrapped_reviewer_unified = ace_middleware.wrap_node(reviewer_agent_node, agent_type="reviewer")

    # Add main agent nodes (use ACE-wrapped versions)
    workflow.add_node("agent", wrapped_supervisor)
    # Phase 1.1: Separate tools nodes for Supervisor
    workflow.add_node("delegation_tools", delegation_tools_node)
    workflow.add_node("supervisor_production_tools", supervisor_production_tools_node)

    # Add all subagent nodes (use ACE-wrapped versions)
    workflow.add_node("researcher_agent", wrapped_researcher_unified)
    # Phase 1.2: Use dedicated tools node for researcher
    workflow.add_node("researcher_tools", researcher_tools_node_unified)

    workflow.add_node("data_scientist_agent", wrapped_data_scientist_unified)
    # Phase 1.2: Use dedicated tools node for data scientist
    workflow.add_node("data_scientist_tools", data_scientist_tools_node_unified)

    workflow.add_node("expert_analyst_agent", wrapped_expert_analyst_unified)
    # Phase 1.2: Use dedicated tools node for expert analyst
    workflow.add_node("expert_analyst_tools", expert_analyst_tools_node_unified)

    workflow.add_node("writer_agent", wrapped_writer_unified)
    # Phase 1.2: Use dedicated tools node for writer
    workflow.add_node("writer_tools", writer_tools_node_unified)

    workflow.add_node("reviewer_agent", wrapped_reviewer_unified)
    # Phase 1.2: Use dedicated tools node for reviewer
    workflow.add_node("reviewer_tools", reviewer_tools_node_unified)

    # Set entry point
    workflow.set_entry_point("agent")

    # Main agent routing - simplified for Command.goto pattern
    # Command.goto from delegation tools handles routing to subagent nodes dynamically
    # Phase 1.3: Route to separate tools nodes based on tool type
    workflow.add_conditional_edges(
        "agent",
        should_continue_supervisor,
        {
            "delegation_tools": "delegation_tools",
            "supervisor_production_tools": "supervisor_production_tools",
            "end": END,
        },
    )

    # Phase 1.1: Edge configuration for separate tools nodes
    # Production tools loop back to agent for continued reasoning
    workflow.add_edge("supervisor_production_tools", "agent")

    # Phase 1.2: Delegation tools routing - conditional edges route to appropriate subagent
    workflow.add_conditional_edges(
        "delegation_tools",
        should_continue_after_delegation,
        {
            "researcher_agent": "researcher_agent",
            "data_scientist_agent": "data_scientist_agent",
            "expert_analyst_agent": "expert_analyst_agent",
            "writer_agent": "writer_agent",
            "reviewer_agent": "reviewer_agent",
            "end": END,
        }
    )

    # Phase 1.4: Individual routing for each subagent (independent reasoning loops)

    # Researcher routing
    workflow.add_conditional_edges(
        "researcher_agent",
        should_continue_researcher,
        {
            "researcher_tools": "researcher_tools",
            "end": END,
        },
    )
    # Researcher tools → back to researcher agent (for continued reasoning)
    workflow.add_edge("researcher_tools", "researcher_agent")

    # Data Scientist routing
    workflow.add_conditional_edges(
        "data_scientist_agent",
        should_continue_data_scientist,
        {
            "data_scientist_tools": "data_scientist_tools",
            "end": END,
        },
    )
    # Data Scientist tools → back to data scientist agent (for continued reasoning)
    workflow.add_edge("data_scientist_tools", "data_scientist_agent")

    # Expert Analyst routing
    workflow.add_conditional_edges(
        "expert_analyst_agent",
        should_continue_expert_analyst,
        {
            "expert_analyst_tools": "expert_analyst_tools",
            "end": END,
        },
    )
    # Expert Analyst tools → back to expert analyst agent (for continued reasoning)
    workflow.add_edge("expert_analyst_tools", "expert_analyst_agent")

    # Writer routing
    workflow.add_conditional_edges(
        "writer_agent",
        should_continue_writer,
        {
            "writer_tools": "writer_tools",
            "end": END,
        },
    )
    # Writer tools → back to writer agent (for continued reasoning)
    workflow.add_edge("writer_tools", "writer_agent")

    # Reviewer routing
    workflow.add_conditional_edges(
        "reviewer_agent",
        should_continue_reviewer,
        {
            "reviewer_tools": "reviewer_tools",
            "end": END,
        },
    )
    # Reviewer tools → back to reviewer agent (for continued reasoning)
    workflow.add_edge("reviewer_tools", "reviewer_agent")

    return workflow.compile(checkpointer=active_checkpointer)


# Compile unified graph (will be re-compiled with PostgreSQL checkpointer in main.py)
supervisor_agent_unified = create_unified_graph()


# ============================================================================
# FULL EXPORTS - ALL GRAPHS
# ============================================================================

# Export all 7 graphs for langgraph.json
__all__ = [
    "supervisor_agent_unified",  # Unified view with all subagents as nodes
    "supervisor_graph",  # Simplified overview
    "researcher_graph",
    "data_scientist_graph",
    "expert_analyst_graph",
    "writer_graph",
    "reviewer_graph",
]


# ============================================================================
# NOTES FOR FUTURE EXPANSION
# ============================================================================

"""
To add remaining 4 subagent graphs:

1. Copy researcher_graph template
2. Rename functions (e.g., data_scientist_agent_node)
3. In full implementation, use subagent-specific tools/model
4. Export: data_scientist_graph, expert_analyst_graph, writer_graph, reviewer_graph
5. Add to langgraph.json graphs section

All subagents follow SAME structure:
- agent → tools → end
- tools → agent → end

Specialization comes from:
- Different tools available (researcher has web_search + citation tools, etc.)
- Different system prompts
- Different model configs (optional)
"""
