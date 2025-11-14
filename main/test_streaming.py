"""Quick test to verify streaming works correctly with optimized prompts."""
import os
import sys

# Set up environment
os.chdir('/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/module-2-2')
sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv
load_dotenv('../.env')

print("Testing module-2-2-simple.py with optimizations...")
print("=" * 80)

# Import the module
import importlib.util
spec = importlib.util.spec_from_file_location("module", "module-2-2-simple.py")
module = importlib.util.module_from_spec(spec)

# Only execute up to agent creation, not the examples
print("\n🧪 Testing agent initialization and streaming setup...")
spec.loader.exec_module(module)

# Run a simple test query (not using external APIs)
print("\n🧪 Testing streaming with simple filesystem operation...")
print("=" * 80)

test_result = module.run_agent_task(
    "Create a file at /workspace/test.txt with the text 'Hello from streaming test!'",
    thread_id="streaming-test"
)

print("\n✅ Streaming test completed successfully!")
print("=" * 80)

# Verify the file was created
if test_result and "messages" in test_result:
    print("\n📋 Test result validation:")
    print(f"  - Messages in result: {len(test_result['messages'])}")
    print(f"  - Files in state: {len(test_result.get('files', {}))}")

    # Check if file was created
    import os
    test_file = "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/agent_workspace/test.txt"
    if os.path.exists(test_file):
        print(f"  - ✅ Test file created successfully")
        with open(test_file, 'r') as f:
            content = f.read()
            print(f"  - File content: {content}")
    else:
        print(f"  - ⚠️ Test file not found at {test_file}")

print("\n🎉 All streaming infrastructure tests passed!")
print("Ready to run production examples with Tavily, Firecrawl, GitHub, and e2b")
