"""
Minimal test to verify Command.goto routing works in isolation.
This helps determine if the issue is with LangGraph's Command routing
or with our specific graph configuration.
"""

import asyncio
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from typing import Literal, TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langgraph.graph.message import add_messages


class State(TypedDict):
    """Minimal state for testing"""
    messages: Annotated[list[BaseMessage], add_messages]


# Minimal delegation tool
async def simple_delegate(task: str, tool_call_id: str) -> Command[Literal["worker"]]:
    """Simple delegation tool that returns Command"""
    print(f"\n🔧 simple_delegate called with task: {task}")
    print(f"   Returning Command(goto='worker')")

    return Command(
        goto="worker",
        update={
            "messages": [
                ToolMessage(
                    content=f"✅ Delegated task: {task}",
                    tool_call_id=tool_call_id
                )
            ]
        }
    )


# Simple worker node
async def worker_node(state: State):
    """Worker that executes the delegated task"""
    print("\n👷 worker_node executing...")
    print(f"   Received {len(state['messages'])} messages")

    return {
        "messages": [
            AIMessage(content="Worker completed the task successfully!")
        ]
    }


# Supervisor node
async def supervisor_node(state: State):
    """Supervisor that calls delegation tool"""
    print("\n👔 supervisor_node executing...")
    print(f"   Received {len(state['messages'])} messages")

    # Create tool call
    return {
        "messages": [
            AIMessage(
                content="Delegating to worker...",
                tool_calls=[{
                    "name": "simple_delegate",
                    "args": {
                        "task": "Test delegation",
                        "tool_call_id": "test-123"
                    },
                    "id": "test-123"
                }]
            )
        ]
    }


def build_test_graph():
    """Build minimal graph with delegation"""
    print("\n📊 Building minimal test graph...")

    workflow = StateGraph(State)

    # Create tool node
    delegation_tool_node = ToolNode([simple_delegate])

    # Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("delegation_tools", delegation_tool_node)
    workflow.add_node("worker", worker_node)

    # Entry
    workflow.set_entry_point("supervisor")

    # Edges
    print("   Adding edges:")
    print("     - supervisor → delegation_tools")
    workflow.add_edge("supervisor", "delegation_tools")

    # NO edge from delegation_tools - let Command.goto route
    print("     - delegation_tools → (Command.goto routing)")

    print("     - worker → END")
    workflow.add_edge("worker", END)

    print("✅ Graph built\n")

    return workflow.compile()


async def test():
    """Run the minimal delegation test"""
    print("\n" + "="*80)
    print("MINIMAL COMMAND.GOTO TEST")
    print("="*80)

    graph = build_test_graph()

    print("\n🔄 Invoking graph with initial message...")

    try:
        result = await graph.ainvoke({
            "messages": [
                HumanMessage(content="Start delegation test")
            ]
        })

        print("\n" + "="*80)
        print("✅ TEST PASSED!")
        print("="*80 + "\n")

        print("📋 Final state:")
        print(f"   Total messages: {len(result['messages'])}")
        print(f"   Message types: {[type(m).__name__ for m in result['messages']]}")

        print("\n📨 Messages:")
        for i, msg in enumerate(result['messages']):
            content = getattr(msg, 'content', '')[:100]
            print(f"   {i+1}. {type(msg).__name__}: {content}")

    except Exception as e:
        print("\n" + "="*80)
        print("❌ TEST FAILED!")
        print("="*80 + "\n")
        print(f"Error: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Starting minimal delegation test...\n")
    asyncio.run(test())
