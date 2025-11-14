"""Test minimal Claude Haiku 4.5 access without DeepAgents."""
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7,
)

print("Testing minimal Claude Haiku 4.5 access...")
print("=" * 80)

try:
    response = model.invoke([HumanMessage(content="Say 'Hello from Claude Haiku 4.5!'")])
    print(f"✅ SUCCESS: {response.content}")
    print("=" * 80)
    print("\nModel is accessible. The 413 error must be from DeepAgents overhead.")
except Exception as e:
    print(f"❌ ERROR: {e}")
    print("=" * 80)
