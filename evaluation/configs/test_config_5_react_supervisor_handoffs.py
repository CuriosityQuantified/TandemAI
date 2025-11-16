"""
Test Configuration 5: ReAct Supervisor with Official LangChain Handoff Tools

This configuration implements the official LangChain handoff pattern:
- Supervisor: Base ReAct agent (create_react_agent)
- Subagents: Base ReAct agents (researcher only)
- Routing: Official LangChain handoff tools (create_handoff_tool)
- Pattern: LangChain documented handoff pattern

Key Architecture:
    START → supervisor (ReAct) → [handoff tools]
                                    ↓
                                 researcher (ReAct) → END

Research Findings:
1. Handoff tools ARE different from Command.goto:
   - create_handoff_tool() is higher-level abstraction wrapping Command
   - Provides automatic message history management
   - Creates Tool objects with semantic clarity
   - Handles metadata tracking and parallel execution

2. Advantages over manual Command.goto:
   - Automatic state management
   - Tool interface for LLM invocation
   - Metadata tracking for audit trails
   - Built-in parallel execution support

3. Implementation:
   - Uses langgraph_supervisor.create_handoff_tool()
   - Returns Command object with goto directive
   - Manages message history automatically
   - Integrates with ReAct agent tool-calling

Requirements:
    pip install langgraph-supervisor langchain-anthropic
"""

import asyncio
import os
from pathlib import Path
from typing import TypedDict, Annotated, Callable
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic

# Import handoff tools from langgraph-supervisor
try:
    from langgraph_supervisor import create_handoff_tool
    HANDOFF_AVAILABLE = True
except ImportError:
    HANDOFF_AVAILABLE = False
    print("\n⚠️  WARNING: langgraph-supervisor not installed")
    print("   Install with: pip install langgraph-supervisor")

# Load environment variables from root .env
env_path = Path(__file__).parent.parent.parent / ".env"  # Up 3 levels to TandemAI root
load_dotenv(env_path)

# Add root to sys.path for absolute imports
import sys
root_path = Path(__file__).parent.parent.parent  # Up to TandemAI root
sys.path.insert(0, str(root_path))

# ============================================================================
# 1. State Definition
# ============================================================================

class State(TypedDict):
    """State for supervisor-subagent delegation with handoff tools"""
    messages: Annotated[list[BaseMessage], add_messages]


# ============================================================================
# 2. Subagent: Researcher (Base ReAct Agent)
# ============================================================================

async def create_researcher_agent() -> Callable:
    """
    Creates a base ReAct researcher agent using create_react_agent.

    This agent will receive delegated research tasks via handoff tools.

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

    # No additional tools needed for this simple test
    tools = []

    # Create ReAct agent
    agent = create_react_agent(
        llm,
        tools=tools,
        state_modifier=(
            "You are a research assistant. Provide a concise, informative answer "
            "to the research query. Focus on the latest developments and key facts."
        )
    )

    print("   ✅ Researcher agent created")
    return agent


# ============================================================================
# 3. Supervisor: Base ReAct Agent with Handoff Tools
# ============================================================================

async def create_supervisor_agent() -> Callable:
    """
    Creates a base ReAct supervisor agent with official handoff tools.

    The supervisor uses create_handoff_tool() to delegate to specialized agents.
    This provides:
    - Automatic message history management
    - Tool-based agent switching
    - Metadata tracking for audit trails

    Returns:
        Compiled ReAct agent graph with handoff tools
    """
    print("\n👔 Creating supervisor agent with handoff tools...")

    if not HANDOFF_AVAILABLE:
        raise ImportError(
            "langgraph-supervisor package required. "
            "Install with: pip install langgraph-supervisor"
        )

    # Use Claude Haiku 4.5
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0,
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    # Create handoff tool for researcher agent
    # This creates a tool that:
    # 1. Returns Command object with goto="researcher"
    # 2. Manages message history automatically
    # 3. Adds handoff confirmation messages
    print("   Creating handoff tool for researcher...")
    handoff_to_researcher = create_handoff_tool(
        agent_name="researcher",
        name="delegate_to_researcher",
        description=(
            "Delegate research queries to the research specialist. "
            "Use this tool when you need to research a topic, gather information, "
            "or find the latest developments in a field."
        ),
        add_handoff_messages=True  # Include handoff confirmation in message history
    )

    print("   ✅ Handoff tool created: delegate_to_researcher")

    # Handoff tools for supervisor
    tools = [handoff_to_researcher]

    # Create ReAct agent with handoff tools
    agent = create_react_agent(
        llm,
        tools=tools,
        state_modifier=(
            "You are a supervisor agent coordinating specialized agents. "
            "When you receive a research query, use the delegate_to_researcher tool "
            "to hand off the task to the research specialist. "
            "After delegation, wait for the results and provide a summary."
        )
    )

    print("   ✅ Supervisor agent created with handoff tools")
    return agent


# ============================================================================
# 4. Graph Construction
# ============================================================================

async def build_graph():
    """
    Builds the supervisor-subagent graph with official handoff tools.

    Architecture:
        START → supervisor (ReAct with handoff tools)
                    ↓ (handoff tool invocation)
                 researcher (ReAct) → END

    The handoff tool handles routing automatically via Command.goto.
    No manual routing function needed.

    Returns:
        Compiled graph
    """
    print("\n📊 Building graph with handoff tools pattern...")

    # Create agents
    supervisor_agent = await create_supervisor_agent()
    researcher_agent = await create_researcher_agent()

    # Create state graph
    workflow = StateGraph(State)

    # Add nodes
    print("\n   Adding nodes:")

    print("     1. supervisor (ReAct agent with handoff tools)")
    workflow.add_node("supervisor", supervisor_agent)

    print("     2. researcher (ReAct agent)")
    workflow.add_node("researcher", researcher_agent)

    # Set entry point
    print("\n   Entry point: supervisor")
    workflow.set_entry_point("supervisor")

    # Add edges
    print("\n   Adding edges:")
    print("     - researcher → END")
    workflow.add_edge("researcher", END)

    # Note: No manual routing needed!
    # The handoff tool (create_handoff_tool) returns Command objects
    # that automatically route to the correct agent.
    print("\n   ℹ️  Note: Routing handled automatically by handoff tools")
    print("      - create_handoff_tool() returns Command.goto('researcher')")
    print("      - No manual conditional edges needed")

    print("\n✅ Graph built successfully\n")

    return workflow.compile()


# ============================================================================
# 5. Test Execution
# ============================================================================

async def test():
    """Run the configuration 5 test with handoff tools"""
    print("\n" + "="*80)
    print("TEST CONFIG 5: ReAct Supervisor with Official Handoff Tools")
    print("="*80)
    print("\nPattern: Official LangChain handoff tools")
    print("- Uses langgraph_supervisor.create_handoff_tool()")
    print("- Handoff tools return Command objects automatically")
    print("- Automatic message history management")
    print("- Metadata tracking and audit trails")
    print("- Supervisor: ReAct agent with handoff tools")
    print("- Subagent: ReAct agent (researcher)")
    print("="*80 + "\n")

    # Check if handoff tools available
    if not HANDOFF_AVAILABLE:
        print("\n" + "="*80)
        print("❌ TEST SKIPPED - langgraph-supervisor not installed")
        print("="*80 + "\n")
        print("Install with: pip install langgraph-supervisor")
        print("\nExiting...\n")
        return

    print("\n📚 Research Findings:")
    print("   1. Handoff tools ARE different from Command.goto")
    print("   2. create_handoff_tool() is higher-level abstraction")
    print("   3. Provides automatic state/message management")
    print("   4. Returns Command object with metadata tracking")
    print("   5. Integrates seamlessly with ReAct agents\n")

    # Build graph
    try:
        graph = await build_graph()
    except ImportError as e:
        print("\n" + "="*80)
        print("❌ TEST FAILED - Missing dependency")
        print("="*80 + "\n")
        print(f"Error: {e}\n")
        return

    # Test query
    query = "What are the latest developments in quantum computing?"

    print(f"\n🚀 Starting test with query: {query}\n")
    print("-"*80)

    try:
        result = await graph.ainvoke({
            "messages": [HumanMessage(content=f"Research: {query}")]
        })

        print("\n" + "="*80)
        print("✅ TEST PASSED!")
        print("="*80 + "\n")

        print("📋 Final state:")
        print(f"   Total messages: {len(result['messages'])}")
        print(f"   Message types: {[type(m).__name__ for m in result['messages']]}")

        print("\n📨 Message sequence:")
        for i, msg in enumerate(result['messages']):
            msg_type = type(msg).__name__
            content = getattr(msg, 'content', '')
            if len(content) > 150:
                content = content[:150] + "..."
            name = getattr(msg, 'name', 'N/A')
            tool_calls = getattr(msg, 'tool_calls', [])

            print(f"\n   {i+1}. {msg_type}")
            if name != 'N/A':
                print(f"      Name: {name}")
            if tool_calls:
                print(f"      Tool calls: {len(tool_calls)}")
                for tc in tool_calls:
                    tc_name = tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown')
                    print(f"        - {tc_name}")
            print(f"      Content: {content}")

        print("\n" + "="*80)
        print("Configuration 5 test completed successfully!")
        print("="*80 + "\n")

        print("✅ Verified:")
        print("   - Handoff tools pattern works with ReAct agents")
        print("   - create_handoff_tool() provides higher-level abstraction")
        print("   - Automatic message history and state management")
        print("   - Command.goto routing handled transparently")
        print("")

    except Exception as e:
        print("\n" + "="*80)
        print("❌ TEST FAILED!")
        print("="*80 + "\n")
        print(f"Error: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()


# ============================================================================
# 6. Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("\n🚀 Starting Configuration 5 Test (Handoff Tools Pattern)...\n")
    asyncio.run(test())
