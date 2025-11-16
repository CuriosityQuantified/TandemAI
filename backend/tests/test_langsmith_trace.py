"""
Quick test script to send a trace to LangSmith and create the project.

This will create the 'module-2-2-research-agent' project in LangSmith
and send a simple test trace so we can verify everything is working.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

# Load environment variables from lessons/.env
env_path = Path(__file__).parent.parent.parent.parent / ".env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

# Verify LangSmith configuration
print("\n✅ LangSmith Configuration:")
print(f"  LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")
print(f"  LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
print(f"  LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT')}")
print(f"  LANGSMITH_API_KEY: {os.getenv('LANGSMITH_API_KEY')[:20]}..." if os.getenv('LANGSMITH_API_KEY') else "  LANGSMITH_API_KEY: Not set")
print(f"  LANGSMITH_ENDPOINT: {os.getenv('LANGSMITH_ENDPOINT')}")

# Send a simple test trace
print("\n📡 Sending test trace to LangSmith...")

llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0,
    max_tokens=100
)

response = llm.invoke([
    HumanMessage(content="Say 'Hello from LangSmith test!' in exactly 5 words.")
])

print(f"\n✅ Trace sent successfully!")
print(f"Response: {response.content}")
print(f"\n🔍 Now check LangSmith UI - the 'module-2-2-research-agent' project should appear!")
print(f"   URL: https://smith.langchain.com/")
