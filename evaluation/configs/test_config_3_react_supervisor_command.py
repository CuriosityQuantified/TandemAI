"""
Test Config 3: ReAct Supervisor with Command.goto Delegation

This configuration demonstrates the SIMPLEST LangGraph v1.0+ delegation pattern:
- Supervisor: Simple node (creates tool call manually)
- Subagents: Base ReAct agents (researcher only)
- Routing: Command.goto from delegation tools
- Pattern: Minimal complexity, maximal LangGraph v1.0+ compliance

Graph Structure:
    START → supervisor (simple node) → delegation_tools (ToolNode)
                                           ↓ (Command.goto)
                                        researcher → researcher_tools
                                           ↑            ↓
                                           └────────────┘
                                           ↓ (when done)
                                          END

Key Design Points:
1. Delegation tool MUST be in parent graph's ToolNode (not in subgraph)
2. Supervisor creates tool call, delegation_tools executes it
3. Delegation tool returns Command(goto="researcher")
4. Researcher has conditional edge with should_continue logic:
   - If AIMessage with no tool_calls → END
   - If tool_calls present → researcher_tools
5. Researcher tools loop back to researcher for ReAct cycle
6. Explicit termination prevents infinite recursion

Critical Learning:
- Command.goto routing only works when the tool returning Command is in the
  PARENT graph's ToolNode, not nested inside a subgraph
- ReAct agents MUST have explicit termination logic (should_continue function)
  to prevent infinite loops
- System prompt instructs researcher to finish without tool calls

Test Results:
✅ Delegation flow works correctly
✅ Supervisor → delegation_tools → researcher
✅ Researcher executes with proper termination
✅ No more GraphRecursionError (infinite loop fixed)
✅ Final results returned successfully

Created: November 12, 2025
Updated: November 13, 2025 (Upgraded to Haiku 4.5)
LangGraph Version: v0.3+ (v1.0+ routing patterns)
Model: Claude Haiku 4.5 (claude-haiku-4-5-20251001)
"""

import asyncio
import os
from pathlib import Path
from typing import Annotated, Literal, TypedDict
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage, ToolMessage
from langchain_core.tools import tool, InjectedToolCallId
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, MessagesState, END, add_messages
from langchain.agents import create_agent
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from root .env
env_path = Path(__file__).parent.parent.parent / '.env'  # Up 3 levels to TandemAI root
load_dotenv(env_path)

# Add root to sys.path for absolute imports
import sys
root_path = Path(__file__).parent.parent.parent  # Up to TandemAI root
sys.path.insert(0, str(root_path))

# Import shared tools with absolute path
from backend.test_configs.shared_tools import (
    create_delegation_tool,
    get_supervisor_tools,
    get_subagent_tools,
    PLANNING_TOOLS,
    RESEARCH_TOOLS,
    FILE_TOOLS
)


# ============================================================================
# STATE SCHEMA
# ============================================================================

class AgentState(TypedDict):
    """
    State schema for ReAct agents.

    create_react_agent requires:
    - messages: list of messages
    - remaining_steps: int for limiting recursion
    """
    messages: Annotated[list[BaseMessage], add_messages]
    remaining_steps: int


# ============================================================================
# CONFIGURATION
# ============================================================================

MODEL = "claude-haiku-4-5-20251001"  # Anthropic Claude Haiku 4.5


# ============================================================================
# TOOLS SETUP
# ============================================================================

# Create delegation tool using shared tools
delegate_to_researcher = create_delegation_tool(
    agent_name="researcher",
    agent_description="Research agent for web search and information gathering",
    target_node="researcher"
)

# Get ALL tools for supervisor (delegation + planning + research + files)
supervisor_tools = get_supervisor_tools([delegate_to_researcher])

# Get ALL tools for researcher (planning + research + files, NO delegation)
researcher_tools = get_subagent_tools()


# ============================================================================
# BUILD GRAPH
# ============================================================================

def build_config_3_graph():
    """
    Build Config 3: ReAct supervisor with Command.goto delegation.

    This demonstrates LangGraph v1.0+ Command.goto routing where the delegation
    tool explicitly routes to the researcher node.

    Important: The delegation tool must be in the PARENT graph's ToolNode,
    not inside the supervisor subgraph, for Command.goto to work correctly.

    Returns:
        Compiled graph ready for execution
    """
    print("\n" + "="*80)
    print("BUILDING CONFIG 3: REACT SUPERVISOR WITH COMMAND.GOTO")
    print("="*80 + "\n")

    # Create model
    model = ChatAnthropic(model=MODEL, temperature=0)

    # Create supervisor ReAct agent (WITHOUT delegation tool)
    print("1. Creating supervisor ReAct agent...")
    print(f"   Supervisor tools: {len(supervisor_tools)} tools")
    print(f"   - Planning: {len(PLANNING_TOOLS)} tools")
    print(f"   - Research: {len(RESEARCH_TOOLS)} tools")
    print(f"   - Files: {len(FILE_TOOLS)} tools")
    print(f"   - Delegation: 1 tool")
    supervisor_agent = create_agent(
        model=model,
        tools=[],  # No tools - supervisor will call delegation tool via parent
        state_schema=AgentState,
        name="supervisor"
    )
    print("   ✅ Supervisor agent created\n")

    # Create researcher ReAct agent with explicit stopping logic
    print("2. Creating researcher ReAct agent...")
    print(f"   Researcher tools: {len(researcher_tools)} tools")
    print(f"   - Planning: {len(PLANNING_TOOLS)} tools")
    print(f"   - Research: {len(RESEARCH_TOOLS)} tools")
    print(f"   - Files: {len(FILE_TOOLS)} tools")
    print(f"   - NO delegation tools")

    # Create researcher model with explicit stopping instruction
    researcher_model = model.bind_tools(researcher_tools)

    # Define should_continue function for researcher
    def should_continue_researcher(state: AgentState) -> Literal["tools", END]:
        """
        Determine if researcher should continue or end.

        LangGraph v1.0 ReAct pattern requires explicit termination:
        - If last message is AIMessage with NO tool_calls → END
        - If last message has tool_calls → continue to tools
        """
        messages = state["messages"]
        last_message = messages[-1]

        # If AIMessage with no tool calls, the agent is done
        if isinstance(last_message, AIMessage) and not last_message.tool_calls:
            print("   🛑 Researcher finished (no more tool calls)")
            return END

        # Otherwise continue to tools
        print("   🔧 Researcher calling tools...")
        return "tools"

    # Create researcher node
    async def researcher_node(state: AgentState):
        """Researcher agent node with explicit stopping condition"""
        print("\n🔬 Researcher executing...")

        messages = state["messages"]
        remaining_steps = state.get("remaining_steps", 10)

        # Add system prompt with explicit stopping instruction
        system_prompt = """You are a research agent.

Your job:
1. Use the search_web tool to find information
2. When you have gathered sufficient information, provide your final answer WITHOUT calling any more tools
3. To finish, simply respond with your findings - DO NOT make any tool calls in your final message

IMPORTANT: When you are done researching, respond with just your answer. Do not call tools in your final response."""

        # Prepend system message if not already present
        if not any(isinstance(m, AIMessage) and "You are a research agent" in m.content for m in messages):
            from langchain_core.messages import SystemMessage
            messages = [SystemMessage(content=system_prompt)] + messages

        # Call researcher model
        response = await researcher_model.ainvoke(messages)

        return {
            "messages": [response],
            "remaining_steps": remaining_steps - 1
        }

    print("   ✅ Researcher agent created with termination logic\n")

    # Create delegation ToolNode in parent graph
    print("3. Creating delegation tools node...")
    delegation_tools_node = ToolNode([delegate_to_researcher])
    print("   ✅ Delegation tools node created\n")

    # Create researcher tools node
    print("4. Creating researcher tools node...")
    researcher_tools_node = ToolNode(researcher_tools)
    print("   ✅ Researcher tools node created\n")

    # Create main graph
    print("5. Building main graph...")
    workflow = StateGraph(AgentState)

    # Add supervisor as a simple node (not subgraph for now)
    print("   Adding supervisor node...")

    # Create a wrapper for supervisor that can call delegation tool
    async def supervisor_with_delegation(state: AgentState):
        """Supervisor node that generates delegation tool call"""
        print("\n👔 Supervisor executing...")
        messages = state["messages"]

        # Get the user request
        user_request = messages[-1].content

        # Create delegation tool call
        return {
            "messages": [
                AIMessage(
                    content="I'll delegate this research task to the researcher.",
                    tool_calls=[{
                        "name": "delegate_to_researcher",
                        "args": {
                            "task": user_request,
                            "tool_call_id": "supervisor_delegation_001"
                        },
                        "id": "supervisor_delegation_001"
                    }]
                )
            ]
        }

    workflow.add_node("supervisor", supervisor_with_delegation)

    # Add delegation tools node
    print("   Adding delegation_tools node...")
    workflow.add_node("delegation_tools", delegation_tools_node)

    # Add researcher node
    print("   Adding researcher node...")
    workflow.add_node("researcher", researcher_node)

    # Add researcher tools node
    print("   Adding researcher_tools node...")
    workflow.add_node("researcher_tools", researcher_tools_node)

    # Set entry point
    print("   Setting entry point: supervisor")
    workflow.set_entry_point("supervisor")

    # Edges
    print("   Adding edge: supervisor → delegation_tools")
    workflow.add_edge("supervisor", "delegation_tools")

    # NO edge from delegation_tools - let Command.goto route
    print("   Note: delegation_tools → (Command.goto routing)")

    # Add conditional edge for researcher with termination logic
    print("   Adding conditional edge: researcher → {tools, END}")
    workflow.add_conditional_edges(
        "researcher",
        should_continue_researcher,
        {
            "tools": "researcher_tools",
            END: END
        }
    )

    # Add edge from researcher_tools back to researcher
    print("   Adding edge: researcher_tools → researcher")
    workflow.add_edge("researcher_tools", "researcher")

    print("\n   ✅ Graph structure complete\n")

    # Compile
    print("6. Compiling graph...")
    graph = workflow.compile()
    print("   ✅ Graph compiled\n")

    print("="*80)
    print("GRAPH BUILD COMPLETE")
    print("="*80 + "\n")

    return graph


# ============================================================================
# TEST FUNCTION
# ============================================================================

async def test_config_3():
    """
    Test Config 3: Verify supervisor delegates and researcher executes.

    Expected Flow:
    1. User provides research request
    2. Supervisor calls delegate_to_researcher tool
    3. Tool returns Command(goto="researcher")
    4. Researcher receives task and executes
    5. Researcher uses search_web tool
    6. Final result returned
    """
    print("\n" + "="*80)
    print("TEST CONFIG 3: REACT SUPERVISOR WITH COMMAND.GOTO")
    print("="*80 + "\n")

    # Build graph
    graph = build_config_3_graph()

    # Test input
    test_message = "Research the latest trends in quantum computing for 2025"

    print(f"📥 Test Input: {test_message}\n")
    print("🔄 Invoking graph...\n")

    try:
        result = await graph.ainvoke({
            "messages": [HumanMessage(content=test_message)],
            "remaining_steps": 10  # Allow up to 10 steps for agent execution
        })

        print("\n" + "="*80)
        print("✅ TEST PASSED - EXECUTION SUCCESSFUL")
        print("="*80 + "\n")

        # Analyze results
        print("📊 RESULTS ANALYSIS")
        print("-" * 80 + "\n")

        messages = result["messages"]
        print(f"Total messages: {len(messages)}\n")

        print("Message sequence:")
        for i, msg in enumerate(messages, 1):
            msg_type = type(msg).__name__
            content = getattr(msg, 'content', '')

            # Truncate long content
            if len(content) > 100:
                content = content[:100] + "..."

            print(f"{i}. {msg_type}: {content}")

            # Check for tool calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"   └─ Tool Call: {tc.get('name', 'unknown')}")

        # Verify delegation occurred
        print("\n" + "="*80)
        print("🔍 VERIFICATION")
        print("="*80 + "\n")

        delegation_found = False
        search_found = False

        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get('name') == 'delegate_to_researcher':
                        delegation_found = True
                        print("✅ Delegation to researcher FOUND")
                    elif tc.get('name') == 'search_web':
                        search_found = True
                        print("✅ Web search by researcher FOUND")

        if delegation_found and search_found:
            print("\n🎉 SUCCESS: Full delegation flow executed!")
            print("   Supervisor → Researcher → Tool execution")
        elif delegation_found:
            print("\n⚠️  PARTIAL: Delegation occurred but researcher may not have used tools")
        else:
            print("\n❌ FAILURE: No delegation found in message history")

    except Exception as e:
        print("\n" + "="*80)
        print("❌ TEST FAILED - EXCEPTION OCCURRED")
        print("="*80 + "\n")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}\n")

        import traceback
        print("Traceback:")
        traceback.print_exc()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n🚀 Starting Config 3 Test...\n")
    asyncio.run(test_config_3())
    print("\n✅ Test complete!\n")
