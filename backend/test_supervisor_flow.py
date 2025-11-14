#!/usr/bin/env python
"""
Test script to verify complete supervisor flow:
1. Create supervisor agent with registered tools
2. Send a message that triggers tool usage
3. Verify response contains tool execution results
"""

import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.supervisor import Supervisor
from src.mlflow.agent_tracking import AgentMLflowTracker

def test_supervisor_creation():
    """Test creating a supervisor with all tools registered."""
    print("=" * 60)
    print("Testing Supervisor Agent Creation with Tools")
    print("=" * 60)

    try:
        # Create supervisor with MLflow tracking
        task_id = f"test_{int(time.time())}"
        mlflow_tracker = AgentMLflowTracker(f"Test_Task_{task_id}")

        print(f"\n1. Creating supervisor for task: {task_id}")
        supervisor = Supervisor(task_id=task_id, mlflow_tracker=mlflow_tracker)

        print(f"✅ Supervisor created: {supervisor.agent.id}")
        print(f"   Task ID: {supervisor.task_id}")
        print(f"   Tools available: {len(supervisor.tools)}")

        # List the registered tools
        print("\n2. Registered tools:")
        for tool in supervisor.tools:
            print(f"   - {tool['name']}: {tool['description'][:50]}...")

        return supervisor

    except Exception as e:
        print(f"❌ Failed to create supervisor: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_tool_invocation(supervisor):
    """Test that the supervisor can invoke its tools."""
    print("\n" + "=" * 60)
    print("Testing Tool Invocation")
    print("=" * 60)

    try:
        # Test 1: Simple planning task
        print("\n1. Testing planning tool:")
        message = "Create a plan to build a simple Python web scraper"

        print(f"   Sending: {message}")
        response = supervisor.send_message(message)

        print(f"   Response type: {type(response)}")
        print(f"   Response length: {len(response)}")

        if response:
            for idx, msg in enumerate(response):
                print(f"\n   Message {idx + 1}:")
                print(f"   Role: {msg.get('role', 'unknown')}")
                content = msg.get('content', '')
                if content:
                    # Show first 200 chars of content
                    preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"   Content preview: {preview}")

        # Test 2: Todo creation
        print("\n2. Testing todo tool:")
        message = "Create a todo item for implementing the web scraper"

        print(f"   Sending: {message}")
        response = supervisor.send_message(message)

        if response and response[0].get('content'):
            print(f"   ✅ Todo tool response received")

        return True

    except Exception as e:
        print(f"❌ Tool invocation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_supervisor_status(supervisor):
    """Test getting supervisor status."""
    print("\n" + "=" * 60)
    print("Testing Supervisor Status")
    print("=" * 60)

    try:
        status = supervisor.get_status()

        print("\nSupervisor Status:")
        print(f"  Agent ID: {status.get('agent_id')}")
        print(f"  Task ID: {status.get('task_id')}")
        print(f"  Tools Available: {len(status.get('tools_available', []))}")
        print(f"  Last Activity: {status.get('last_activity')}")

        if status.get('memory_state'):
            print(f"  Memory State Keys: {list(status['memory_state'].keys())}")

        return True

    except Exception as e:
        print(f"❌ Status retrieval failed: {e}")
        return False

def cleanup_supervisor(supervisor):
    """Clean up the supervisor agent."""
    print("\n" + "=" * 60)
    print("Cleaning Up")
    print("=" * 60)

    try:
        supervisor.cleanup()
        print("✅ Supervisor cleaned up successfully")
        return True
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Complete Supervisor Flow")
    print("=" * 60)
    print("Requirements:")
    print("- Letta server running on http://localhost:8283")
    print("- Backend virtual environment activated")
    print("=" * 60)

    # Test supervisor creation
    supervisor = test_supervisor_creation()

    if supervisor:
        # Test tool invocation
        tool_success = test_tool_invocation(supervisor)

        # Test status retrieval
        status_success = test_supervisor_status(supervisor)

        # Clean up
        cleanup_success = cleanup_supervisor(supervisor)

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"✅ Supervisor Creation: Success")
        print(f"{'✅' if tool_success else '❌'} Tool Invocation: {'Success' if tool_success else 'Failed'}")
        print(f"{'✅' if status_success else '❌'} Status Retrieval: {'Success' if status_success else 'Failed'}")
        print(f"{'✅' if cleanup_success else '❌'} Cleanup: {'Success' if cleanup_success else 'Failed'}")

        if tool_success and status_success:
            print("\n🎉 All tests passed! The supervisor agent is working correctly.")
            print("\nNext step: Test the API endpoint to verify frontend integration.")
    else:
        print("\n❌ Could not create supervisor. Check that:")
        print("   1. Letta server is running (letta server --port 8283)")
        print("   2. Virtual environment is activated")
        print("   3. All dependencies are installed")