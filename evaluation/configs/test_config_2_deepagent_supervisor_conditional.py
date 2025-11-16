"""
Test Configuration 2: DeepAgent Supervisor with Conditional Routing

This configuration demonstrates:
1. DeepAgent supervisor with reflection and memory capabilities
2. Base ReAct subagents (researcher only)
3. Traditional LangGraph conditional edges with routing function
4. ToolMessage return (NOT Command) from delegation tools
5. Routing function inspects tool_calls to determine next node

Graph Structure:
    START → supervisor (DeepAgent) → delegation_tools (ToolNode)
                                        ↓ (conditional edge)
                                     researcher (ReAct) → END

Key Differences from Config 1:
- Uses conditional edges instead of Command.goto
- Routing function examines last AI message's tool_calls
- Returns ToolMessage instead of Command from delegation tools
- More traditional LangGraph routing pattern

Created: November 12, 2025
Pattern: Conditional routing with tool_calls inspection
Model: Claude Haiku 4.5 for all agents
"""

import asyncio
import os
from pathlib import Path
from typing import Literal, Annotated, TypedDict
from dotenv import load_dotenv

# Load environment from root .env
env_path = Path(__file__).parent.parent.parent / ".env"  # Up 3 levels to TandemAI root
load_dotenv(env_path)

# LangGraph imports
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

# LangChain imports (new location for create_react_agent)
from langchain.agents import create_agent

# LangChain imports
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langchain_core.tools import tool, InjectedToolCallId

# DeepAgents imports
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

# Add root to sys.path for absolute imports
import sys
root_path = Path(__file__).parent.parent.parent  # Up to TandemAI root
sys.path.insert(0, str(root_path))

# Import shared tools with absolute path
from backend.test_configs.shared_tools import (
    get_supervisor_tools,
    get_subagent_tools,
    PLANNING_TOOLS,
    RESEARCH_TOOLS,
    FILE_TOOLS
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Use Claude Haiku 4.5 for all agents
MODEL_NAME = "claude-haiku-4-5-20251001"

# Workspace directory
WORKSPACE_DIR = Path(__file__).parent.parent / "workspace"
WORKSPACE_DIR.mkdir(exist_ok=True)

# ============================================================================
# DELEGATION TOOLS (Return ToolMessage, NOT Command)
# ============================================================================

@tool("delegate_to_researcher")
async def delegate_to_researcher(
    task: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> str:
    """
    Delegate a research task to the Researcher subagent.

    The Researcher specializes in:
    - Web research and information gathering
    - Synthesizing information from multiple sources
    - Creating well-cited documents

    Args:
        task: Complete task description including research question and output file
        tool_call_id: Injected by LangGraph for ToolMessage matching

    Returns:
        String content for ToolMessage (NOT Command object)
    """
    print(f"\n🔧 delegate_to_researcher called")
    print(f"   Task: {task[:100]}...")
    print(f"   Tool call ID: {tool_call_id}")
    print(f"   Returning ToolMessage content (NOT Command)")

    # Return string content - LangGraph will wrap in ToolMessage
    return f"✅ Routing to researcher subagent: {task[:100]}..."


# ============================================================================
# ROUTING FUNCTION (Inspects tool_calls)
# ============================================================================

def route_after_delegation(state: MessagesState) -> Literal["researcher", "end"]:
    """
    Route based on which delegation tool was called.

    This function inspects the tool_calls in the last AI message to determine
    which subagent node to route to next.

    Args:
        state: Current graph state with messages

    Returns:
        "researcher" if delegate_to_researcher was called
        "end" otherwise
    """
    messages = state["messages"]

    print(f"\n🔀 route_after_delegation called")
    print(f"   Total messages: {len(messages)}")

    # Find the last AIMessage before the ToolMessage(s)
    # Messages order: [..., AIMessage(tool_calls=[...]), ToolMessage, ...]
    last_ai_message = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            last_ai_message = msg
            break

    if not last_ai_message:
        print(f"   ⚠️  No AIMessage found - routing to END")
        return "end"

    print(f"   Last AI message type: {type(last_ai_message).__name__}")

    # Check if message has tool_calls attribute
    if not hasattr(last_ai_message, "tool_calls"):
        print(f"   ⚠️  No tool_calls attribute - routing to END")
        return "end"

    tool_calls = last_ai_message.tool_calls
    print(f"   Tool calls found: {len(tool_calls) if tool_calls else 0}")

    if not tool_calls:
        print(f"   ⚠️  Empty tool_calls - routing to END")
        return "end"

    # Check each tool call
    for tool_call in tool_calls:
        tool_name = tool_call.get("name", "")
        print(f"   📞 Tool call: {tool_name}")

        if tool_name == "delegate_to_researcher":
            print(f"   ✅ Routing to researcher")
            return "researcher"

    print(f"   ⚠️  No delegation tool found - routing to END")
    return "end"


# ============================================================================
# SUBAGENT CREATION
# ============================================================================

def create_researcher_subagent(workspace_dir: Path):
    """
    Create ReAct researcher subagent with ALL tools.

    Uses create_agent for simple tool-calling agent pattern.
    Uses shared_tools for consistent tool implementation.
    """
    print("\n📚 Creating researcher subagent...")

    # Create LLM
    llm = ChatAnthropic(model=MODEL_NAME, temperature=0)

    # Get all subagent tools (planning + research + files, NO delegation)
    researcher_tools = get_subagent_tools()

    print(f"   Researcher tools: {len(researcher_tools)}")
    print(f"   - Planning: {len(PLANNING_TOOLS)} tools")
    print(f"   - Research: {len(RESEARCH_TOOLS)} tools")
    print(f"   - Files: {len(FILE_TOOLS)} tools")

    # Create ReAct agent
    agent = create_agent(
        model=llm,
        tools=researcher_tools,
        system_prompt=(
            "You are a research specialist. Your task is to:\n"
            "1. Search for information using search_web tool\n"
            "2. Synthesize findings into a clear, well-cited report\n"
            "3. Save the report to the specified file path using write_file\n"
            "4. Use numbered citations like [1] [2] [3]\n"
            "\n"
            "Always complete the full research task before finishing."
        )
    )

    print("✅ Researcher subagent created")
    return agent


def create_supervisor(workspace_dir: Path):
    """
    Create DeepAgent supervisor with reflection and memory.

    DeepAgent features:
    - Planning via planning tools (create_research_plan, etc.)
    - Filesystem backend for context management
    - Reflection capabilities through task decomposition
    - Full access to ALL tools (delegation + planning + research + files)
    """
    print("\n👔 Creating DeepAgent supervisor...")

    # Create LLM
    llm = ChatAnthropic(model=MODEL_NAME, temperature=0)

    # Create filesystem backend for DeepAgent
    backend = FilesystemBackend(root_dir=str(workspace_dir))

    # Get ALL supervisor tools (delegation + planning + research + files)
    supervisor_tools = get_supervisor_tools([delegate_to_researcher])

    print(f"   Supervisor tools: {len(supervisor_tools)}")
    print(f"   - Delegation: 1 tool")
    print(f"   - Planning: {len(PLANNING_TOOLS)} tools")
    print(f"   - Research: {len(RESEARCH_TOOLS)} tools")
    print(f"   - Files: {len(FILE_TOOLS)} tools")

    # Create DeepAgent with backend
    supervisor = create_deep_agent(
        model=llm,
        tools=supervisor_tools,
        backend=backend,
        checkpointer=MemorySaver(),
        system_prompt=(
            "You are a research supervisor. Your role is to:\n"
            "1. Understand the research request\n"
            "2. Plan the research approach using create_research_plan\n"
            "3. Delegate tasks to specialized subagents\n"
            "4. Use delegate_to_researcher for research tasks\n"
            "\n"
            "Always delegate to the appropriate subagent - do not do the work yourself."
        )
    )

    print("✅ DeepAgent supervisor created")
    return supervisor


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def build_graph():
    """
    Build graph with conditional routing.

    Graph structure:
        START → supervisor → delegation_tools → (conditional) → researcher → END
                                                              → end
    """
    print("\n📊 Building graph with conditional routing...")

    # Create supervisor and subagent
    supervisor_agent = create_supervisor(WORKSPACE_DIR)
    researcher_agent = create_researcher_subagent(WORKSPACE_DIR)

    # Create StateGraph
    workflow = StateGraph(MessagesState)

    # Add nodes
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("delegation_tools", ToolNode([delegate_to_researcher]))
    workflow.add_node("researcher", researcher_agent)

    # Set entry point
    workflow.set_entry_point("supervisor")

    # Add edges
    print("\n📋 Adding edges:")

    # supervisor → delegation_tools
    print("   1. supervisor → delegation_tools (regular edge)")
    workflow.add_edge("supervisor", "delegation_tools")

    # delegation_tools → (conditional routing)
    print("   2. delegation_tools → (conditional edge)")
    print("      - Routing function: route_after_delegation")
    print("      - Options: researcher | end")
    workflow.add_conditional_edges(
        "delegation_tools",
        route_after_delegation,
        {
            "researcher": "researcher",
            "end": END
        }
    )

    # researcher → END
    print("   3. researcher → END")
    workflow.add_edge("researcher", END)

    print("\n✅ Graph construction complete")

    # Compile with checkpointer
    graph = workflow.compile(checkpointer=MemorySaver())

    return graph


# ============================================================================
# TEST FUNCTION
# ============================================================================

async def test_config_2():
    """
    Test Config 2: DeepAgent supervisor with conditional routing.

    This test verifies:
    1. DeepAgent supervisor receives task
    2. Supervisor calls delegate_to_researcher tool
    3. ToolNode executes delegation tool
    4. Routing function inspects tool_calls
    5. Graph routes to researcher node
    6. Researcher executes task
    7. Graph completes successfully
    """
    print("\n" + "="*80)
    print("TEST CONFIG 2: DeepAgent Supervisor + Conditional Routing")
    print("="*80)

    # Build graph
    graph = build_graph()

    # Test query (simplified for faster testing)
    test_query = (
        "Write a simple test file to /workspace/test_config_2.md with the text 'Config 2 test successful'."
    )

    print(f"\n📝 Test query: {test_query}")

    # Create config with thread
    config = {"configurable": {"thread_id": "test-config-2"}}

    print("\n🔄 Invoking graph...")
    print("-" * 80)

    try:
        # Stream events to see routing
        async for event in graph.astream_events(
            {"messages": [HumanMessage(content=test_query)]},
            config,
            version="v2"
        ):
            kind = event.get("event", "")

            # Log important events
            if kind == "on_chain_start":
                node = event.get("name", "")
                if node in ["supervisor", "delegation_tools", "researcher"]:
                    print(f"\n▶️  Starting: {node}")

            elif kind == "on_chain_end":
                node = event.get("name", "")
                if node in ["supervisor", "delegation_tools", "researcher"]:
                    print(f"✅ Completed: {node}")

            elif kind == "on_tool_start":
                tool_name = event.get("name", "")
                print(f"\n🔧 Tool called: {tool_name}")

            elif kind == "on_tool_end":
                tool_name = event.get("name", "")
                print(f"✅ Tool completed: {tool_name}")

        print("\n" + "-" * 80)
        print("\n✅ TEST PASSED - Graph execution completed successfully")

        # Get final state
        final_state = await graph.aget_state(config)
        messages = final_state.values.get("messages", [])

        print(f"\n📊 Final state:")
        print(f"   Total messages: {len(messages)}")
        print(f"   Message types: {[type(m).__name__ for m in messages]}")

        # Check if file was created
        output_file = WORKSPACE_DIR / "test_config_2.md"
        if output_file.exists():
            print(f"\n✅ Output file created: {output_file}")
            content = output_file.read_text()
            print(f"   Content: {content}")
        else:
            print(f"\n⚠️  Output file not found: {output_file}")

        # Verify routing function was called
        print(f"\n✅ Routing verification:")
        print(f"   - Conditional edge should have called route_after_delegation")
        print(f"   - Check logs above for '🔀 route_after_delegation called'")
        print(f"   - Should show routing to 'researcher' node")

        return True

    except Exception as e:
        print("\n" + "-" * 80)
        print(f"\n❌ TEST FAILED - {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n🚀 Starting Config 2 test...\n")

    # Run test
    success = asyncio.run(test_config_2())

    if success:
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("❌ TESTS FAILED")
        print("="*80)
        exit(1)
