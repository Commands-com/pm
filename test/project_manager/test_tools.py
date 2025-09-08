"""
Comprehensive Test Suite for MCP Tools

Tests all MCP tools with various scenarios including success cases, error cases,
and edge cases. Uses pytest-asyncio for async testing and mocking for isolated
unit tests and integration tests for database interactions.

Test Coverage:
- BaseTool abstract functionality
- GetAvailableTasks with status filtering and lock exclusion
- AcquireTaskLock success/failure scenarios and race conditions
- UpdateTaskStatus with lock validation and auto-release
- ReleaseTaskLock with agent validation
- WebSocket broadcasting integration
- Error handling and edge cases
"""

import asyncio
import json
import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from task_manager.database import TaskDatabase
from task_manager.api import ConnectionManager
from task_manager.tools import (
    BaseTool, GetAvailableTasks, AcquireTaskLock, 
    UpdateTaskStatus, ReleaseTaskLock, create_tool_instance, AVAILABLE_TOOLS
)


class TestBaseTool:
    """Test BaseTool abstract class functionality."""
    
    class ConcreteTestTool(BaseTool):
        """Concrete implementation of BaseTool for testing."""
        async def apply(self, **kwargs) -> str:
            return "test_result"
    
    @pytest.fixture
    def mock_database(self):
        """Mock TaskDatabase for isolated testing."""
        return MagicMock(spec=TaskDatabase)
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock ConnectionManager for isolated testing."""
        manager = MagicMock(spec=ConnectionManager)
        manager.broadcast = AsyncMock()
        return manager
    
    @pytest.fixture
    def concrete_tool(self, mock_database, mock_websocket_manager):
        """Create concrete tool instance for testing."""
        return self.ConcreteTestTool(mock_database, mock_websocket_manager)
    
    def test_base_tool_initialization(self, concrete_tool, mock_database, mock_websocket_manager):
        """Test BaseTool initialization with dependencies."""
        assert concrete_tool.db == mock_database
        assert concrete_tool.websocket_manager == mock_websocket_manager
    
    def test_format_success_response(self, concrete_tool):
        """Test success response formatting."""
        response = concrete_tool._format_success_response("Operation successful", task_id=123)
        data = json.loads(response)
        
        assert data["success"] is True
        assert data["message"] == "Operation successful"
        assert data["task_id"] == 123
    
    def test_format_error_response(self, concrete_tool):
        """Test error response formatting."""
        response = concrete_tool._format_error_response("Operation failed", error_code="INVALID_INPUT")
        data = json.loads(response)
        
        assert data["success"] is False
        assert data["message"] == "Operation failed"
        assert data["error_code"] == "INVALID_INPUT"
    
    @pytest.mark.asyncio
    async def test_broadcast_event_success(self, concrete_tool, mock_websocket_manager):
        """Test successful event broadcasting."""
        await concrete_tool._broadcast_event("test.event", task_id=123, agent_id="test_agent")
        
        mock_websocket_manager.broadcast.assert_called_once()
        call_args = mock_websocket_manager.broadcast.call_args[0][0]
        
        assert call_args["type"] == "test.event"
        assert call_args["task_id"] == 123
        assert call_args["agent_id"] == "test_agent"
        assert "timestamp" in call_args
    
    @pytest.mark.asyncio
    async def test_broadcast_event_failure_handling(self, concrete_tool, mock_websocket_manager):
        """Test that broadcast failures don't raise exceptions."""
        mock_websocket_manager.broadcast.side_effect = Exception("Broadcast failed")
        
        # Should not raise exception
        await concrete_tool._broadcast_event("test.event", task_id=123)
        
        mock_websocket_manager.broadcast.assert_called_once()


class TestDatabaseIntegration:
    """Integration tests using real database operations."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for integration testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        db = TaskDatabase(path)
        yield db
        
        db.close()
        os.unlink(path)
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock ConnectionManager for integration testing."""
        manager = MagicMock(spec=ConnectionManager)
        manager.broadcast = AsyncMock()
        return manager
    
    @pytest.fixture
    def sample_data(self, temp_db):
        """Create sample data for testing."""
        # Create epic
        epic_id = temp_db.create_epic("Test Epic", "Test epic description")
        
        # Create story
        story_id = temp_db.create_story(epic_id, "Test Story", "Test story description")
        
        # Create tasks with different statuses
        task1_id = temp_db.create_task("Task 1", "Test task 1", story_id=story_id)
        task2_id = temp_db.create_task("Task 2", "Test task 2", story_id=story_id)
        task3_id = temp_db.create_task("Task 3", "Test task 3", story_id=story_id)
        
        # Set different statuses
        temp_db.update_task_status(task2_id, "in_progress", "test_agent")
        temp_db.update_task_status(task3_id, "completed", "test_agent")
        
        return {
            "epic_id": epic_id,
            "story_id": story_id,
            "task_ids": [task1_id, task2_id, task3_id]
        }
    
    @pytest.mark.asyncio
    async def test_get_available_tasks_integration(self, temp_db, mock_websocket_manager, sample_data):
        """Integration test for GetAvailableTasks with real database."""
        tool = GetAvailableTasks(temp_db, mock_websocket_manager)
        
        # Test getting pending tasks
        result = await tool.apply(status="TODO")
        tasks = json.loads(result)
        
        assert isinstance(tasks, list)
        assert len(tasks) >= 1  # At least one pending task
        
        # Verify task structure
        for task in tasks:
            assert "id" in task
            assert "name" in task
            assert "status" in task
            assert "available" in task
            assert task["available"] is True
    
    @pytest.mark.asyncio
    async def test_acquire_lock_integration(self, temp_db, mock_websocket_manager, sample_data):
        """Integration test for AcquireTaskLock with real database."""
        tool = AcquireTaskLock(temp_db, mock_websocket_manager)
        task_id = str(sample_data["task_ids"][0])
        
        # Test successful lock acquisition
        result = await tool.apply(task_id=task_id, agent_id="test_agent", timeout=300)
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["task_id"] == int(task_id)
        assert response["agent_id"] == "test_agent"
        assert response["timeout"] == 300
        
        # Verify WebSocket broadcast was called
        mock_websocket_manager.broadcast.assert_called()
    
    @pytest.mark.asyncio
    async def test_acquire_lock_already_locked(self, temp_db, mock_websocket_manager, sample_data):
        """Test lock acquisition failure when task is already locked."""
        tool = AcquireTaskLock(temp_db, mock_websocket_manager)
        task_id = str(sample_data["task_ids"][0])
        
        # First agent acquires lock
        await tool.apply(task_id=task_id, agent_id="agent1", timeout=300)
        
        # Second agent attempts to acquire same lock
        result = await tool.apply(task_id=task_id, agent_id="agent2", timeout=300)
        response = json.loads(result)
        
        assert response["success"] is False
        assert "already locked" in response["message"]
        assert response["lock_holder"] == "agent1"
    
    @pytest.mark.asyncio
    async def test_update_status_integration(self, temp_db, mock_websocket_manager, sample_data):
        """Integration test for UpdateTaskStatus with lock validation."""
        acquire_tool = AcquireTaskLock(temp_db, mock_websocket_manager)
        update_tool = UpdateTaskStatus(temp_db, mock_websocket_manager)
        task_id = str(sample_data["task_ids"][0])
        
        # First acquire lock
        await acquire_tool.apply(task_id=task_id, agent_id="test_agent", timeout=300)
        
        # Then update status
        result = await update_tool.apply(task_id=task_id, status="DONE", agent_id="test_agent")
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["status"] == "completed"
        assert response.get("lock_released") is True  # Should auto-release on completion
    
    @pytest.mark.asyncio
    async def test_update_status_without_lock(self, temp_db, mock_websocket_manager, sample_data):
        """Test status update failure without lock."""
        tool = UpdateTaskStatus(temp_db, mock_websocket_manager)
        task_id = str(sample_data["task_ids"][0])
        
        result = await tool.apply(task_id=task_id, status="DONE", agent_id="test_agent")
        response = json.loads(result)
        
        assert response["success"] is False
        assert "must be locked" in response["message"]
    
    @pytest.mark.asyncio
    async def test_release_lock_integration(self, temp_db, mock_websocket_manager, sample_data):
        """Integration test for ReleaseTaskLock."""
        acquire_tool = AcquireTaskLock(temp_db, mock_websocket_manager)
        release_tool = ReleaseTaskLock(temp_db, mock_websocket_manager)
        task_id = str(sample_data["task_ids"][0])
        
        # First acquire lock
        await acquire_tool.apply(task_id=task_id, agent_id="test_agent", timeout=300)
        
        # Then release lock
        result = await release_tool.apply(task_id=task_id, agent_id="test_agent")
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["task_id"] == int(task_id)
        assert response["agent_id"] == "test_agent"
    
    @pytest.mark.asyncio
    async def test_release_lock_unauthorized(self, temp_db, mock_websocket_manager, sample_data):
        """Test lock release failure by unauthorized agent."""
        acquire_tool = AcquireTaskLock(temp_db, mock_websocket_manager)
        release_tool = ReleaseTaskLock(temp_db, mock_websocket_manager)
        task_id = str(sample_data["task_ids"][0])
        
        # Agent 1 acquires lock
        await acquire_tool.apply(task_id=task_id, agent_id="agent1", timeout=300)
        
        # Agent 2 attempts to release lock
        result = await release_tool.apply(task_id=task_id, agent_id="agent2")
        response = json.loads(result)
        
        assert response["success"] is False
        assert "Lock is held by agent" in response["message"]
        assert response["lock_holder"] == "agent1"


class TestGetAvailableTasksEdgeCases:
    """Test edge cases for GetAvailableTasks tool."""
    
    @pytest.fixture
    def tool(self):
        """Create GetAvailableTasks with mocked dependencies."""
        mock_db = MagicMock(spec=TaskDatabase)
        mock_ws = MagicMock(spec=ConnectionManager)
        mock_ws.broadcast = AsyncMock()
        return GetAvailableTasks(mock_db, mock_ws)
    
    @pytest.mark.asyncio
    async def test_invalid_status(self, tool):
        """Test handling of invalid status parameter."""
        result = await tool.apply(status="INVALID_STATUS")
        response = json.loads(result)
        
        assert response["success"] is False
        assert "Invalid status" in response["message"]
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, tool):
        """Test handling of database errors."""
        tool.db.get_available_tasks.side_effect = Exception("Database connection failed")
        
        result = await tool.apply(status="TODO")
        response = json.loads(result)
        
        assert response["success"] is False
        assert "Failed to retrieve available tasks" in response["message"]
    
    @pytest.mark.asyncio
    async def test_empty_task_list(self, tool):
        """Test handling of empty task list."""
        tool.db.get_available_tasks.return_value = []
        
        result = await tool.apply(status="TODO")
        tasks = json.loads(result)
        
        assert isinstance(tasks, list)
        assert len(tasks) == 0
    
    @pytest.mark.asyncio
    async def test_locked_task_filtering(self, tool):
        """Test filtering of locked tasks."""
        current_time = datetime.now(timezone.utc)
        future_time = (current_time + timedelta(minutes=5)).isoformat() + 'Z'
        
        mock_tasks = [
            {
                "id": 1,
                "name": "Available Task",
                "status": "pending",
                "lock_holder": None,
                "lock_expires_at": None
            },
            {
                "id": 2, 
                "name": "Locked Task",
                "status": "pending",
                "lock_holder": "other_agent",
                "lock_expires_at": future_time
            }
        ]
        
        tool.db.get_available_tasks.return_value = mock_tasks
        
        result = await tool.apply(status="TODO", include_locked=False)
        tasks = json.loads(result)
        
        # Should only return available task
        assert len(tasks) == 1
        assert tasks[0]["id"] == 1
        assert tasks[0]["available"] is True


class TestToolInputValidation:
    """Test input validation across all tools."""
    
    @pytest.fixture
    def tools(self):
        """Create all tools with mocked dependencies."""
        mock_db = MagicMock(spec=TaskDatabase)
        mock_ws = MagicMock(spec=ConnectionManager)
        mock_ws.broadcast = AsyncMock()
        
        return {
            "get_available_tasks": GetAvailableTasks(mock_db, mock_ws),
            "acquire_task_lock": AcquireTaskLock(mock_db, mock_ws),
            "update_task_status": UpdateTaskStatus(mock_db, mock_ws),
            "release_task_lock": ReleaseTaskLock(mock_db, mock_ws)
        }
    
    @pytest.mark.asyncio
    async def test_invalid_task_id_format(self, tools):
        """Test handling of invalid task_id format."""
        acquire_tool = tools["acquire_task_lock"]
        
        result = await acquire_tool.apply(task_id="invalid_id", agent_id="test_agent")
        response = json.loads(result)
        
        assert response["success"] is False
        assert "Invalid task_id" in response["message"]
    
    @pytest.mark.asyncio
    async def test_empty_agent_id(self, tools):
        """Test handling of empty agent_id."""
        acquire_tool = tools["acquire_task_lock"]
        
        result = await acquire_tool.apply(task_id="123", agent_id="")
        response = json.loads(result)
        
        assert response["success"] is False
        assert "agent_id cannot be empty" in response["message"]
    
    @pytest.mark.asyncio
    async def test_invalid_timeout_range(self, tools):
        """Test handling of invalid timeout values."""
        acquire_tool = tools["acquire_task_lock"]
        
        # Test negative timeout
        result = await acquire_tool.apply(task_id="123", agent_id="test_agent", timeout=-1)
        response = json.loads(result)
        assert response["success"] is False
        assert "timeout must be between" in response["message"]
        
        # Test excessive timeout
        result = await acquire_tool.apply(task_id="123", agent_id="test_agent", timeout=5000)
        response = json.loads(result)
        assert response["success"] is False
        assert "timeout must be between" in response["message"]


class TestConcurrencyAndRaceConditions:
    """Test concurrent operations and race condition handling."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for concurrency testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        db = TaskDatabase(path)
        # Create a test task
        task_id = db.create_task("Concurrent Test Task", "Test task for concurrency")
        
        yield db, task_id
        
        db.close()
        os.unlink(path)
    
    @pytest.mark.asyncio
    async def test_concurrent_lock_acquisition(self, temp_db):
        """Test that only one agent can acquire lock in concurrent scenario."""
        db, task_id = temp_db
        mock_ws = MagicMock(spec=ConnectionManager)
        mock_ws.broadcast = AsyncMock()
        
        tool1 = AcquireTaskLock(db, mock_ws)
        tool2 = AcquireTaskLock(db, mock_ws)
        
        # Simulate concurrent lock acquisition attempts
        results = await asyncio.gather(
            tool1.apply(task_id=str(task_id), agent_id="agent1", timeout=300),
            tool2.apply(task_id=str(task_id), agent_id="agent2", timeout=300),
            return_exceptions=True
        )
        
        responses = [json.loads(result) for result in results]
        
        # Exactly one should succeed
        successful = [r for r in responses if r["success"]]
        failed = [r for r in responses if not r["success"]]
        
        assert len(successful) == 1
        assert len(failed) == 1
        
        # Failed attempt should indicate task is locked
        assert "locked" in failed[0]["message"]


class TestToolRegistry:
    """Test tool registry and factory functionality."""
    
    def test_available_tools_registry(self):
        """Test that all expected tools are in registry."""
        expected_tools = {
            "get_available_tasks",
            "acquire_task_lock", 
            "update_task_status",
            "release_task_lock"
        }
        
        assert set(AVAILABLE_TOOLS.keys()) == expected_tools
    
    def test_create_tool_instance(self):
        """Test tool factory function."""
        mock_db = MagicMock(spec=TaskDatabase)
        mock_ws = MagicMock(spec=ConnectionManager)
        
        tool = create_tool_instance("get_available_tasks", mock_db, mock_ws)
        
        assert isinstance(tool, GetAvailableTasks)
        assert tool.db == mock_db
        assert tool.websocket_manager == mock_ws
    
    def test_create_unknown_tool_instance(self):
        """Test factory function with unknown tool name."""
        mock_db = MagicMock(spec=TaskDatabase)
        mock_ws = MagicMock(spec=ConnectionManager)
        
        with pytest.raises(KeyError, match="Unknown tool"):
            create_tool_instance("unknown_tool", mock_db, mock_ws)


class TestWebSocketIntegration:
    """Test WebSocket broadcasting integration."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        db = TaskDatabase(path)
        task_id = db.create_task("WebSocket Test Task", "Test task for WebSocket")
        
        yield db, task_id
        
        db.close()
        os.unlink(path)
    
    @pytest.mark.asyncio
    async def test_lock_acquisition_broadcasts_event(self, temp_db):
        """Test that lock acquisition broadcasts correct WebSocket event."""
        db, task_id = temp_db
        mock_ws = MagicMock(spec=ConnectionManager)
        mock_ws.broadcast = AsyncMock()
        
        tool = AcquireTaskLock(db, mock_ws)
        await tool.apply(task_id=str(task_id), agent_id="test_agent", timeout=300)
        
        # Verify broadcast was called with correct event
        mock_ws.broadcast.assert_called()
        call_args = mock_ws.broadcast.call_args[0][0]
        
        assert call_args["type"] == "task.locked"
        assert call_args["task_id"] == task_id
        assert call_args["agent_id"] == "test_agent"
    
    @pytest.mark.asyncio
    async def test_status_update_broadcasts_event(self, temp_db):
        """Test that status updates broadcast correct WebSocket events."""
        db, task_id = temp_db
        mock_ws = MagicMock(spec=ConnectionManager)
        mock_ws.broadcast = AsyncMock()
        
        # First acquire lock
        acquire_tool = AcquireTaskLock(db, mock_ws)
        await acquire_tool.apply(task_id=str(task_id), agent_id="test_agent", timeout=300)
        
        # Reset mock to test status update broadcast
        mock_ws.reset_mock()
        mock_ws.broadcast = AsyncMock()
        
        # Update status
        update_tool = UpdateTaskStatus(db, mock_ws)
        await update_tool.apply(task_id=str(task_id), status="DONE", agent_id="test_agent")
        
        # Should broadcast both status change and lock release events
        assert mock_ws.broadcast.call_count >= 1
        
        # Check that status change event was broadcast
        call_args_list = [call[0][0] for call in mock_ws.broadcast.call_args_list]
        status_events = [event for event in call_args_list if event["type"] == "task.status_changed"]
        
        assert len(status_events) >= 1
        assert status_events[0]["task_id"] == task_id
        assert status_events[0]["status"] == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])