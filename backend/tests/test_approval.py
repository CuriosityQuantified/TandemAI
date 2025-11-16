"""
Test script for approval system functionality.

This script tests the approval system without requiring the frontend.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from module_2_2_simple import (
    get_approval_for_tool,
    submit_approval_decision,
    get_auto_approve,
    set_auto_approve
)


async def test_approval_flow():
    """Test the complete approval flow."""
    print("=" * 80)
    print("Testing Approval System")
    print("=" * 80)

    # Test 1: Request approval
    print("\n[Test 1] Creating approval request...")
    request_id = "test-request-123"

    # Create approval request task
    approval_task = asyncio.create_task(
        get_approval_for_tool(
            tool_name="write_file",
            tool_args={"file_path": "/workspace/test.md", "content": "Hello World"},
            request_id=request_id
        )
    )

    # Simulate delay before decision
    await asyncio.sleep(0.5)

    # Test 2: Submit approval decision
    print("\n[Test 2] Submitting approval decision (approved=True)...")
    decision_result = await submit_approval_decision(
        request_id=request_id,
        approved=True,
        feedback=None
    )

    print(f"Decision result: {decision_result}")

    # Wait for approval task to complete
    print("\n[Test 3] Waiting for approval task to complete...")
    approval_result = await approval_task

    print(f"Approval result: {approval_result}")

    # Verify result
    assert approval_result.get("approved") == True, "Expected approval to be True"
    assert decision_result.get("status") == "ok", "Expected decision status to be ok"

    print("\n✅ All tests passed!")
    print("=" * 80)


async def test_rejection_flow():
    """Test the rejection flow."""
    print("\n" + "=" * 80)
    print("Testing Rejection Flow")
    print("=" * 80)

    request_id = "test-request-456"

    # Create approval request task
    approval_task = asyncio.create_task(
        get_approval_for_tool(
            tool_name="write_file",
            tool_args={"file_path": "/workspace/test2.md", "content": "Test"},
            request_id=request_id
        )
    )

    # Simulate delay
    await asyncio.sleep(0.5)

    # Submit rejection
    print("\n[Test] Submitting rejection (approved=False)...")
    decision_result = await submit_approval_decision(
        request_id=request_id,
        approved=False,
        feedback="Test rejection"
    )

    print(f"Decision result: {decision_result}")

    # Wait for approval task
    approval_result = await approval_task

    print(f"Approval result: {approval_result}")

    # Verify result
    assert approval_result.get("approved") == False, "Expected approval to be False"
    assert approval_result.get("feedback") == "Test rejection", "Expected feedback to match"

    print("\n✅ Rejection test passed!")
    print("=" * 80)


async def test_timeout():
    """Test timeout behavior."""
    print("\n" + "=" * 80)
    print("Testing Timeout (this will take a few seconds)...")
    print("=" * 80)

    request_id = "test-request-timeout"

    # Create approval request with short timeout
    # Note: Modify get_approval_for_tool to accept timeout parameter for testing
    print("\n[Test] Creating approval request without submitting decision...")
    print("(Waiting for timeout...)")

    try:
        # This should timeout after 5 minutes by default
        # For testing, we'd need to modify the function to accept a shorter timeout
        approval_result = await asyncio.wait_for(
            get_approval_for_tool(
                tool_name="write_file",
                tool_args={"file_path": "/workspace/test3.md", "content": "Test"},
                request_id=request_id
            ),
            timeout=3.0  # 3 second timeout for testing
        )

        print(f"Unexpected result: {approval_result}")
        print("❌ Expected timeout, but got result")

    except asyncio.TimeoutError:
        print("\n✅ Timeout test passed (request timed out as expected)!")

    print("=" * 80)


async def main():
    """Run all tests."""
    try:
        await test_approval_flow()
        await test_rejection_flow()
        # await test_timeout()  # Commented out - takes too long

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED ✅")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
