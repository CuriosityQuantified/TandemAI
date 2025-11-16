"""
Test Configuration 4: ReAct Supervisor with Conditional Edges

This configuration implements the traditional LangGraph pre-v1.0 pattern:
- Supervisor: Custom node with LLM + tool binding (NOT full ReAct agent)
- Subagents: Base ReAct agents (researcher only)
- Routing: Conditional edges with routing function
- Pattern: Tool calls return ToolMessage, not Command

Key Architecture:
    START → supervisor (LLM node) → delegation_tools (ToolNode)
                                       ↓ (conditional edge via routing function)
                                    researcher (ReAct) → END

Flow:
    1. User message → supervisor
    2. Supervisor (LLM) calls delegate_research tool → returns AIMessage with tool_calls
    3. delegation_tools node executes tool → returns ToolMessage
    4. Routing function inspects ToolMessage → routes to researcher
    5. Researcher executes research → returns result
    6. END

Key Difference from Config 3:
    - Config 3: Tools return Command (LangGraph v1.0+ pattern)
    - Config 4: Tools return ToolMessage, conditional edge routes (pre-v1.0 pattern)

The routing function inspects the last ToolMessage to determine the next node.
"""

import asyncio
import os
from pathlib import Path
from typing import Literal, TypedDict, Annotated, Callable
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain.agents import create_agent
from langgraph.prebuilt import ToolNode
from langchain_anthropic import ChatAnthropic

# Load environment variables from root .env
env_path = Path(__file__).parent.parent.parent / ".env"  # Up 3 levels to TandemAI root
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

# Verify API key is loaded
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise ValueError(f"ANTHROPIC_API_KEY not found. Tried loading from: {env_path}")

# ============================================================================
# 1. State Definition
# ============================================================================

class State(TypedDict):
    """State for supervisor-subagent delegation with traditional routing"""
    messages: Annotated[list[BaseMessage], add_messages]


# ============================================================================
# 2. TOOLS SETUP
# ============================================================================

# Create delegation tool using shared tools
# Note: For this config we're using traditional routing, so we just use the function directly
# This creates a tool named "delegate_to_researcher"
delegate_to_researcher = create_delegation_tool(
    agent_name="researcher",
    agent_description="Research agent for web search and information gathering",
    target_node="researcher"
)

# Get ALL tools for supervisor (delegation + planning + research + files)
supervisor_tools = get_supervisor_tools([delegate_to_researcher])

# Get ALL tools for researcher (planning + research + files, NO delegation)
researcher_tools = get_subagent_tools()

print(f"\n✓ Tools configured:")
print(f"  - Supervisor tools: {len(supervisor_tools)} (delegation + planning + research + files)")
print(f"  - Researcher tools: {len(researcher_tools)} (planning + research + files, NO delegation)")


# ============================================================================
# 3. Routing Function (Conditional Edge Logic)
# ============================================================================

def route_after_delegation(state: State) -> Literal["researcher", "__end__"]:
    """
    Routing function for conditional edge after delegation_tools.

    Traditional LangGraph pattern: Inspect messages to determine routing.

    Flow:
    1. delegation_tools node executes tool calls from supervisor's AIMessage
    2. Creates ToolMessages with results
    3. This routing function inspects the state to determine next node

    We need to check BOTH:
    - The ToolMessage (result of tool execution)
    - The AIMessage that triggered it (to see which tool was called)

    Args:
        state: Current graph state

    Returns:
        Next node name or END constant
    """
    messages = state["messages"]

    print(f"\n🔀 Routing function called")
    print(f"   Total messages in state: {len(messages)}")

    # Look for delegate_research tool call in recent messages
    # Strategy: Check last few messages for AIMessage with delegate_research tool_call
    for i in range(len(messages) - 1, max(-1, len(messages) - 5), -1):
        msg = messages[i]
        msg_type = type(msg).__name__

        print(f"   Checking message {i}: {msg_type}")

        # Check AIMessage for tool_calls
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_name = tool_call.get('name', '')
                print(f"      Tool call found: {tool_name}")

                if tool_name == "delegate_to_researcher":
                    print(f"   ✅ Found delegate_to_researcher tool call!")
                    print(f"   → Routing to researcher")
                    return "researcher"

        # Also check ToolMessage name attribute
        if isinstance(msg, ToolMessage):
            tool_name = getattr(msg, "name", None)
            print(f"      ToolMessage name: {tool_name}")

            if tool_name == "delegate_to_researcher":
                print(f"   ✅ Found delegate_to_researcher ToolMessage!")
                print(f"   → Routing to researcher")
                return "researcher"

    # Default: end execution
    print(f"   ⚠️  No delegation found in recent messages")
    print(f"   → Routing to END")
    return "__end__"


# ============================================================================
# 4. Subagent: Researcher (Base ReAct Agent)
# ============================================================================

async def create_researcher_agent() -> Callable:
    """
    Creates a base ReAct researcher agent with ALL tools.

    Returns:
        Compiled ReAct agent graph
    """
    print("\n🔬 Creating researcher agent...")

    # Use Claude Haiku 4.5
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0,
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    # Create ReAct agent with all researcher tools
    agent = create_agent(llm, tools=researcher_tools)

    print(f"   ✅ Researcher agent created with {len(researcher_tools)} tools")
    print(f"      - Planning: {len(PLANNING_TOOLS)} tools")
    print(f"      - Research: {len(RESEARCH_TOOLS)} tools")
    print(f"      - Files: {len(FILE_TOOLS)} tools")
    return agent


# ============================================================================
# 5. Supervisor: Simple LLM Node with Tool Binding
# ============================================================================

async def supervisor_node(state: State) -> dict:
    """
    Supervisor node that decides which subagent to delegate to.

    This is NOT a full ReAct agent - it's just an LLM call with tool binding.
    This allows us to control the flow with conditional edges.

    Args:
        state: Current graph state

    Returns:
        Updated state with AIMessage containing tool_calls
    """
    print("\n👔 Supervisor node executing...")
    print(f"   Received {len(state['messages'])} messages")

    # Create LLM with tool binding
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0,
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    # Bind supervisor tools to LLM
    llm_with_tools = llm.bind_tools(supervisor_tools)

    # System message for supervisor - EMPHASIS ON DELEGATION
    system_msg = (
        "You are a SUPERVISOR that DELEGATES tasks to specialized subagents.\n\n"
        "CRITICAL RULES:\n"
        "1. You MUST ALWAYS delegate research tasks using the delegate_to_researcher tool\n"
        "2. DO NOT execute research yourself - that's the researcher's job\n"
        "3. DO NOT use planning tools - delegate to researcher who will plan\n"
        "4. Your ONLY job is to route tasks to the appropriate subagent\n\n"
        "When you receive a research query:\n"
        "→ Immediately call delegate_to_researcher with the query\n"
        "→ Let the researcher subagent handle all research operations\n\n"
        "You are a ROUTER, not an executor. Always delegate."
    )

    # Get the user's message
    messages = state["messages"]
    user_message = messages[0] if messages else HumanMessage(content="")

    print(f"   User query: {user_message.content[:100]}...")

    # Call LLM with tools
    response = await llm_with_tools.ainvoke([
        {"role": "system", "content": system_msg},
        user_message
    ])

    print(f"   Supervisor response has {len(response.tool_calls) if response.tool_calls else 0} tool calls")

    return {"messages": [response]}


# ============================================================================
# 6. Researcher Node Wrapper
# ============================================================================

async def researcher_node(state: State, researcher_agent: Callable) -> dict:
    """
    Wrapper for researcher subagent execution.

    Key: Creates a FRESH message history for researcher to avoid tool call conflicts.

    Args:
        state: Current graph state
        researcher_agent: The compiled researcher agent

    Returns:
        Updated state with researcher response
    """
    print("\n🔬 Researcher node executing...")
    print(f"   Received {len(state['messages'])} messages")

    # Extract the research query from the delegation ToolMessage
    query = "Unknown query"

    # Look back through messages to find the delegation
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) == "delegate_to_researcher":
            # Parse query from content - format: "✅ Task delegated to researcher: {query}\n..."
            content = msg.content
            if "Task delegated to researcher:" in content:
                # Extract everything between "researcher:" and the next newline or end
                parts = content.split("Task delegated to researcher:", 1)
                if len(parts) > 1:
                    query_part = parts[1].strip()
                    # Get first line (in case there are multiple lines)
                    query = query_part.split('\n')[0].strip()
            break

    print(f"   Research query: {query}")

    # IMPORTANT: Create fresh message history for researcher
    # This prevents tool call validation errors when researcher's internal ReAct
    # agent sees delegation tool_calls in its history
    result = await researcher_agent.ainvoke({
        "messages": [HumanMessage(content=query)]
    })

    # Extract researcher's response
    researcher_messages = result.get("messages", [])
    print(f"   Researcher returned {len(researcher_messages)} messages")

    # Return only the final AIMessage response
    # This gets appended to the main state
    return {
        "messages": [
            AIMessage(
                content=f"🔬 Research results: {researcher_messages[-1].content}",
                name="researcher"
            )
        ]
    }


# ============================================================================
# 7. Graph Construction
# ============================================================================

async def build_graph():
    """
    Builds the supervisor-subagent graph with conditional edges.

    Architecture:
        START → supervisor (LLM) → delegation_tools (ToolNode)
                                      ↓ (conditional edge)
                                   researcher (ReAct) → END

    Key Pattern:
        - Supervisor is a simple LLM node (NOT full ReAct agent)
        - Conditional edge uses routing function to inspect ToolMessage
        - Routes to researcher when delegate_research tool is called
        - Researcher completes task and ends flow

    Returns:
        Compiled graph
    """
    print("\n📊 Building graph with conditional edges...")

    # Create researcher agent
    researcher_agent = await create_researcher_agent()

    # Create state graph
    workflow = StateGraph(State)

    # Add nodes
    print("\n   Adding nodes:")

    print("     1. supervisor (LLM node with tool binding)")
    workflow.add_node("supervisor", supervisor_node)

    print("     2. delegation_tools (ToolNode)")
    delegation_tool_node = ToolNode(supervisor_tools)
    workflow.add_node("delegation_tools", delegation_tool_node)

    print("     3. researcher (ReAct agent)")
    async def researcher_wrapper(state: State) -> dict:
        return await researcher_node(state, researcher_agent)
    workflow.add_node("researcher", researcher_wrapper)

    # Set entry point
    print("\n   Entry point: supervisor")
    workflow.set_entry_point("supervisor")

    # Add edges
    print("\n   Adding edges:")

    print("     - supervisor → delegation_tools")
    workflow.add_edge("supervisor", "delegation_tools")

    print("     - delegation_tools → (conditional routing function)")
    workflow.add_conditional_edges(
        "delegation_tools",
        route_after_delegation,
        {
            "researcher": "researcher",
            "__end__": END
        }
    )

    print("     - researcher → END")
    workflow.add_edge("researcher", END)

    print("\n✅ Graph built successfully\n")

    return workflow.compile()


# ============================================================================
# 8. Test Execution
# ============================================================================

async def test():
    """Run the configuration 4 test"""
    print("\n" + "="*80)
    print("TEST CONFIG 4: ReAct Supervisor with Conditional Edges")
    print("="*80)
    print("\nPattern: Traditional LangGraph pre-v1.0 routing")
    print("- Delegation tools return ToolMessage (NOT Command)")
    print("- Conditional edge with routing function inspects tool_calls")
    print("- Supervisor: ReAct agent")
    print("- Subagent: ReAct agent (researcher)")
    print("="*80 + "\n")

    # Build graph
    graph = await build_graph()

    # Test query - EXPLICIT delegation instruction
    query = "What are the latest developments in quantum computing?"

    # Make it crystal clear: supervisor should delegate
    test_message = (
        f"Please delegate this research task to the researcher subagent: {query}\n\n"
        f"Step 1: Use delegate_to_researcher tool to pass this query to the researcher.\n"
        f"The researcher will then plan and execute the research."
    )

    print(f"\n🚀 Starting test with query: {query}")
    print(f"📝 Full test message:")
    print(f"   {test_message}\n")
    print("-"*80)

    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=test_message)]},
            {"recursion_limit": 50}
        )

        print("\n" + "="*80)
        print("✅ TEST PASSED!")
        print("="*80 + "\n")

        print("📋 Final state:")
        print(f"   Total messages: {len(result['messages'])}")
        print(f"   Message types: {[type(m).__name__ for m in result['messages']]}")

        print("\n📨 Message sequence:")
        for i, msg in enumerate(result['messages']):
            msg_type = type(msg).__name__
            content = getattr(msg, 'content', '')[:150]
            name = getattr(msg, 'name', 'N/A')
            tool_calls = getattr(msg, 'tool_calls', [])

            print(f"\n   {i+1}. {msg_type}")
            if name != 'N/A':
                print(f"      Name: {name}")
            if tool_calls:
                print(f"      Tool calls: {len(tool_calls)}")
                for tc in tool_calls:
                    print(f"        - {tc.get('name', 'unknown')}")
            print(f"      Content: {content}...")

        print("\n" + "="*80)
        print("Configuration 4 test completed successfully!")
        print("="*80 + "\n")

    except Exception as e:
        print("\n" + "="*80)
        print("❌ TEST FAILED!")
        print("="*80 + "\n")
        print(f"Error: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()


# ============================================================================
# 9. Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("\n🚀 Starting Configuration 4 Test...\n")
    asyncio.run(test())
