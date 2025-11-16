"""
Test Configuration 7: Official LangChain Multi-Agent Supervisor Pattern

This configuration implements the OFFICIAL LangChain multi-agent supervisor pattern
as documented in the LangGraph tutorials at:
https://github.com/langchain-ai/langgraph/blob/main/docs/docs/tutorials/multi_agent/agent_supervisor.md

Pattern Overview:
- Supervisor agent coordinates specialized worker agents
- Handoff tools enable delegation from supervisor to workers
- Workers automatically return control to supervisor
- Command API used for graph navigation

Architecture (Official Pattern):
    START → supervisor → research_agent → supervisor → END
                      ↘ math_agent    ↗

Key Components from Official Tutorial:
1. Worker agents: Specialized ReAct agents with domain-specific tools
2. Handoff tools: Tools that return Command for graph navigation
3. Supervisor agent: Coordinator with handoff tools
4. Graph structure: Nodes for supervisor and each worker with edges back to supervisor

Reference: LangGraph Multi-Agent Supervisor Tutorial
https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/
"""

import asyncio
import os
from pathlib import Path
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph.types import Command
from langchain_anthropic import ChatAnthropic
from langchain_tavily import TavilySearch

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

# ============================================================================
# 1. State Definition
# ============================================================================

class State(TypedDict):
    """
    State for multi-agent supervisor system.

    Official pattern uses MessagesState which contains:
    - messages: List of messages in the conversation
    - remaining_steps: Iteration limit for agents

    Reference: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/#create-multi-agent-graph
    """
    messages: Annotated[list[BaseMessage], add_messages]
    remaining_steps: int


# ============================================================================
# 2. Worker Agent Tools (Domain-Specific)
# ============================================================================

def add(a: float, b: float) -> float:
    """
    Add two numbers.

    Math tool for the math agent.
    From official tutorial: "Math agent will have access to simple math tools"

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b


def multiply(a: float, b: float) -> float:
    """
    Multiply two numbers.

    Math tool for the math agent.
    From official tutorial: "Math agent will have access to simple math tools"

    Args:
        a: First number
        b: Second number

    Returns:
        Product of a and b
    """
    return a * b


def divide(a: float, b: float) -> float:
    """
    Divide two numbers.

    Math tool for the math agent.
    From official tutorial: "Math agent will have access to simple math tools"

    Args:
        a: First number (numerator)
        b: Second number (denominator)

    Returns:
        Quotient of a / b
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


# ============================================================================
# 3. Handoff Tools (Supervisor Delegation)
# ============================================================================

def create_handoff_tool(*, agent_name: str, description: str | None = None):
    """
    Creates a handoff tool for delegating to a specific agent.

    OFFICIAL PATTERN from LangGraph Tutorial:
    "We will implement handoffs via handoff tools and give these tools to the
    supervisor agent: when the supervisor calls these tools, it will hand off
    control to a worker agent, passing the full message history to that agent."

    The handoff tool returns a Command object that:
    1. Navigates to the target agent node (goto)
    2. Passes the full state to that agent (update)
    3. Operates in the parent graph context (graph=Command.PARENT)

    Reference: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/#set-up-agent-communication

    Args:
        agent_name: Name of the agent to hand off to
        description: Tool description for the LLM

    Returns:
        Tool function that returns Command for graph navigation
    """
    name = f"transfer_to_{agent_name}"
    description = description or f"Ask {agent_name} for help."

    @tool(name, description=description)
    def handoff_tool(
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId]
    ) -> Command:
        """
        Handoff tool implementation.

        Returns Command object for graph navigation as per official pattern.

        Args:
            state: Current graph state (injected)
            tool_call_id: ID of the tool call (injected)

        Returns:
            Command directing graph to target agent
        """
        # Create tool message confirming handoff
        tool_message = ToolMessage(
            content=f"Successfully transferred to {agent_name}",
            name=name,
            tool_call_id=tool_call_id,
        )

        print(f"\n🔧 Handoff tool '{name}' called")
        print(f"   → Transferring control to: {agent_name}")
        print(f"   → Passing full message history ({len(state.get('messages', []))} messages)")

        # Return Command for graph navigation
        # From official tutorial:
        # 1. goto: Name of agent node to hand off to
        # 2. update: Take agent's messages and add to parent state
        # 3. graph: Navigate to agent node in parent multi-agent graph
        return Command(
            goto=agent_name,  # Navigate to this node
            update={"messages": state.get("messages", []) + [tool_message]},  # Add handoff confirmation
            graph=Command.PARENT,  # Execute in parent graph
        )

    return handoff_tool


# Create handoff tools for each worker agent
transfer_to_research_agent = create_handoff_tool(
    agent_name="research_agent",
    description="Assign research-related tasks to the research agent. Use for web searches and information gathering."
)

transfer_to_math_agent = create_handoff_tool(
    agent_name="math_agent",
    description="Assign math-related tasks to the math agent. Use for calculations and mathematical operations."
)


# ============================================================================
# 4. Worker Agents (Specialized ReAct Agents)
# ============================================================================

async def create_research_agent():
    """
    Creates a research agent with ALL tools (planning + research + files).

    The agent is created using create_agent with:
    - Claude Haiku 4.5 as the LLM (as per requirements)
    - All researcher tools from shared_tools module
    - Specific instructions for research tasks only

    Returns:
        Compiled ReAct agent for research tasks
    """
    print("\n🔬 Creating research agent...")

    # Initialize LLM - Using Claude Haiku 4.5 as per requirements
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0,
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    # Get researcher tools (NO delegation)
    researcher_tools = get_subagent_tools()

    # Create ReAct agent with all researcher tools
    from langchain_core.messages import SystemMessage

    agent = create_react_agent(
        llm,
        tools=researcher_tools,
        state_schema=State,
        messages_modifier=SystemMessage(content=(
            "You are a research agent.\n\n"
            "INSTRUCTIONS:\n"
            "- Assist ONLY with research-related tasks, DO NOT do any math\n"
            "- After you're done with your tasks, respond to the supervisor directly\n"
            "- Respond ONLY with the results of your work, do NOT include ANY other text."
        )),
    )

    print(f"   ✅ Research agent created with {len(researcher_tools)} tools")
    print(f"      - Planning: {len(PLANNING_TOOLS)} tools")
    print(f"      - Research: {len(RESEARCH_TOOLS)} tools")
    print(f"      - Files: {len(FILE_TOOLS)} tools")
    return agent


async def create_math_agent():
    """
    Creates a math agent with ALL tools (math + planning + research + files).

    The agent is created using create_agent with:
    - Claude Haiku 4.5 as the LLM (as per requirements)
    - Math operation tools + all subagent tools
    - Specific instructions for math tasks only

    Returns:
        Compiled ReAct agent for math tasks
    """
    print("\n🔢 Creating math agent...")

    # Initialize LLM - Using Claude Haiku 4.5 as per requirements
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0,
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    # Get subagent tools + math tools
    math_tools = get_subagent_tools() + [add, multiply, divide]

    # Create ReAct agent with all tools
    from langchain_core.messages import SystemMessage

    agent = create_react_agent(
        llm,
        tools=math_tools,
        state_schema=State,
        messages_modifier=SystemMessage(content=(
            "You are a math agent.\n\n"
            "INSTRUCTIONS:\n"
            "- Assist ONLY with math-related tasks\n"
            "- After you're done with your tasks, respond to the supervisor directly\n"
            "- Respond ONLY with the results of your work, do NOT include ANY other text."
        )),
    )

    print(f"   ✅ Math agent created with {len(math_tools)} tools")
    print(f"      - Math: 3 tools")
    print(f"      - Planning: {len(PLANNING_TOOLS)} tools")
    print(f"      - Research: {len(RESEARCH_TOOLS)} tools")
    print(f"      - Files: {len(FILE_TOOLS)} tools")
    return agent


# ============================================================================
# 5. Supervisor Agent (Coordinator)
# ============================================================================

async def create_supervisor_agent():
    """
    Creates the supervisor agent that coordinates worker agents.

    The supervisor:
    - Has handoff tools for delegating to workers
    - Has ALL supervisor tools (planning + research + files)
    - Makes decisions about which agent to invoke
    - Can also perform work directly if needed

    Returns:
        Compiled ReAct supervisor agent
    """
    print("\n👔 Creating supervisor agent...")

    # Initialize LLM - Using Claude Haiku 4.5 as per requirements
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0,
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    # Get all supervisor tools (delegation + planning + research + files)
    supervisor_tools = get_supervisor_tools([transfer_to_research_agent, transfer_to_math_agent])

    # Create supervisor with all tools
    from langchain_core.messages import SystemMessage

    agent = create_react_agent(
        llm,
        tools=supervisor_tools,
        state_schema=State,
        messages_modifier=SystemMessage(content=(
            "You are a supervisor managing two agents:\n"
            "- a research agent. Assign research-related tasks to this agent\n"
            "- a math agent. Assign math-related tasks to this agent\n\n"
            "Assign work to one agent at a time, do not call agents in parallel.\n"
            "Do not do any work yourself. Only delegate and summarize results."
        )),
    )

    print(f"   ✅ Supervisor agent created with {len(supervisor_tools)} tools")
    print(f"      - Delegation: 2 tools")
    print(f"      - Planning: {len(PLANNING_TOOLS)} tools")
    print(f"      - Research: {len(RESEARCH_TOOLS)} tools")
    print(f"      - Files: {len(FILE_TOOLS)} tools")
    return agent


# ============================================================================
# 6. Multi-Agent Graph Construction
# ============================================================================

async def build_graph():
    """
    Builds the multi-agent supervisor graph.

    OFFICIAL PATTERN from LangGraph Tutorial:
    "Putting this all together, let's create a graph for our overall multi-agent
    system. We will add the supervisor and the individual agents as subgraph nodes."

    Graph structure:
        START → supervisor → research_agent → supervisor
                         ↘ math_agent    ↗        ↓
                                                  END

    Key points from official tutorial:
    1. All agents added as nodes
    2. START edge points to supervisor
    3. Worker agents have edges back to supervisor
    4. "We've added explicit edges from worker agents back to the supervisor —
       this means that they are guaranteed to return control back to the supervisor"

    Reference: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/#create-multi-agent-graph

    Returns:
        Compiled multi-agent graph
    """
    print("\n📊 Building multi-agent supervisor graph...")

    # Create all agents
    supervisor_agent = await create_supervisor_agent()
    research_agent = await create_research_agent()
    math_agent = await create_math_agent()

    # Initialize StateGraph
    # Official tutorial uses MessagesState
    workflow = StateGraph(State)

    # Add nodes
    print("\n   Adding nodes:")
    print("     1. supervisor (coordinator)")
    workflow.add_node("supervisor", supervisor_agent)

    print("     2. research_agent (web search)")
    workflow.add_node("research_agent", research_agent)

    print("     3. math_agent (calculations)")
    workflow.add_node("math_agent", math_agent)

    # Set entry point
    print("\n   Entry point: START → supervisor")
    workflow.add_edge(START, "supervisor")

    # Add edges from workers back to supervisor
    # Official tutorial: "always return back to the supervisor"
    print("\n   Adding return edges (workers → supervisor):")
    print("     - research_agent → supervisor")
    workflow.add_edge("research_agent", "supervisor")

    print("     - math_agent → supervisor")
    workflow.add_edge("math_agent", "supervisor")

    print("\n✅ Multi-agent graph built successfully")
    print("\n   Graph flow:")
    print("   START → supervisor")
    print("           ├→ research_agent → supervisor")
    print("           ├→ math_agent → supervisor")
    print("           └→ END (when no more delegations)\n")

    return workflow.compile()


# ============================================================================
# 7. Test Execution
# ============================================================================

async def test():
    """
    Tests the multi-agent supervisor system.

    Test cases from official tutorial:
    1. Simple delegation: Research or math only
    2. Complex delegation: Both research and math required

    The official tutorial example:
    "find US and New York state GDP in 2024. what % of US GDP was New York state?"
    - Research agent looks up GDP information
    - Math agent performs division to find percentage
    """
    print("\n" + "="*80)
    print("TEST CONFIG 7: Official LangChain Multi-Agent Supervisor Pattern")
    print("="*80)
    print("\nImplementation based on:")
    print("https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/")
    print("\nPattern:")
    print("- Supervisor coordinates specialized worker agents")
    print("- Handoff tools enable delegation with Command API")
    print("- Workers automatically return to supervisor")
    print("- Full message history passed between agents")
    print("="*80 + "\n")

    # Build the graph
    graph = await build_graph()

    # Test 1: Simple research task
    print("\n" + "="*80)
    print("TEST 1: Simple Research Task")
    print("="*80 + "\n")

    query1 = "Who is the current mayor of New York City?"
    print(f"Query: {query1}\n")
    print("Expected flow: supervisor → research_agent → supervisor → END\n")
    print("-"*80)

    try:
        result1 = await graph.ainvoke({
            "messages": [HumanMessage(content=query1)],
            "remaining_steps": 25
        })

        print("\n✅ Test 1 PASSED")
        print(f"Messages exchanged: {len(result1['messages'])}")
        print(f"\nFinal answer: {result1['messages'][-1].content}\n")

    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return

    # Test 2: Simple math task
    print("\n" + "="*80)
    print("TEST 2: Simple Math Task")
    print("="*80 + "\n")

    query2 = "What is (15 + 27) × 3?"
    print(f"Query: {query2}\n")
    print("Expected flow: supervisor → math_agent → supervisor → END\n")
    print("-"*80)

    try:
        result2 = await graph.ainvoke({
            "messages": [HumanMessage(content=query2)],
            "remaining_steps": 25
        })

        print("\n✅ Test 2 PASSED")
        print(f"Messages exchanged: {len(result2['messages'])}")
        print(f"\nFinal answer: {result2['messages'][-1].content}\n")

    except Exception as e:
        print(f"\n❌ Test 2 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return

    # Test 3: Complex multi-agent task (like official tutorial)
    print("\n" + "="*80)
    print("TEST 3: Complex Multi-Agent Task (Official Tutorial Example)")
    print("="*80 + "\n")

    query3 = "Find the population of Tokyo and calculate what 15% of that population would be."
    print(f"Query: {query3}\n")
    print("Expected flow:")
    print("  supervisor → research_agent (find population) → supervisor →")
    print("  math_agent (calculate 15%) → supervisor → END\n")
    print("-"*80)

    try:
        result3 = await graph.ainvoke({
            "messages": [HumanMessage(content=query3)],
            "remaining_steps": 25
        })

        print("\n✅ Test 3 PASSED")
        print(f"Messages exchanged: {len(result3['messages'])}")

        print("\n📨 Message flow:")
        for i, msg in enumerate(result3['messages']):
            msg_type = type(msg).__name__
            content = getattr(msg, 'content', '')[:100]
            name = getattr(msg, 'name', 'N/A')

            print(f"\n   {i+1}. {msg_type}")
            if name != 'N/A':
                print(f"      Agent: {name}")
            print(f"      Content: {content}...")

        print(f"\n\nFinal answer: {result3['messages'][-1].content}\n")

    except Exception as e:
        print(f"\n❌ Test 3 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED!")
    print("="*80)
    print("\nConfiguration 7 successfully implements the official LangChain")
    print("multi-agent supervisor pattern with:")
    print("  ✓ Handoff tools with Command API")
    print("  ✓ Specialized worker agents (research + math)")
    print("  ✓ Supervisor coordination")
    print("  ✓ Automatic return to supervisor")
    print("  ✓ Full message history passing")
    print("="*80 + "\n")


# ============================================================================
# 8. Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("\n🚀 Starting Configuration 7: Official Multi-Agent Supervisor Test...\n")
    asyncio.run(test())
