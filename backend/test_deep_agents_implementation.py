"""
Validation test for Deep Agents implementation.

This script tests that all components are properly configured and
can be imported and initialized without errors.
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from: {env_path}")
else:
    print(f"⚠️  .env file not found at: {env_path}")

# Add ATLAS root directory to path for absolute imports (backend.src.*)
# This file is in backend/, so parent is ATLAS/
atlas_root = Path(__file__).parent.parent
sys.path.insert(0, str(atlas_root))


async def test_model_config():
    """Test model configuration."""
    print("\n🧪 Testing model configuration...")
    try:
        from backend.src.agents.model_config import get_groq_model

        model = get_groq_model(temperature=0.7)
        print(f"✅ Model created: {type(model).__name__}")
        print(f"   Model name: {getattr(model, 'model_name', 'openai/gpt-oss-120b')}")
        print(f"   Temperature: {model.temperature}")
        print(f"   Max tokens: {model.max_tokens}")
        return True
    except Exception as e:
        print(f"❌ Model config failed: {e}")
        return False


async def test_prompt_loader():
    """Test prompt loading utility."""
    print("\n🧪 Testing prompt loader...")
    try:
        from backend.src.utils.prompt_loader import (
            load_agent_prompt,
            load_agent_config,
            validate_prompt_file
        )

        # Test global supervisor
        if validate_prompt_file("global_supervisor"):
            prompt = load_agent_prompt("global_supervisor")
            print(f"✅ Loaded global_supervisor prompt ({len(prompt)} chars)")
        else:
            print("❌ global_supervisor.yaml not found or invalid")
            return False

        # Test research agent
        if validate_prompt_file("research_agent"):
            prompt = load_agent_prompt("research_agent")
            config = load_agent_config("research_agent")
            print(f"✅ Loaded research_agent prompt ({len(prompt)} chars)")
            print(f"   Agent type: {config.get('agent_type')}")
        else:
            print("❌ research_agent.yaml not found or invalid")
            return False

        # Test analysis agent
        if validate_prompt_file("analysis_agent"):
            prompt = load_agent_prompt("analysis_agent")
            print(f"✅ Loaded analysis_agent prompt ({len(prompt)} chars)")
        else:
            print("❌ analysis_agent.yaml not found or invalid")
            return False

        # Test writing agent
        if validate_prompt_file("writing_agent"):
            prompt = load_agent_prompt("writing_agent")
            print(f"✅ Loaded writing_agent prompt ({len(prompt)} chars)")
        else:
            print("❌ writing_agent.yaml not found or invalid")
            return False

        return True
    except Exception as e:
        print(f"❌ Prompt loader failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_external_tools():
    """Test external tools can be imported."""
    print("\n🧪 Testing external tools...")
    try:
        from backend.src.tools.external_tools import internet_search, execute_python_code

        print("✅ internet_search imported successfully")
        print("✅ execute_python_code imported successfully")

        # Test function signatures
        import inspect

        internet_sig = inspect.signature(internet_search)
        print(f"   internet_search params: {list(internet_sig.parameters.keys())}")

        execute_sig = inspect.signature(execute_python_code)
        print(f"   execute_python_code params: {list(execute_sig.parameters.keys())}")

        return True
    except Exception as e:
        print(f"❌ External tools failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_supervisor_agent():
    """Test supervisor agent creation."""
    print("\n🧪 Testing supervisor agent creation...")
    try:
        from backend.src.agents.supervisor_agent import create_supervisor_agent

        print("⏳ Creating supervisor agent...")
        agent = await create_supervisor_agent()

        print("✅ Supervisor agent created successfully")
        print(f"   Agent type: {type(agent).__name__}")

        # Check if agent has expected attributes
        if hasattr(agent, 'ainvoke'):
            print("✅ Agent has ainvoke method (async support)")

        return True
    except Exception as e:
        print(f"❌ Supervisor agent creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("ATLAS Deep Agents Implementation Validation")
    print("=" * 60)

    results = {
        "Model Configuration": await test_model_config(),
        "Prompt Loader": await test_prompt_loader(),
        "External Tools": await test_external_tools(),
        "Supervisor Agent": await test_supervisor_agent(),
    }

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Implementation is valid.")
        print("\nNext steps:")
        print("1. Set up environment variables (GROQ_API_KEY, TAVILY_API_KEY, E2B_API_KEY)")
        print("2. Test with a simple task using invoke_supervisor()")
        print("3. Integrate with API endpoints")
        print("4. Add comprehensive testing")
    else:
        print("⚠️  Some tests failed. Review errors above.")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
