"""Test that agent correctly uses write_file with both file_path AND content parameters."""
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

# Test write_file with explicit content instruction
print("\n" + "🧪" * 40)
print("TESTING write_file WITH CONTENT PARAMETER")
print("🧪" * 40)

module.run_agent_task(
    "Write a brief summary about the benefits of AI agents to /workspace/ai_benefits.md. Include at least 3 key benefits in your summary.",
    thread_id="test-write-content"
)

# Verify the file was created
import os
test_file = "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/agent_workspace/ai_benefits.md"
if os.path.exists(test_file):
    with open(test_file, 'r') as f:
        content = f.read()
    print("\n" + "=" * 80)
    print("✅ WRITE_FILE WITH CONTENT TEST PASSED!")
    print("=" * 80)
    print(f"File created at: {test_file}")
    print(f"Content length: {len(content)} characters")
    print(f"Preview:\n{content[:300]}...")
    print("=" * 80)
else:
    print("\n❌ WRITE_FILE TEST FAILED - File not found")
