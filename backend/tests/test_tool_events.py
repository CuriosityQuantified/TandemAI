"""
Tests for Tool Event Broadcasting System
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

from src.agui.tool_events import (
    ToolEventBroadcaster,
    broadcast_tool_call,
    set_agui_manager,
    emit_progress
)
from src.agui.events import AGUIEvent, AGUIEventType
from src.agui.server import AGUIConnectionManager


class TestToolEventBroadcaster:
    """Test suite for tool event broadcasting functionality."""

    @pytest.fixture
    def mock_agui_manager(self):
        """Create a mock AG-UI connection manager."""
        manager = MagicMock(spec=AGUIConnectionManager)
        manager.broadcast_to_task = AsyncMock()
        return manager

    @pytest.fixture
    def broadcaster(self, mock_agui_manager):
        """Create a tool event broadcaster with mocked AG-UI manager."""
        broadcaster = ToolEventBroadcaster(agui_manager=mock_agui_manager)
        return broadcaster

    @pytest.mark.asyncio
    async def test_broadcast_tool_event(self, broadcaster, mock_agui_manager):
        """Test broadcasting a tool event."""
        await broadcaster.broadcast_tool_event(
            task_id="test_task",
            tool_name="test_tool",
            event_type="started",
            data={"param": "value"},
            agent_id="test_agent"
        )

        # Verify broadcast was called
        mock_agui_manager.broadcast_to_task.assert_called_once()

        # Check the event structure
        call_args = mock_agui_manager.broadcast_to_task.call_args
        assert call_args[0][0] == "test_task"  # task_id

        event = call_args[0][1]
        assert event.event_type == "tool_started"
        assert event.task_id == "test_task"
        assert event.agent_id == "test_agent"
        assert event.data["tool_name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_track_tool_decorator_success(self, broadcaster):
        """Test the track_tool decorator with successful execution."""

        @broadcaster.track_tool("decorated_tool", task_id="test_task")
        async def sample_tool(value: int) -> int:
            return value * 2

        result = await sample_tool(value=5)

        assert result == 10

        # Verify two broadcasts: started and completed
        assert broadcaster.agui_manager.broadcast_to_task.call_count == 2

        # Check started event
        start_call = broadcaster.agui_manager.broadcast_to_task.call_args_list[0]
        start_event = start_call[0][1]
        assert start_event.event_type == "tool_started"
        assert start_event.data["parameters"]["value"] == 5

        # Check completed event
        complete_call = broadcaster.agui_manager.broadcast_to_task.call_args_list[1]
        complete_event = complete_call[0][1]
        assert complete_event.event_type == "tool_completed"
        assert complete_event.data["status"] == "success"
        assert complete_event.data["result"] == 10

    @pytest.mark.asyncio
    async def test_track_tool_decorator_failure(self, broadcaster):
        """Test the track_tool decorator with execution failure."""

        @broadcaster.track_tool("failing_tool", task_id="test_task")
        async def failing_tool():
            raise ValueError("Tool execution failed")

        with pytest.raises(ValueError):
            await failing_tool()

        # Verify two broadcasts: started and failed
        assert broadcaster.agui_manager.broadcast_to_task.call_count == 2

        # Check failed event
        fail_call = broadcaster.agui_manager.broadcast_to_task.call_args_list[1]
        fail_event = fail_call[0][1]
        assert fail_event.event_type == "tool_failed"
        assert fail_event.data["status"] == "failed"
        assert "Tool execution failed" in fail_event.data["error"]
        assert fail_event.data["error_type"] == "ValueError"

    def test_sanitize_params(self, broadcaster):
        """Test parameter sanitization for sensitive data."""
        params = {
            "query": "test query",
            "api_key": "secret123",
            "password": "password123",
            "data": list(range(100)),  # Large list
            "nested": {
                "token": "token456",
                "safe_field": "visible"
            }
        }

        sanitized = broadcaster._sanitize_params(params)

        assert sanitized["query"] == "test query"
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["data"] == "[100 items]"
        assert sanitized["nested"]["token"] == "***REDACTED***"
        assert sanitized["nested"]["safe_field"] == "visible"

    def test_sanitize_result_truncation(self, broadcaster):
        """Test result sanitization with truncation."""
        # Test string truncation
        long_string = "x" * 10000
        sanitized_string = broadcaster._sanitize_result(long_string)
        assert len(sanitized_string) < 6000
        assert "[truncated" in sanitized_string

        # Test list truncation
        long_list = list(range(100))
        sanitized_list = broadcaster._sanitize_result(long_list)
        assert len(sanitized_list) == 21  # 20 items + truncation message
        assert "and 80 more items" in sanitized_list[-1]

        # Test dict with results truncation
        result_dict = {
            "results": list(range(50)),
            "other_field": "value"
        }
        sanitized_dict = broadcaster._sanitize_result(result_dict)
        assert len(sanitized_dict["results"]) == 10
        assert sanitized_dict["_truncated"] == True
        assert sanitized_dict["_total_results"] == 50

    def test_generate_tool_call_id(self, broadcaster):
        """Test tool call ID generation."""
        id1 = broadcaster._generate_tool_call_id("tool1", "task1")
        id2 = broadcaster._generate_tool_call_id("tool1", "task1")
        id3 = broadcaster._generate_tool_call_id("tool2", "task1")

        # IDs should be unique
        assert id1 != id2
        assert id1 != id3
        assert id2 != id3

        # IDs should have consistent format
        assert len(id1) == 12
        assert all(c in "0123456789abcdef" for c in id1)

    @pytest.mark.asyncio
    async def test_track_progress(self, broadcaster, mock_agui_manager):
        """Test progress tracking for active tools."""
        # First register an active tool
        tool_call_id = "test_tool_123"
        broadcaster.active_tools[tool_call_id] = {
            'tool_name': 'long_running_tool',
            'task_id': 'test_task',
            'agent_id': 'test_agent',
            'started_at': datetime.now().isoformat()
        }

        # Track progress
        broadcaster.track_progress(
            tool_call_id=tool_call_id,
            progress=50.0,
            message="Halfway done"
        )

        # Wait for async task to complete
        await asyncio.sleep(0.1)

        # Verify progress broadcast
        mock_agui_manager.broadcast_to_task.assert_called()

        # Find the progress event call
        progress_call = None
        for call in mock_agui_manager.broadcast_to_task.call_args_list:
            event = call[0][1]
            if event.event_type == "tool_progress":
                progress_call = call
                break

        assert progress_call is not None
        progress_event = progress_call[0][1]
        assert progress_event.data["progress_percentage"] == 50.0
        assert progress_event.data["message"] == "Halfway done"


class TestGlobalFunctions:
    """Test module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_broadcast_tool_call_decorator(self):
        """Test the global broadcast_tool_call decorator."""
        mock_manager = AsyncMock(spec=AGUIConnectionManager)
        set_agui_manager(mock_manager)

        @broadcast_tool_call("global_tool", task_id="global_task")
        async def decorated_function(value: int) -> int:
            return value + 1

        result = await decorated_function(value=10)

        assert result == 11
        assert mock_manager.broadcast_to_task.call_count == 2

    def test_emit_progress_global(self):
        """Test the global emit_progress function."""
        # This just verifies the function exists and can be called
        # Actual testing would require setting up active tools
        emit_progress("tool_123", 75.0, "Three quarters done")
        # No assertion needed - just checking it doesn't error


class TestIntegrationWithTools:
    """Test integration with actual tool implementations."""

    @pytest.mark.asyncio
    async def test_firecrawl_tool_broadcasting(self):
        """Test that Firecrawl tool broadcasts events correctly."""
        from src.tools.firecrawl_tool import FirecrawlTool

        # Create mock AG-UI manager
        mock_manager = AsyncMock(spec=AGUIConnectionManager)
        set_agui_manager(mock_manager)

        # Create Firecrawl tool instance (will fail due to no API key, but decorator should still work)
        tool = FirecrawlTool()

        # Call web_search (will return error due to no client, but should broadcast)
        result = tool.web_search("test query", task_id="test_task")

        # Should have broadcast started and completed/failed events
        assert mock_manager.broadcast_to_task.call_count >= 2

        # Check that result indicates error (no API key)
        assert result["status"] == "error"
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_e2b_tool_broadcasting(self):
        """Test that E2B tool broadcasts events correctly."""
        from src.tools.e2b_tool import E2BTool

        # Create mock AG-UI manager
        mock_manager = AsyncMock(spec=AGUIConnectionManager)
        set_agui_manager(mock_manager)

        # Create E2B tool instance (will fail due to no API key, but decorator should still work)
        tool = E2BTool()

        # Call execute_python (will return error due to no API key, but should broadcast)
        result = tool.execute_python("print('test')", task_id="test_task")

        # Should have broadcast started and completed events
        assert mock_manager.broadcast_to_task.call_count >= 2

        # Check that result indicates error (no API key)
        assert result["status"] == "error"
        assert "not configured" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])