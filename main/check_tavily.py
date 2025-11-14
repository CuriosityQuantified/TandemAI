"""Check Tavily tool description."""
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_tavily import TavilySearch

tavily = TavilySearch(
    max_results=5,
    api_key=os.getenv("TAVILY_API_KEY"),
)

print("=" * 80)
print("TAVILY TOOL INSPECTION")
print("=" * 80)
print(f"\nName: {tavily.name}")
print(f"\nDescription:\n{tavily.description}")
print(f"\nDescription length: {len(tavily.description)} characters")
print(f"Estimated tokens: ~{len(tavily.description.split()) * 1.3:.0f}")
print("=" * 80)
