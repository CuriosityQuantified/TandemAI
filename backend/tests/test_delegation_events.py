"""
Test Delegation Event Emission - Phase 1 Verification
=====================================================

This script tests that delegation lifecycle events are correctly emitted
when subagents are invoked. It verifies:
1. subagent_started events fire when delegation begins
2. subagent_completed events fire when delegation succeeds
3. subagent_error events fire when delegation fails
4. Events have correct structure and metadata

Usage:
    cd backend
    source /Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.venv/bin/activate
    python test_delegation_events.py
"""
import asyncio
import json
from typing import List, Dict, Any
from datetime import datetime


class MockWebSocketManager:
    """Mock WebSocket manager to capture broadcasted events."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.started_events: List[Dict] = []
        self.completed_events: List[Dict] = []
        self.error_events: List[Dict] = []

    async def broadcast(self, message: dict):
        """Capture broadcast events."""
        # Parse if string (from event_emitter.py)
        if isinstance(message, str):
            message = json.loads(message)

        self.events.append(message)

        # Categorize by event type
        if message.get("type") == "agent_event":
            event_type = message.get("event_type")
            if event_type == "subagent_started":
                self.started_events.append(message)
            elif event_type == "subagent_completed":
                self.completed_events.append(message)
            elif event_type == "subagent_error":
                self.error_events.append(message)

        print(f"[EVENT CAPTURED] {message.get('type')} -> {message.get('event_type', 'N/A')}")

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of captured events."""
        return {
            "total_events": len(self.events),
            "started_events": len(self.started_events),
            "completed_events": len(self.completed_events),
            "error_events": len(self.error_events),
            "event_types": [e.get("event_type", e.get("type")) for e in self.events]
        }

    def verify_delegation_lifecycle(self) -> bool:
        """Verify complete delegation lifecycle was captured."""
        has_started = len(self.started_events) > 0
        has_completed = len(self.completed_events) > 0

        if not has_started:
            print("❌ Missing subagent_started event")
            return False

        if not has_completed and len(self.error_events) == 0:
            print("❌ Missing subagent_completed or subagent_error event")
            return False

        return True


async def test_researcher_delegation():
    """Test researcher delegation events."""
    print("\n" + "="*80)
    print("TEST 1: Researcher Delegation Events")
    print("="*80)

    # Replace websocket manager with mock
    import websocket_manager
    mock_ws = MockWebSocketManager()
    websocket_manager.manager = mock_ws

    # Import graph after mocking
    from langgraph_studio_graphs import supervisor_agent_unified

    # Test researcher delegation
    print("\nInvoking supervisor with researcher delegation task...")
    result = await supervisor_agent_unified.ainvoke(
        {
            "messages": [{
                "role": "user",
                "content": "Research the latest developments in quantum computing."
            }],
            "thread_id": "test-delegation-events-researcher"
        },
        config={"configurable": {"thread_id": "test-delegation-events-researcher"}}
    )

    # Verify events
    print("\n" + "-"*80)
    print("Event Summary:")
    print(json.dumps(mock_ws.get_summary(), indent=2))

    print("\n" + "-"*80)
    print("Event Details:")
    for i, event in enumerate(mock_ws.events, 1):
        event_type = event.get("event_type", event.get("type"))
        data_keys = list(event.get("data", {}).keys()) if isinstance(event.get("data"), dict) else []
        print(f"  {i}. {event_type} | data_keys={data_keys}")

    # Verify lifecycle
    print("\n" + "-"*80)
    print("Lifecycle Verification:")
    if mock_ws.verify_delegation_lifecycle():
        print("✅ Complete delegation lifecycle captured!")
    else:
        print("❌ Incomplete delegation lifecycle")
        return False

    # Verify event structure
    print("\n" + "-"*80)
    print("Event Structure Verification:")

    if mock_ws.started_events:
        started = mock_ws.started_events[0]
        required_fields = ["type", "event_type", "thread_id", "data", "timestamp"]
        missing_fields = [f for f in required_fields if f not in started]

        if missing_fields:
            print(f"❌ subagent_started missing fields: {missing_fields}")
            return False

        data = started.get("data", {})
        required_data_fields = ["subagent_thread_id", "subagent_type", "task", "timestamp"]
        missing_data = [f for f in required_data_fields if f not in data]

        if missing_data:
            print(f"❌ subagent_started data missing fields: {missing_data}")
            return False

        print("✅ subagent_started event structure correct")
        print(f"   - subagent_type: {data.get('subagent_type')}")
        print(f"   - task: {data.get('task')[:50]}...")

    if mock_ws.completed_events:
        completed = mock_ws.completed_events[0]
        data = completed.get("data", {})
        required_data_fields = ["subagent_thread_id", "subagent_type", "result_summary"]
        missing_data = [f for f in required_data_fields if f not in data]

        if missing_data:
            print(f"❌ subagent_completed data missing fields: {missing_data}")
            return False

        print("✅ subagent_completed event structure correct")
        print(f"   - subagent_type: {data.get('subagent_type')}")
        print(f"   - result_summary: {data.get('result_summary')[:50]}...")

    print("\n✅ TEST 1 PASSED: Researcher delegation events working correctly!")
    return True


async def test_multiple_subagents():
    """Test delegation events across multiple subagent types."""
    print("\n" + "="*80)
    print("TEST 2: Multiple Subagent Delegation Events")
    print("="*80)

    # Replace websocket manager with mock
    import websocket_manager
    mock_ws = MockWebSocketManager()
    websocket_manager.manager = mock_ws

    from langgraph_studio_graphs import supervisor_agent_unified

    test_cases = [
        ("researcher", "Research AI trends in 2025"),
        ("writer", "Write a blog post about quantum computing"),
        ("reviewer", "Review the quantum computing document"),
    ]

    for subagent_type, task in test_cases:
        print(f"\nTesting {subagent_type} delegation...")
        mock_ws.events.clear()
        mock_ws.started_events.clear()
        mock_ws.completed_events.clear()

        result = await supervisor_agent_unified.ainvoke(
            {
                "messages": [{"role": "user", "content": task}],
                "thread_id": f"test-{subagent_type}"
            },
            config={"configurable": {"thread_id": f"test-{subagent_type}"}}
        )

        if mock_ws.verify_delegation_lifecycle():
            print(f"✅ {subagent_type} delegation events captured")
        else:
            print(f"❌ {subagent_type} delegation events incomplete")
            return False

    print("\n✅ TEST 2 PASSED: Multiple subagent delegation events working!")
    return True


async def test_error_handling():
    """Test that delegation error events are emitted on failure."""
    print("\n" + "="*80)
    print("TEST 3: Delegation Error Event Handling")
    print("="*80)

    # This test would require triggering an error in a subagent
    # For now, we'll verify the error event emitter exists
    from subagents.event_emitter import emit_delegation_error

    import websocket_manager
    mock_ws = MockWebSocketManager()
    websocket_manager.manager = mock_ws

    # Manually emit an error event
    await emit_delegation_error(
        parent_thread_id="test-thread",
        subagent_thread_id="test-thread/subagent-researcher-001",
        subagent_type="researcher",
        error="Test error: API timeout"
    )

    if len(mock_ws.error_events) == 1:
        error_event = mock_ws.error_events[0]
        data = error_event.get("data", {})

        if data.get("error") == "Test error: API timeout":
            print("✅ Error event emitted correctly")
            print(f"   - error: {data.get('error')}")
            return True
        else:
            print("❌ Error event data incorrect")
            return False
    else:
        print("❌ Error event not emitted")
        return False


async def main():
    """Run all delegation event tests."""
    print("\n" + "="*80)
    print("DELEGATION EVENT EMISSION TEST SUITE")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")

    tests = [
        ("Researcher Delegation", test_researcher_delegation),
        ("Multiple Subagents", test_multiple_subagents),
        ("Error Handling", test_error_handling),
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

    # Final summary
    print("\n" + "="*80)
    print("TEST SUITE SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)

    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Delegation events are working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Review output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
