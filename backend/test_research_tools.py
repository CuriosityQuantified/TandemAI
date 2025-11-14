"""
Test to verify research agent has access to write_file tool.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_research_agent_tools():
    """Test what tools the research agent actually has access to."""
    from backend.src.agents.supervisor_agent import create_supervisor_agent

    print("\n" + "="*70)
    print("RESEARCH AGENT TOOLS TEST")
    print("="*70)

    # Create supervisor
    supervisor = await create_supervisor_agent()

    # Get the research agent's graph
    # Deep Agents stores sub-agents in the supervisor's graph
    # Let's check if we can access the research agent's tool list

    print("\n📋 Supervisor graph keys:")
    if hasattr(supervisor, 'nodes'):
        print(f"   Nodes: {list(supervisor.nodes.keys())}")

    # Try to get research agent's state
    print("\n🔧 Checking research agent configuration...")

    # Create a test task to see what tools are actually available
    test_task = "List all tools you have access to."

    print(f"\n🎯 Test task: {test_task}")
    print("\n⏳ Executing...")

    result = await supervisor.ainvoke({
        "messages": [{"role": "user", "content": test_task}]
    })

    # Show final message
    if result.get("messages"):
        final_msg = result["messages"][-1]
        print(f"\n📝 Response:")
        print(final_msg.content[:500] if hasattr(final_msg, 'content') else str(final_msg)[:500])

    print("\n" + "="*70)

if __name__ == "__main__":
    asyncio.run(test_research_agent_tools())
