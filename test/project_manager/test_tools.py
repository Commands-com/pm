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
    UpdateTaskStatus, ReleaseTaskLock, CreateTaskTool,
    ListProjectsTool, ListEpicsTool, ListTasksTool, DeleteTaskTool,
    create_tool_instance, AVAILABLE_TOOLS
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
        # Create project
        project_id = temp_db.create_project("Test Project", "Test project description")
        
        # Create epic
        epic_id = temp_db.create_epic(project_id, "Test Epic", "Test epic description")
        
        # Create tasks with different statuses
        task1_id = temp_db.create_task(epic_id, "Task 1", "Test task 1")
        task2_id = temp_db.create_task(epic_id, "Task 2", "Test task 2")
        task3_id = temp_db.create_task(epic_id, "Task 3", "Test task 3")
        
        # Set different statuses
        temp_db.update_task_status(task2_id, "in_progress", "test_agent")
        temp_db.update_task_status(task3_id, "completed", "test_agent")
        
        return {
            "project_id": project_id,
            "epic_id": epic_id,
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
        """Test status update auto-acquires lock when unlocked."""
        tool = UpdateTaskStatus(temp_db, mock_websocket_manager)
        task_id = str(sample_data["task_ids"][0])
        
        result = await tool.apply(task_id=task_id, status="DONE", agent_id="test_agent")
        response = json.loads(result)
        
        assert response["success"] is True
        # DB vocabulary in tool response
        assert response["status"] == "completed"
        # Auto-acquired lock should be released on DONE
        assert response.get("lock_released") is True
    
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
        # Create test hierarchy: project -> epic -> task
        project_id = db.create_project("Test Project", "Project for concurrency testing")
        epic_id = db.create_epic(project_id, "Test Epic", "Epic for concurrency testing")
        task_id = db.create_task(epic_id, "Concurrent Test Task", "Test task for concurrency")
        
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
            "release_task_lock",
            "create_task",
            "update_task",
            "get_task_details",
            "list_projects",
            "list_epics",
            "list_tasks",
            "delete_task"
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
        # Create test hierarchy: project -> epic -> task
        project_id = db.create_project("Test Project", "Project for WebSocket testing")
        epic_id = db.create_epic(project_id, "Test Epic", "Epic for WebSocket testing")
        task_id = db.create_task(epic_id, "WebSocket Test Task", "Test task for WebSocket")
        
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
        # UI vocabulary is broadcast in events
        assert status_events[0]["status"] == "DONE"


class TestCreateTaskTool:
    """Test CreateTaskTool with comprehensive RA-Light testing."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock database with all necessary methods for CreateTaskTool."""
        db = MagicMock(spec=TaskDatabase)
        
        # Mock upsert methods - return (id, was_created) tuple
        db.upsert_project_with_status.return_value = (1, True)
        db.upsert_epic_with_status.return_value = (1, True)
        db.get_epic_with_project_info.return_value = {
            'epic_id': 1, 'epic_name': 'Test Epic',
            'project_id': 1, 'project_name': 'Test Project'
        }
        
        # Mock task creation
        db.create_task_with_ra_metadata.return_value = 123
        db.add_task_log_entry.return_value = 1
        
        return db
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager for testing."""
        ws_manager = AsyncMock(spec=ConnectionManager)
        ws_manager.optimized_broadcast = AsyncMock()
        ws_manager.broadcast_enriched_event = AsyncMock()
        return ws_manager
    
    @pytest.fixture
    def create_task_tool(self, mock_database, mock_websocket_manager):
        """CreateTaskTool instance with mocked dependencies."""
        return CreateTaskTool(mock_database, mock_websocket_manager)
    
    @pytest.mark.asyncio
    async def test_create_task_with_epic_id_success(self, create_task_tool, mock_database, mock_websocket_manager):
        """Test successful task creation using existing epic_id."""
        result = await create_task_tool.apply(
            name="Test Task",
            description="Test Description", 
            epic_id=1,
            ra_mode="ra-light",
            ra_score=7
        )
        
        # Parse JSON response
        response = json.loads(result)
        assert response["success"] is True
        assert "Test Task" in response["message"]
        assert response["task_id"] == 123
        assert response["ra_score"] == 7
        assert response["ra_mode"] == "ra-light"
        
        # Verify database calls
        mock_database.get_epic_with_project_info.assert_called_once_with(1)
        mock_database.create_task_with_ra_metadata.assert_called_once()
        # Verify two log entries are created: task creation + prompt snapshot
        assert mock_database.add_task_log_entry.call_count == 2
        
        # Verify task creation log entry
        create_call = mock_database.add_task_log_entry.call_args_list[0]
        assert create_call[0][0] == 123  # task_id
        assert create_call[0][1] == 'create'  # entry_type
        assert create_call[0][2]['agent_action'] == 'task_created'  # entry_data
        
        # Verify prompt snapshot log entry  
        prompt_call = mock_database.add_task_log_entry.call_args_list[1]
        assert prompt_call[0][0] == 123  # task_id
        assert prompt_call[0][1] == 'prompt'  # entry_type
        assert 'prompt_snapshot' in prompt_call[0][2]  # entry_data
        
        # Verify WebSocket broadcast
        mock_websocket_manager.broadcast_enriched_event.assert_called_once()
        event_type, broadcast_data = mock_websocket_manager.broadcast_enriched_event.call_args[0]
        assert event_type == "task.created"
        assert broadcast_data["task"]["id"] == 123
        assert broadcast_data["task"]["name"] == "Test Task"
    
    @pytest.mark.asyncio
    async def test_create_task_with_project_epic_names_success(self, create_task_tool, mock_database, mock_websocket_manager):
        """Test successful task creation with project/epic upsert."""
        result = await create_task_tool.apply(
            name="New Task",
            description="New Description",
            project_name="New Project",
            epic_name="New Epic", 
            ra_mode="ra-full"
        )
        
        response = json.loads(result)
        assert response["success"] is True
        assert response["task_id"] == 123
        
        # Verify upsert calls
        mock_database.upsert_project_with_status.assert_called_once_with("New Project", "")
        mock_database.upsert_epic_with_status.assert_called_once_with(1, "New Epic", "")
        mock_database.create_task_with_ra_metadata.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_task_ra_complexity_auto_assessment(self, create_task_tool, mock_database, mock_websocket_manager):
        """Test RA complexity auto-assessment algorithm."""
        # Test with complex task characteristics
        long_description = "x" * 600  # Long description adds complexity
        dependencies = [1, 2, 3, 4, 5, 6]  # Many dependencies add complexity
        ra_tags = ["tag" + str(i) for i in range(12)]  # Many tags add complexity
        
        result = await create_task_tool.apply(
            name="Complex Task",
            description=long_description,
            epic_id=1,
            ra_mode="ra-full",  # RA-full adds complexity
            dependencies=dependencies,
            ra_tags=ra_tags
        )
        
        response = json.loads(result)
        assert response["success"] is True
        
        # Verify auto-assessed complexity is high (should be close to max due to all factors)
        assert response["ra_score"] >= 8  # Should be high complexity
        assert response["ra_score"] <= 10  # Clamped to max
        
        # Verify database was called with auto-assessed score
        create_call = mock_database.create_task_with_ra_metadata.call_args
        assert create_call[1]["ra_score"] >= 8
    
    @pytest.mark.asyncio
    async def test_create_task_parameter_validation_errors(self, create_task_tool):
        """Test parameter validation error cases."""
        # Test empty name
        result = await create_task_tool.apply(name="")
        response = json.loads(result)
        assert response["success"] is False
        assert "Task name is required" in response["message"]
        
        # Test missing epic identification
        result = await create_task_tool.apply(name="Test")
        response = json.loads(result)
        assert response["success"] is False
        assert "Either epic_id or epic_name must be provided" in response["message"]
        
        # Test conflicting epic parameters
        result = await create_task_tool.apply(name="Test", epic_id=1, epic_name="Epic")
        response = json.loads(result)
        assert response["success"] is False
        assert "Provide either epic_id or epic_name, not both" in response["message"]
        
        # Test invalid RA score
        result = await create_task_tool.apply(name="Test", epic_id=1, ra_score=11)
        response = json.loads(result)
        assert response["success"] is False
        assert "ra_score must be between 1 and 10" in response["message"]
        
        # Test invalid RA mode
        result = await create_task_tool.apply(name="Test", epic_id=1, ra_mode="invalid")
        response = json.loads(result)
        assert response["success"] is False
        assert "ra_mode must be one of" in response["message"]
    
    @pytest.mark.asyncio
    async def test_create_task_database_integrity_error(self, create_task_tool, mock_database, mock_websocket_manager):
        """Test handling of database integrity errors."""
        import sqlite3
        mock_database.create_task_with_ra_metadata.side_effect = sqlite3.IntegrityError("Foreign key constraint failed")
        
        result = await create_task_tool.apply(
            name="Test Task",
            epic_id=999  # Non-existent epic
        )
        
        response = json.loads(result)
        assert response["success"] is False
        assert "Database constraint violation" in response["message"]
        assert "error_details" in response
    
    @pytest.mark.asyncio
    async def test_create_task_websocket_broadcast_with_session(self, create_task_tool, mock_database, mock_websocket_manager):
        """Test WebSocket broadcasting with client session for auto-switch."""
        result = await create_task_tool.apply(
            name="Session Task",
            epic_id=1,
            client_session_id="client123"
        )
        
        response = json.loads(result)
        assert response["success"] is True
        
        # Verify WebSocket broadcast includes session data
        mock_websocket_manager.broadcast_enriched_event.assert_called_once()
        event_type, broadcast_data = mock_websocket_manager.broadcast_enriched_event.call_args[0]
        assert event_type == "task.created"
        assert broadcast_data["initiator"] == "client123"
        assert broadcast_data["flags"]["project_created"] is False
        assert broadcast_data["flags"]["epic_created"] is False
    
    @pytest.mark.asyncio
    async def test_create_task_prompt_snapshot_auto_capture(self, create_task_tool, mock_database, mock_websocket_manager):
        """Test automatic prompt snapshot capture for RA modes."""
        result = await create_task_tool.apply(
            name="RA Task",
            epic_id=1,
            ra_mode="ra-light"
        )
        
        response = json.loads(result)
        assert response["success"] is True
        
        # Verify task creation was called with auto-captured prompt
        create_call = mock_database.create_task_with_ra_metadata.call_args
        assert create_call[1]["prompt_snapshot"] is not None
        assert "RA methodology system instructions active" in create_call[1]["prompt_snapshot"]


class TestListProjectsTool:
    """Test ListProjectsTool functionality."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock TaskDatabase for testing."""
        return MagicMock(spec=TaskDatabase)
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock ConnectionManager for testing."""
        manager = MagicMock(spec=ConnectionManager)
        manager.broadcast = AsyncMock()
        return manager
    
    @pytest.fixture
    def list_projects_tool(self, mock_database, mock_websocket_manager):
        """Create ListProjectsTool instance for testing."""
        from task_manager.tools import ListProjectsTool
        return ListProjectsTool(mock_database, mock_websocket_manager)
    
    @pytest.mark.asyncio
    async def test_list_projects_basic(self, list_projects_tool, mock_database):
        """Test basic project listing without filters."""
        mock_database.list_projects_filtered.return_value = [
            {"id": 1, "name": "Project A", "description": "Description A", "created_at": "2023-01-01", "updated_at": "2023-01-01"},
            {"id": 2, "name": "Project B", "description": "Description B", "created_at": "2023-01-02", "updated_at": "2023-01-02"}
        ]
        
        result = await list_projects_tool.apply()
        
        projects = json.loads(result)
        assert len(projects) == 2
        assert projects[0]["name"] == "Project A"
        assert projects[1]["name"] == "Project B"
        mock_database.list_projects_filtered.assert_called_once_with(status=None, limit=None)
    
    @pytest.mark.asyncio
    async def test_list_projects_with_limit(self, list_projects_tool, mock_database):
        """Test project listing with limit parameter."""
        mock_database.list_projects_filtered.return_value = [
            {"id": 1, "name": "Project A", "description": "Description A", "created_at": "2023-01-01", "updated_at": "2023-01-01"}
        ]
        
        result = await list_projects_tool.apply(limit=1)
        
        projects = json.loads(result)
        assert len(projects) == 1
        mock_database.list_projects_filtered.assert_called_once_with(status=None, limit=1)
    
    @pytest.mark.asyncio
    async def test_list_projects_invalid_limit(self, list_projects_tool):
        """Test error handling for invalid limit."""
        result = await list_projects_tool.apply(limit=0)
        
        response = json.loads(result)
        assert "success" in response
        assert response["success"] == False
        assert "Limit must be a positive integer" in response["message"]
    
    @pytest.mark.asyncio
    async def test_list_projects_database_error(self, list_projects_tool, mock_database):
        """Test error handling for database errors."""
        mock_database.list_projects_filtered.side_effect = Exception("Database error")
        
        result = await list_projects_tool.apply()
        
        response = json.loads(result)
        assert "success" in response
        assert response["success"] == False
        assert "Failed to list projects" in response["message"]


class TestListEpicsTool:
    """Test ListEpicsTool functionality."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock TaskDatabase for testing."""
        return MagicMock(spec=TaskDatabase)
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock ConnectionManager for testing."""
        manager = MagicMock(spec=ConnectionManager)
        manager.broadcast = AsyncMock()
        return manager
    
    @pytest.fixture
    def list_epics_tool(self, mock_database, mock_websocket_manager):
        """Create ListEpicsTool instance for testing."""
        from task_manager.tools import ListEpicsTool
        return ListEpicsTool(mock_database, mock_websocket_manager)
    
    @pytest.mark.asyncio
    async def test_list_epics_basic(self, list_epics_tool, mock_database):
        """Test basic epic listing without filters."""
        mock_database.list_epics_filtered.return_value = [
            {"id": 1, "name": "Epic A", "description": "Description A", "project_id": 1, "project_name": "Project 1", "created_at": "2023-01-01"},
            {"id": 2, "name": "Epic B", "description": "Description B", "project_id": 1, "project_name": "Project 1", "created_at": "2023-01-02"}
        ]
        
        result = await list_epics_tool.apply()
        
        epics = json.loads(result)
        assert len(epics) == 2
        assert epics[0]["name"] == "Epic A"
        assert epics[1]["name"] == "Epic B"
        assert epics[0]["project_name"] == "Project 1"
        mock_database.list_epics_filtered.assert_called_once_with(project_id=None, limit=None)
    
    @pytest.mark.asyncio
    async def test_list_epics_with_project_filter(self, list_epics_tool, mock_database):
        """Test epic listing with project filtering."""
        mock_database.list_epics_filtered.return_value = [
            {"id": 1, "name": "Epic A", "description": "Description A", "project_id": 2, "project_name": "Project 2", "created_at": "2023-01-01"}
        ]
        
        result = await list_epics_tool.apply(project_id=2)
        
        epics = json.loads(result)
        assert len(epics) == 1
        assert epics[0]["project_id"] == 2
        mock_database.list_epics_filtered.assert_called_once_with(project_id=2, limit=None)
    
    @pytest.mark.asyncio
    async def test_list_epics_invalid_project_id(self, list_epics_tool):
        """Test error handling for invalid project_id."""
        result = await list_epics_tool.apply(project_id=0)
        
        response = json.loads(result)
        assert "success" in response
        assert response["success"] == False
        assert "Project ID must be a positive integer" in response["message"]
    
    @pytest.mark.asyncio
    async def test_list_epics_with_limit(self, list_epics_tool, mock_database):
        """Test epic listing with limit parameter."""
        mock_database.list_epics_filtered.return_value = [
            {"id": 1, "name": "Epic A", "description": "Description A", "project_id": 1, "project_name": "Project 1", "created_at": "2023-01-01"}
        ]
        
        result = await list_epics_tool.apply(limit=1)
        
        epics = json.loads(result)
        assert len(epics) == 1
        mock_database.list_epics_filtered.assert_called_once_with(project_id=None, limit=1)


class TestListTasksTool:
    """Test ListTasksTool functionality."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock TaskDatabase for testing."""
        return MagicMock(spec=TaskDatabase)
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock ConnectionManager for testing."""
        manager = MagicMock(spec=ConnectionManager)
        manager.broadcast = AsyncMock()
        return manager
    
    @pytest.fixture
    def list_tasks_tool(self, mock_database, mock_websocket_manager):
        """Create ListTasksTool instance for testing."""
        from task_manager.tools import ListTasksTool
        return ListTasksTool(mock_database, mock_websocket_manager)
    
    @pytest.mark.asyncio
    async def test_list_tasks_basic(self, list_tasks_tool, mock_database):
        """Test basic task listing without filters."""
        mock_database.list_tasks_filtered.return_value = [
            {"id": 1, "name": "Task A", "status": "pending", "ra_score": 5, "epic_name": "Epic 1", "project_name": "Project 1"},
            {"id": 2, "name": "Task B", "status": "in_progress", "ra_score": 7, "epic_name": "Epic 1", "project_name": "Project 1"}
        ]
        
        result = await list_tasks_tool.apply()
        
        tasks = json.loads(result)
        assert len(tasks) == 2
        assert tasks[0]["name"] == "Task A"
        assert tasks[1]["name"] == "Task B"
        assert tasks[0]["ra_score"] == 5
        mock_database.list_tasks_filtered.assert_called_once_with(project_id=None, epic_id=None, status=None, limit=None)
    
    @pytest.mark.asyncio
    async def test_list_tasks_with_all_filters(self, list_tasks_tool, mock_database):
        """Test task listing with all filtering options."""
        mock_database.list_tasks_filtered.return_value = [
            {"id": 1, "name": "Task A", "status": "pending", "ra_score": 5, "epic_name": "Epic 1", "project_name": "Project 1"}
        ]
        
        result = await list_tasks_tool.apply(project_id=1, epic_id=2, status="pending", limit=10)
        
        tasks = json.loads(result)
        assert len(tasks) == 1
        mock_database.list_tasks_filtered.assert_called_once_with(project_id=1, epic_id=2, status="pending", limit=10)
    
    @pytest.mark.asyncio
    async def test_list_tasks_status_vocabulary_mapping(self, list_tasks_tool, mock_database):
        """Test status vocabulary mapping from UI terms to DB terms."""
        mock_database.list_tasks_filtered.return_value = []
        
        # Test UI status mapping
        await list_tasks_tool.apply(status="TODO")
        mock_database.list_tasks_filtered.assert_called_with(project_id=None, epic_id=None, status="pending", limit=None)
        
        await list_tasks_tool.apply(status="IN_PROGRESS")
        mock_database.list_tasks_filtered.assert_called_with(project_id=None, epic_id=None, status="in_progress", limit=None)
        
        await list_tasks_tool.apply(status="REVIEW")
        mock_database.list_tasks_filtered.assert_called_with(project_id=None, epic_id=None, status="review", limit=None)
        
        await list_tasks_tool.apply(status="DONE")
        mock_database.list_tasks_filtered.assert_called_with(project_id=None, epic_id=None, status="completed", limit=None)
    
    @pytest.mark.asyncio
    async def test_list_tasks_invalid_status(self, list_tasks_tool):
        """Test error handling for invalid status."""
        result = await list_tasks_tool.apply(status="INVALID_STATUS")
        
        response = json.loads(result)
        assert "success" in response
        assert response["success"] == False
        assert "Invalid status 'INVALID_STATUS'" in response["message"]
    
    @pytest.mark.asyncio
    async def test_list_tasks_invalid_parameters(self, list_tasks_tool):
        """Test error handling for invalid parameters."""
        # Test invalid project_id
        result = await list_tasks_tool.apply(project_id=0)
        response = json.loads(result)
        assert "success" in response
        assert response["success"] == False
        assert "Project ID must be a positive integer" in response["message"]
        
        # Test invalid epic_id
        result = await list_tasks_tool.apply(epic_id=-1)
        response = json.loads(result)
        assert "success" in response
        assert response["success"] == False
        assert "Epic ID must be a positive integer" in response["message"]
        
        # Test invalid limit
        result = await list_tasks_tool.apply(limit=0)
        response = json.loads(result)
        assert "success" in response
        assert response["success"] == False
        assert "Limit must be a positive integer" in response["message"]


class TestListToolsIntegration:
    """Integration tests for list tools with AVAILABLE_TOOLS registry."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock TaskDatabase for testing."""
        return MagicMock(spec=TaskDatabase)
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock ConnectionManager for testing."""
        manager = MagicMock(spec=ConnectionManager)
        manager.broadcast = AsyncMock()
        return manager
    
    def test_list_tools_registered(self):
        """Test that new list tools are properly registered."""
        assert "list_projects" in AVAILABLE_TOOLS
        assert "list_epics" in AVAILABLE_TOOLS 
        assert "list_tasks" in AVAILABLE_TOOLS
    
    def test_create_list_tool_instances(self, mock_database, mock_websocket_manager):
        """Test creating list tool instances via factory."""
        list_projects = create_tool_instance("list_projects", mock_database, mock_websocket_manager)
        list_epics = create_tool_instance("list_epics", mock_database, mock_websocket_manager)
        list_tasks = create_tool_instance("list_tasks", mock_database, mock_websocket_manager)
        
        from task_manager.tools import ListProjectsTool, ListEpicsTool, ListTasksTool
        assert isinstance(list_projects, ListProjectsTool)
        assert isinstance(list_epics, ListEpicsTool)
        assert isinstance(list_tasks, ListTasksTool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
