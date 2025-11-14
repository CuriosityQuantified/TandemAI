"""Quick test to verify module-2-2-simple.py can be initialized"""
import os
import sys

# Set up environment
os.chdir('/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2')
sys.path.insert(0, os.getcwd())

print("Testing imports and initialization...")

# Import dependencies
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from e2b_code_interpreter import Sandbox
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv('../.env')

print("✅ All imports successful!")
print(f"✅ ANTHROPIC_API_KEY: {'Present' if os.getenv('ANTHROPIC_API_KEY') else 'Missing'}")
print(f"✅ TAVILY_API_KEY: {'Present' if os.getenv('TAVILY_API_KEY') else 'Missing'}")
print(f"✅ FIRECRAWL_API_KEY: {'Present' if os.getenv('FIRECRAWL_API_KEY') else 'Missing'}")
print(f"✅ GITHUB_API_KEY: {'Present' if os.getenv('GITHUB_API_KEY') else 'Missing'}")
print(f"✅ E2B_API_KEY: {'Present' if os.getenv('E2B_API_KEY') else 'Missing'}")

# Test model initialization
model = ChatAnthropic(
    model="claude-sonnet-4-5-20250924",  # Sonnet for higher request limits
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.7,
)
print(f"✅ Model initialized: {model.model}")
print(f"ℹ️  Note: Using Sonnet instead of Haiku due to DeepAgents' 10+ tool overhead")

# Test Tavily tool
tavily = TavilySearchResults(
    max_results=5,
    api_key=os.getenv("TAVILY_API_KEY"),
)
print(f"✅ Tavily tool initialized: {tavily.name}")

print("\n🎉 All components ready for DeepAgent creation!")
