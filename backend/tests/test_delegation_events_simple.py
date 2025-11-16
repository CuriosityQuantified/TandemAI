"""
Simple Test for Delegation Event Emission
==========================================

This test directly verifies the delegation event functions emit correct payloads.
It doesn't test full graph execution, just the event emission logic.

Usage:
    cd backend
    source /Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.venv/bin/activate
    python test_delegation_events_simple.py
"""
import asyncio
import json
from typing import List, Dict, Any
from datetime import datetime


class MockWebSocketManager:
    """Mock WebSocket manager to capture broadcasted events."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    async def broadcast(self, message: dict):
        """Capture broadcast events."""
        # Parse if string (from event_emitter.py)
        if isinstance(message, str):
            message = json.loads(message)

        self.events.append(message)
        print(f"[EVENT] {message.get('type')} -> {message.get('event_type', 'N/A')}")


async def test_delegation_event_structure():
    """Test that delegation events have correct structure."""
    print("\n" + "="*80)
    print("TEST: Delegation Event Structure")
    print("="*80)

    # Replace websocket manager with mock
    import websocket_manager
    mock_ws = MockWebSocketManager()
    websocket_manager.manager = mock_ws

    # Import event emitters after mocking
    from subagents.event_emitter import (
        emit_delegation_started,
        emit_delegation_completed,
        emit_delegation_error
    )

    # Test 1: subagent_started event
    print("\n1. Testing subagent_started event...")
    await emit_delegation_started(
        parent_thread_id="main-thread-123",
        subagent_thread_id="main-thread-123/subagent-researcher-uuid",
        subagent_type="researcher",
        task="Research quantum computing trends in 2025"
    )

    if len(mock_ws.events) != 1:
        print(f"❌ Expected 1 event, got {len(mock_ws.events)}")
        return False

    started_event = mock_ws.events[0]

    # Verify event structure
    required_fields = ["type", "event_type", "thread_id", "data", "timestamp"]
    missing_fields = [f for f in required_fields if f not in started_event]

    if missing_fields:
        print(f"❌ Missing fields: {missing_fields}")
        return False

    # Verify event type
    if started_event.get("type") != "agent_event":
        print(f"❌ Wrong type: {started_event.get('type')}")
        return False

    if started_event.get("event_type") != "subagent_started":
        print(f"❌ Wrong event_type: {started_event.get('event_type')}")
        return False

    if started_event.get("thread_id") != "main-thread-123":
        print(f"❌ Wrong thread_id: {started_event.get('thread_id')}")
        return False

    # Verify data structure
    data = started_event.get("data", {})
    required_data_fields = ["subagent_thread_id", "subagent_type", "task", "timestamp"]
    missing_data_fields = [f for f in required_data_fields if f not in data]

    if missing_data_fields:
        print(f"❌ Missing data fields: {missing_data_fields}")
        return False

    print("✅ subagent_started event structure correct")
    print(f"   Event: {json.dumps(started_event, indent=2)}")

    # Test 2: subagent_completed event
    print("\n2. Testing subagent_completed event...")
    mock_ws.events.clear()

    await emit_delegation_completed(
        parent_thread_id="main-thread-123",
        subagent_thread_id="main-thread-123/subagent-researcher-uuid",
        subagent_type="researcher",
        result_summary="Research completed. Found 7 sources on quantum trends."
    )

    if len(mock_ws.events) != 1:
        print(f"❌ Expected 1 event, got {len(mock_ws.events)}")
        return False

    completed_event = mock_ws.events[0]

    if completed_event.get("event_type") != "subagent_completed":
        print(f"❌ Wrong event_type: {completed_event.get('event_type')}")
        return False

    data = completed_event.get("data", {})
    if "result_summary" not in data:
        print("❌ Missing result_summary in data")
        return False

    print("✅ subagent_completed event structure correct")
    print(f"   Event: {json.dumps(completed_event, indent=2)}")

    # Test 3: subagent_error event
    print("\n3. Testing subagent_error event...")
    mock_ws.events.clear()

    await emit_delegation_error(
        parent_thread_id="main-thread-123",
        subagent_thread_id="main-thread-123/subagent-researcher-uuid",
        subagent_type="researcher",
        error="API rate limit exceeded after 30 seconds"
    )

    if len(mock_ws.events) != 1:
        print(f"❌ Expected 1 event, got {len(mock_ws.events)}")
        return False

    error_event = mock_ws.events[0]

    if error_event.get("event_type") != "subagent_error":
        print(f"❌ Wrong event_type: {error_event.get('event_type')}")
        return False

    data = error_event.get("data", {})
    if "error" not in data:
        print("❌ Missing error in data")
        return False

    print("✅ subagent_error event structure correct")
    print(f"   Event: {json.dumps(error_event, indent=2)}")

    print("\n✅ ALL DELEGATION EVENTS HAVE CORRECT STRUCTURE!")
    return True


async def test_frontend_compatibility():
    """Test that events match frontend expectations."""
    print("\n" + "="*80)
    print("TEST: Frontend Compatibility")
    print("="*80)

    # This is what the frontend expects (from usePlanWebSocket.ts lines 170-189)
    frontend_expectations = {
        "subagent_started": {
            "required_data_fields": ["subagent_thread_id", "subagent_type", "task"]
        },
        "subagent_completed": {
            "required_data_fields": ["subagent_thread_id"]
        },
        "subagent_error": {
            "required_data_fields": ["subagent_thread_id", "error"]
        }
    }

    import websocket_manager
    mock_ws = MockWebSocketManager()
    websocket_manager.manager = mock_ws

    from subagents.event_emitter import (
        emit_delegation_started,
        emit_delegation_completed,
        emit_delegation_error
    )

    # Emit all three event types
    await emit_delegation_started(
        "thread-123", "thread-123/sub-researcher-001", "researcher", "Test task"
    )
    await emit_delegation_completed(
        "thread-123", "thread-123/sub-researcher-001", "researcher", "Done"
    )
    await emit_delegation_error(
        "thread-123", "thread-123/sub-researcher-001", "researcher", "Test error"
    )

    # Verify each event
    for event in mock_ws.events:
        event_type = event.get("event_type")
        data = event.get("data", {})

        expected = frontend_expectations.get(event_type, {})
        required_fields = expected.get("required_data_fields", [])

        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            print(f"❌ {event_type} missing fields: {missing_fields}")
            return False

        print(f"✅ {event_type} compatible with frontend")

    print("\n✅ ALL EVENTS COMPATIBLE WITH FRONTEND!")
    return True


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("DELEGATION EVENT EMISSION VERIFICATION")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")

    tests = [
        ("Event Structure", test_delegation_event_structure),
        ("Frontend Compatibility", test_frontend_compatibility),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    passed_tests = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nNext Steps:")
        print("1. ✅ Delegation events correctly structured")
        print("2. ✅ Events compatible with frontend expectations")
        print("3. ⏭️  Run full integration test with actual agent execution")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
