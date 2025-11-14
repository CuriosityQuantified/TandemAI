"""Test that the agent can write files with correct /workspace/ prefix."""
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

# Test file writing
print("\n" + "🧪" * 40)
print("TESTING FILE WRITE WITH /workspace/ PREFIX")
print("🧪" * 40)

module.run_agent_task(
    "Write a short test message to /workspace/test_message.txt with the content 'File write test successful!'",
    thread_id="test-file-write"
)

# Verify the file was created
import os
test_file = "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/agent_workspace/test_message.txt"
if os.path.exists(test_file):
    with open(test_file, 'r') as f:
        content = f.read()
    print("\n" + "=" * 80)
    print("✅ FILE WRITE TEST PASSED!")
    print("=" * 80)
    print(f"File created at: {test_file}")
    print(f"Content: {content}")
    print("=" * 80)
else:
    print("\n❌ FILE WRITE TEST FAILED - File not found")
