"""Test Example 1: Tavily search with simplified architecture."""
import os
import sys

os.chdir('/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2')
sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv
load_dotenv('../.env')

# Import the module
import importlib.util
spec = importlib.util.spec_from_file_location("module", "module-2-2-simple.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Run Example 1
print("\n" + "🧪" * 40)
print("TESTING EXAMPLE 1 WITH HAIKU 4.5")
print("🧪" * 40)

module.run_agent_task(
    "Search for the latest updates on LangChain v1.0 and summarize the key features",
    thread_id="test-tavily-demo"
)

print("\n" + "=" * 80)
print("✅ Test completed successfully with Haiku 4.5!")
print("=" * 80)
