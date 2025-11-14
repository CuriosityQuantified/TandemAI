"""
Test llama-3.3-70b-versatile tool calling directly with LangChain.
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


@tool
async def test_search(query: str) -> str:
    """
    Test search tool.

    Args:
        query: The search query

    Returns:
        Search results
    """
    return f"Search results for: {query}"


async def test_direct_tool_calling():
    """Test if qwen/qwen3-32b can call tools properly."""
    print("Testing qwen/qwen3-32b tool calling...")

    # Create model - test qwen/qwen3-32b
    model = ChatGroq(
        model="qwen/qwen3-32b",
        temperature=0.7,
        max_tokens=1000,
        groq_api_key=os.getenv("GROQ_API_KEY"),
    )

    # Bind tool to model
    model_with_tools = model.bind_tools([test_search])

    # Test message
    message = "Search for information about superforecasting"

    print(f"\nUser message: {message}\n")

    # Invoke model
    response = await model_with_tools.ainvoke([{"role": "user", "content": message}])

    print(f"Response type: {type(response)}")
    print(f"Response content: {response.content}")
    print(f"Response additional_kwargs: {response.additional_kwargs}")

    if hasattr(response, 'tool_calls'):
        print(f"\nTool calls: {response.tool_calls}")
        if response.tool_calls:
            for tc in response.tool_calls:
                print(f"  - Tool: {tc.get('name')}")
                print(f"    Args: {tc.get('args')}")
        else:
            print("  (No tool calls made)")

    return response


if __name__ == "__main__":
    asyncio.run(test_direct_tool_calling())
