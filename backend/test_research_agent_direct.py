"""
Direct test of research agent to diagnose issues.
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parents[1] / ".env"
load_dotenv(env_path)

# Add ATLAS root and deepagents to path
atlas_root = Path(__file__).parents[1]
deepagents_src = atlas_root / "deepagents" / "src"
sys.path.insert(0, str(atlas_root))
sys.path.insert(0, str(deepagents_src))

from deepagents import async_create_deep_agent
from backend.src.agents.model_config import get_groq_model
from backend.src.utils.prompt_loader import load_agent_prompt
from backend.src.tools.external_tools import internet_search


async def test_research_agent():
    """Test research agent directly without supervisor."""
    print("Creating research agent...")

    # Load instructions
    instructions = load_agent_prompt("research_agent")
    print(f"Loaded instructions ({len(instructions)} chars)")

    # Create agent with internet_search tool
    agent = async_create_deep_agent(
        model=get_groq_model(temperature=0.5),
        instructions=instructions,
        tools=[internet_search],
        subagents=[],
    )

    print("\n" + "="*60)
    print("Testing research agent with simple query...")
    print("="*60)

    # Test with simple query
    query = "What is 2+2?"
    print(f"\nQuery: {query}")

    # Invoke agent
    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": query}]
    })

    print("\n" + "="*60)
    print("RESULT:")
    print("="*60)

    # Print all messages
    for i, msg in enumerate(result.get("messages", []), 1):
        msg_type = getattr(msg, 'type', 'unknown')
        content = getattr(msg, 'content', '')
        print(f"\nMessage {i} ({msg_type}):")
        if content:
            print(content[:500])  # First 500 chars
        else:
            print("[EMPTY]")

    return result


if __name__ == "__main__":
    asyncio.run(test_research_agent())
