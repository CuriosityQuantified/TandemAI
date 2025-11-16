"""Quick test to verify Config 2 graph compiles correctly"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment from root .env
env_path = Path(__file__).parent.parent.parent / ".env"  # Up 3 levels to TandemAI root
load_dotenv(env_path)

# Add root to sys.path for absolute imports
root_path = Path(__file__).parent.parent.parent  # Up to TandemAI root
sys.path.insert(0, str(root_path))

# Import the test module with absolute path
from backend.test_configs.test_config_2_deepagent_supervisor_conditional import build_graph, WORKSPACE_DIR

def quick_test():
    """Quick test to verify graph builds correctly"""
    print("="*80)
    print("QUICK TEST: Config 2 Graph Compilation")
    print("="*80)

    try:
        print("\n1. Building graph...")
        graph = build_graph()
        print("✅ Graph built successfully")

        print("\n2. Checking graph structure...")
        print(f"   Nodes: {list(graph.get_graph().nodes.keys())}")
        print("✅ Graph structure looks good")

        print("\n3. Workspace directory:")
        print(f"   Path: {WORKSPACE_DIR}")
        print(f"   Exists: {WORKSPACE_DIR.exists()}")

        print("\n" + "="*80)
        print("✅ QUICK TEST PASSED - Graph compiles correctly")
        print("="*80)

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)
