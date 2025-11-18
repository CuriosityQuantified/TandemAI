#!/usr/bin/env python3
"""
Test script for Kimi K2 Thinking model using Groq via LangChain v1.0+

This script tests the moonshotai/kimi-k2-instruct-0905 model through Groq's API
using the langchain-groq library.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Import LangChain Groq
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage


def test_kimi_k2_basic():
    """Test basic Kimi K2 model invocation"""
    print("=" * 80)
    print("KIMI K2 THINKING MODEL TEST (via Groq + LangChain v1.0+)")
    print("=" * 80)
    print()

    # Verify API key
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("❌ ERROR: GROQ_API_KEY not found in .env file")
        sys.exit(1)

    print(f"✓ GROQ_API_KEY loaded: {groq_api_key[:10]}...")
    print()

    # Initialize Kimi K2 model
    print("Initializing Kimi K2 model...")
    model = ChatGroq(
        model="moonshotai/kimi-k2-instruct-0905",
        temperature=0.7,
        max_tokens=2000,
        api_key=groq_api_key
    )
    print("✓ Model initialized successfully")
    print()

    # Test queries
    test_queries = [
        {
            "name": "Simple Reasoning",
            "query": "What is 15 * 24? Think step by step."
        },
        {
            "name": "Logical Thinking",
            "query": "If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly? Explain your reasoning."
        },
        {
            "name": "Creative Problem Solving",
            "query": "How would you design a system to detect citation accuracy in AI-generated research reports? Think through the key components."
        }
    ]

    for i, test in enumerate(test_queries, 1):
        print(f"\n{'─' * 80}")
        print(f"Test {i}: {test['name']}")
        print(f"{'─' * 80}")
        print(f"Query: {test['query']}")
        print()

        try:
            # Create messages
            messages = [
                SystemMessage(content="You are a helpful AI assistant with strong reasoning capabilities. Think step by step and show your reasoning process."),
                HumanMessage(content=test['query'])
            ]

            # Invoke model
            print("Invoking Kimi K2 model...")
            response = model.invoke(messages)

            # Display response
            print("\n✓ Response received:")
            print("-" * 80)
            print(response.content)
            print("-" * 80)
            print(f"\nToken usage: {response.response_metadata.get('token_usage', 'N/A')}")

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ KIMI K2 TEST COMPLETE")
    print("=" * 80)


def test_kimi_k2_streaming():
    """Test streaming response from Kimi K2"""
    print("\n" + "=" * 80)
    print("KIMI K2 STREAMING TEST")
    print("=" * 80)
    print()

    groq_api_key = os.getenv("GROQ_API_KEY")

    # Initialize model
    model = ChatGroq(
        model="moonshotai/kimi-k2-instruct-0905",
        temperature=0.7,
        streaming=True,
        api_key=groq_api_key
    )

    query = "Explain the concept of recursion in programming in 3 sentences."
    print(f"Query: {query}")
    print("\nStreaming response:")
    print("-" * 80)

    try:
        for chunk in model.stream([HumanMessage(content=query)]):
            print(chunk.content, end='', flush=True)
        print()
        print("-" * 80)
        print("✓ Streaming complete")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run tests
    test_kimi_k2_basic()
    test_kimi_k2_streaming()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)
