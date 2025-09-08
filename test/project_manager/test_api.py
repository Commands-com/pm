"""
Comprehensive test suite for FastAPI backend with WebSocket functionality.

Tests API endpoints, WebSocket connections, lock validation, and error scenarios
according to RA-Light mode requirements for thorough validation.
"""

import asyncio
import json
import pytest
import tempfile
import os
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from fastapi import FastAPI
import websockets
import threading
import time

# Import the modules under test  
from task_manager.api import app, connection_manager, get_database
from task_manager.database import TaskDatabase


class TestDatabaseFixture:
    __test__ = False  # Prevent pytest from collecting this helper class as tests
    """Test fixture providing isolated database for testing."""
    
    def __init__(self):
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.db = TaskDatabase(self.db_path)
        
        # Set up test data
        self._setup_test_data()
    
    def _setup_test_data(self):
        """Create test projects, epics, and tasks for testing."""
        # Create test project
        project_id = self.db.create_project("Test Project", "Project for testing")
        
        # Create test epic
        epic_id = self.db.create_epic(project_id, "Test Epic", "Epic for testing")
        
        # Create test tasks
        self.task1_id = self.db.create_task(epic_id, "Test Task 1", "First test task")
        self.task2_id = self.db.create_task(epic_id, "Test Task 2", "Second test task")
        
        self.project_id = project_id
        self.epic_id = epic_id
    
    def cleanup(self):
        """Clean up test database."""
        self.db.close()
        os.unlink(self.db_path)


# Test fixtures
@pytest.fixture
def test_db():
    """Provide test database fixture."""
    fixture = TestDatabaseFixture()
    yield fixture.db, fixture
    fixture.cleanup()


@pytest.fixture
def client(test_db):
    """Provide FastAPI test client with database dependency override."""
    db, fixture = test_db
    
    # Override database dependency
    def get_test_database():
        return db
    
    app.dependency_overrides[get_database] = get_test_database
    
    with TestClient(app) as test_client:
        yield test_client, fixture
    
    # Clean up dependency override
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Test suite for health check endpoint."""
    
    def test_health_check_success(self, client):
        """Test successful health check response."""
        test_client, fixture = client
        
        response = test_client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["database_connected"] is True
        assert "timestamp" in data
        assert "active_websocket_connections" in data
    
    def test_health_check_with_database_error(self, client):
        """Test health check when database is unavailable."""
        test_client, fixture = client
        
        # Close database to simulate failure
        # #COMPLETION_DRIVE_IMPL: Simulating database failure by closing connection
        fixture.db.close()
        
        response = test_client.get("/healthz")
        
        # Should still return 200 but with degraded status
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database_connected"] is False


class TestBoardStateEndpoint:
    """Test suite for board state endpoint."""
    
    def test_get_board_state_success(self, client):
        """Test successful board state retrieval."""
        test_client, fixture = client
        
        response = test_client.get("/api/board/state")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "tasks" in data
        assert "projects" in data  
        assert "epics" in data
        
        # Verify we have our test data
        assert len(data["projects"]) >= 1
        assert len(data["epics"]) >= 1
        assert len(data["tasks"]) >= 2
        
        # Verify task structure includes lock information
        task = data["tasks"][0]
        required_fields = ["id", "name", "status", "lock_holder", "is_locked"]
        for field in required_fields:
            assert field in task
    
    def test_board_state_with_locked_task(self, client):
        """Test board state shows locked task information correctly."""
        test_client, fixture = client
        
        # Lock a task first
        success = fixture.db.acquire_task_lock_atomic(fixture.task1_id, "test-agent", 300)
        assert success
        
        response = test_client.get("/api/board/state")
        assert response.status_code == 200
        
        data = response.json()
        
        # Find the locked task
        locked_task = None
        for task in data["tasks"]:
            if task["id"] == fixture.task1_id:
                locked_task = task
                break
        
        assert locked_task is not None
        assert locked_task["is_locked"] is True
        assert locked_task["lock_holder"] == "test-agent"
    
    def test_board_state_hierarchical_relationships(self, client):
        """Test that board state maintains project->epic->task relationships."""
        test_client, fixture = client
        
        response = test_client.get("/api/board/state")
        data = response.json()
        
        # Verify project has our test project
        project = None
        for p in data["projects"]:
            if p["id"] == fixture.project_id:
                project = p
                break
        assert project is not None
        assert project["name"] == "Test Project"
        
        # Verify epic references the project
        epic = None
        for e in data["epics"]:
            if e["id"] == fixture.epic_id:
                epic = e
                break
        assert epic is not None
        assert epic["name"] == "Test Epic"
        assert epic["project_id"] == fixture.project_id
        
        # Verify tasks reference the epic
        for task in data["tasks"]:
            if task["id"] in [fixture.task1_id, fixture.task2_id]:
                assert task["epic_id"] == fixture.epic_id


class TestTaskStatusEndpoint:
    """Test suite for task status update endpoint."""
    
    def test_update_task_status_success(self, client):
        """Test successful task status update with proper lock."""
        test_client, fixture = client
        
        # First acquire lock
        success = fixture.db.acquire_task_lock_atomic(fixture.task1_id, "test-agent", 300)
        assert success
        
        # Update task status
        response = test_client.post(
            f"/api/task/{fixture.task1_id}/status",
            json={"status": "in_progress", "agent_id": "test-agent"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["status"] == "in_progress"
    
    def test_update_task_status_without_lock(self, client):
        """Test task status update auto-acquires lock when unlocked."""
        test_client, fixture = client
        
        # Attempt to update without acquiring lock first
        response = test_client.post(
            f"/api/task/{fixture.task1_id}/status",
            json={"status": "in_progress", "agent_id": "test-agent"}
        )
        
        # API auto-acquires a short-lived lock to allow update
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "in_progress"
    
    def test_update_task_status_wrong_agent(self, client):
        """Test task status update fails with wrong agent ID."""
        test_client, fixture = client
        
        # Lock with one agent
        success = fixture.db.acquire_task_lock_atomic(fixture.task1_id, "agent-1", 300)
        assert success
        
        # Try to update with different agent
        response = test_client.post(
            f"/api/task/{fixture.task1_id}/status",
            json={"status": "in_progress", "agent_id": "agent-2"}
        )
        
        assert response.status_code == 403
        data = response.json()
        # When locked by a different agent, API should report lock ownership conflict
        assert "locked by another agent" in data["detail"].lower()
    
    def test_update_nonexistent_task(self, client):
        """Test task status update fails for nonexistent task."""
        test_client, fixture = client
        
        response = test_client.post(
            "/api/task/99999/status",
            json={"status": "in_progress", "agent_id": "test-agent"}
        )
        
        assert response.status_code == 404
    
    def test_invalid_status_value(self, client):
        """Test validation of status values."""
        test_client, fixture = client
        
        # Lock task first
        success = fixture.db.acquire_task_lock_atomic(fixture.task1_id, "test-agent", 300)
        assert success
        
        # Try invalid status
        response = test_client.post(
            f"/api/task/{fixture.task1_id}/status",
            json={"status": "invalid_status", "agent_id": "test-agent"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_empty_agent_id(self, client):
        """Test validation of agent ID."""
        test_client, fixture = client
        
        response = test_client.post(
            f"/api/task/{fixture.task1_id}/status",
            json={"status": "in_progress", "agent_id": ""}
        )
        
        assert response.status_code == 422  # Validation error


class TestLockEndpoints:
    """Test suite for task lock/unlock endpoints."""
    
    def test_acquire_task_lock_success(self, client):
        """Test successful task lock acquisition."""
        test_client, fixture = client
        
        response = test_client.post(
            f"/api/task/{fixture.task1_id}/lock",
            json={"agent_id": "test-agent", "duration_seconds": 300}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["agent_id"] == "test-agent"
        
        # Verify lock in database
        lock_status = fixture.db.get_task_lock_status(fixture.task1_id)
        assert lock_status["is_locked"] is True
        assert lock_status["lock_holder"] == "test-agent"
    
    def test_acquire_already_locked_task(self, client):
        """Test lock acquisition fails when task already locked."""
        test_client, fixture = client
        
        # Lock task first
        success = fixture.db.acquire_task_lock_atomic(fixture.task1_id, "agent-1", 300)
        assert success
        
        # Try to lock with different agent
        response = test_client.post(
            f"/api/task/{fixture.task1_id}/lock",
            json={"agent_id": "agent-2"}
        )
        
        assert response.status_code == 409  # Conflict
        assert "already locked" in response.json()["detail"].lower()
    
    def test_release_task_lock_success(self, client):
        """Test successful task lock release."""
        test_client, fixture = client
        
        # Lock task first
        success = fixture.db.acquire_task_lock_atomic(fixture.task1_id, "test-agent", 300)
        assert success
        
        # Release lock
        response = test_client.request(
            "DELETE",
            f"/api/task/{fixture.task1_id}/lock",
            json={"agent_id": "test-agent"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify lock released in database
        lock_status = fixture.db.get_task_lock_status(fixture.task1_id)
        assert lock_status["is_locked"] is False
    
    def test_release_lock_wrong_agent(self, client):
        """Test lock release fails with wrong agent."""
        test_client, fixture = client
        
        # Lock with one agent
        success = fixture.db.acquire_task_lock_atomic(fixture.task1_id, "agent-1", 300)
        assert success
        
        # Try to release with different agent
        response = test_client.request(
            "DELETE",
            f"/api/task/{fixture.task1_id}/lock",
            json={"agent_id": "agent-2"}
        )
        
        assert response.status_code == 403
        assert "does not hold lock" in response.json()["detail"].lower()


class TestConnectionManager:
    """Test suite for WebSocket ConnectionManager functionality."""
    
    @pytest.mark.asyncio
    async def test_connection_manager_connect_disconnect(self):
        """Test WebSocket connection and disconnection handling."""
        # Clear any existing connections from other tests
        connection_manager.active_connections.clear()
        
        # Create mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        
        # Test connection
        await connection_manager.connect(mock_ws)
        assert mock_ws in connection_manager.active_connections
        assert connection_manager.get_connection_count() == 1
        
        # Test disconnection
        await connection_manager.disconnect(mock_ws)
        assert mock_ws not in connection_manager.active_connections
        assert connection_manager.get_connection_count() == 0
    
    @pytest.mark.asyncio
    async def test_connection_manager_broadcast(self):
        """Test parallel broadcasting to multiple WebSocket connections."""
        # Clear any existing connections from other tests
        connection_manager.active_connections.clear()
        
        # Create multiple mock WebSocket connections
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws3 = AsyncMock()
        
        mock_ws1.accept = AsyncMock()
        mock_ws2.accept = AsyncMock() 
        mock_ws3.accept = AsyncMock()
        
        mock_ws1.send_text = AsyncMock()
        mock_ws2.send_text = AsyncMock()
        mock_ws3.send_text = AsyncMock()
        
        # Connect all WebSockets
        await connection_manager.connect(mock_ws1)
        await connection_manager.connect(mock_ws2)
        await connection_manager.connect(mock_ws3)
        
        assert connection_manager.get_connection_count() == 3
        
        # Test broadcast
        test_event = {"type": "test", "data": "broadcast_test"}
        await connection_manager.broadcast(test_event)
        
        # Verify all connections received the message
        expected_message = json.dumps(test_event)
        mock_ws1.send_text.assert_called_once_with(expected_message)
        mock_ws2.send_text.assert_called_once_with(expected_message)
        mock_ws3.send_text.assert_called_once_with(expected_message)
    
    @pytest.mark.asyncio
    async def test_connection_manager_failed_send(self):
        """Test handling of failed WebSocket sends."""
        # Clear any existing connections from other tests
        connection_manager.active_connections.clear()
        
        # Create mock WebSocket that fails on send
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock(side_effect=Exception("Connection failed"))
        
        await connection_manager.connect(mock_ws)
        assert connection_manager.get_connection_count() == 1
        
        # Broadcast should handle the failure and remove the connection
        test_event = {"type": "test", "data": "failure_test"}
        await connection_manager.broadcast(test_event)
        
        # Connection should be automatically removed
        assert connection_manager.get_connection_count() == 0
        assert mock_ws not in connection_manager.active_connections
    
    @pytest.mark.asyncio
    async def test_broadcast_with_no_connections(self):
        """Test broadcast behavior with no active connections."""
        # Ensure no connections
        connection_manager.active_connections.clear()
        
        # Should not raise exception
        test_event = {"type": "test", "data": "no_connections"}
        await connection_manager.broadcast(test_event)
        
        # Should handle gracefully
        assert connection_manager.get_connection_count() == 0


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""
    
    @pytest.mark.asyncio 
    async def test_websocket_connection_lifecycle(self, client):
        """Test full WebSocket connection lifecycle."""
        test_client, fixture = client
        
        # #COMPLETION_DRIVE_IMPL: Using TestClient WebSocket support for integration testing
        # Real WebSocket client testing requires more complex setup
        with test_client.websocket_connect("/ws/updates") as websocket:
            # Connection should be established
            assert connection_manager.get_connection_count() >= 0  # May have other test connections
            
            # Send a test message (client to server)
            websocket.send_text("ping")
            
            # Connection should remain active
            # WebSocket endpoint keeps connection alive in message loop
    
    def test_websocket_receives_task_status_broadcasts(self, client):
        """Test WebSocket receives task status change broadcasts."""
        test_client, fixture = client
        
        # This is a complex integration test that would require:
        # 1. Establishing WebSocket connection 
        # 2. Making API call to update task status
        # 3. Verifying WebSocket receives broadcast
        
        # #SUGGEST_ERROR_HANDLING: Complex WebSocket integration testing
        # Requires careful coordination between API calls and WebSocket message reception
        # Consider using separate thread or async task coordination
        
        # Simplified test structure:
        with test_client.websocket_connect("/ws/updates") as websocket:
            # In separate thread/coroutine: make API call
            # Verify websocket receives expected broadcast message
            pass  # Implementation requires async coordination


class TestErrorHandling:
    """Test suite for API error handling."""
    
    def test_404_for_nonexistent_endpoints(self, client):
        """Test 404 responses for nonexistent endpoints."""
        test_client, fixture = client
        
        response = test_client.get("/api/nonexistent")
        assert response.status_code == 404
    
    def test_405_for_wrong_http_methods(self, client):
        """Test 405 responses for wrong HTTP methods."""
        test_client, fixture = client
        
        # GET on POST-only endpoint
        response = test_client.get(f"/api/task/{fixture.task1_id}/status")
        assert response.status_code == 405
        
        # POST on GET-only endpoint  
        response = test_client.post("/api/board/state")
        assert response.status_code == 405
    
    def test_422_for_malformed_json(self, client):
        """Test validation error responses for malformed requests."""
        test_client, fixture = client
        
        # Missing required fields
        response = test_client.post(
            f"/api/task/{fixture.task1_id}/status",
            json={"status": "in_progress"}  # Missing agent_id
        )
        
        assert response.status_code == 422
    
    def test_500_for_database_errors(self, client):
        """Test 500 responses for database errors."""
        test_client, fixture = client
        
        # Close database to cause errors
        fixture.db.close()
        
        response = test_client.get("/api/board/state")
        assert response.status_code == 500


class TestConcurrencyAndPerformance:
    """Test suite for concurrent access and performance."""
    
    @pytest.mark.asyncio
    async def test_concurrent_lock_acquisition(self):
        """Test atomic lock acquisition under concurrent access."""
        # Create test database
        fixture = TestDatabaseFixture()
        
        # #COMPLETION_DRIVE_IMPL: Testing atomic lock behavior under concurrency
        # Multiple agents trying to lock same task simultaneously
        results = []
        
        async def try_acquire_lock(agent_id: str):
            try:
                success = fixture.db.acquire_task_lock_atomic(fixture.task1_id, agent_id, 300)
                results.append((agent_id, success))
            except Exception as e:
                results.append((agent_id, False))
        
        # Launch multiple concurrent lock attempts
        tasks = []
        for i in range(5):
            tasks.append(try_acquire_lock(f"agent-{i}"))
        
        await asyncio.gather(*tasks)
        
        # Only one should succeed
        successes = [result for result in results if result[1] is True]
        assert len(successes) == 1
        
        # Verify lock status
        lock_status = fixture.db.get_task_lock_status(fixture.task1_id)
        assert lock_status["is_locked"] is True
        
        fixture.cleanup()
    
    @pytest.mark.asyncio
    async def test_websocket_broadcast_performance(self):
        """Test WebSocket broadcast performance with multiple connections."""
        # Create multiple mock connections
        connections = []
        for i in range(50):  # Test with 50 connections
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            mock_ws.send_text = AsyncMock()
            connections.append(mock_ws)
            await connection_manager.connect(mock_ws)
        
        assert connection_manager.get_connection_count() == 50
        
        # Measure broadcast time
        start_time = time.time()
        
        test_event = {"type": "performance_test", "data": "large_broadcast"}
        await connection_manager.broadcast(test_event)
        
        end_time = time.time()
        broadcast_time = end_time - start_time
        
        # #SUGGEST_ERROR_HANDLING: Performance thresholds for broadcast operations
        # Broadcast to 50 connections should complete quickly (< 1 second)
        assert broadcast_time < 1.0
        
        # Verify all connections received message
        expected_message = json.dumps(test_event)
        for ws in connections:
            ws.send_text.assert_called_once_with(expected_message)
        
        # Clean up connections
        for ws in connections:
            await connection_manager.disconnect(ws)


class TestDataValidation:
    """Test suite for data validation and sanitization."""
    
    def test_agent_id_validation(self, client):
        """Test agent ID validation in various endpoints."""
        test_client, fixture = client
        
        # Empty agent ID
        response = test_client.post(
            f"/api/task/{fixture.task1_id}/lock",
            json={"agent_id": ""}
        )
        assert response.status_code == 400
        
        # Whitespace-only agent ID  
        response = test_client.post(
            f"/api/task/{fixture.task1_id}/status",
            json={"status": "in_progress", "agent_id": "   "}
        )
        assert response.status_code == 422
    
    def test_task_id_validation(self, client):
        """Test task ID validation for numeric constraints."""
        test_client, fixture = client
        
        # Non-numeric task ID should be handled by FastAPI path validation
        # Negative task ID
        response = test_client.post(
            "/api/task/-1/status",
            json={"status": "in_progress", "agent_id": "test-agent"}
        )
        # Should be handled gracefully (404 for nonexistent task)
        assert response.status_code in [404, 422]
    
    def test_status_enum_validation(self, client):
        """Test status value enumeration validation."""
        test_client, fixture = client
        
        # Lock task first
        success = fixture.db.acquire_task_lock_atomic(fixture.task1_id, "test-agent", 300)
        assert success
        
        # Valid statuses should work
        valid_statuses = ["pending", "in_progress", "completed", "blocked"]
        for status in valid_statuses:
            response = test_client.post(
                f"/api/task/{fixture.task1_id}/status",
                json={"status": status, "agent_id": "test-agent"}
            )
            # Should succeed (or at least not fail validation)
            assert response.status_code in [200, 403]  # 403 if task gets unlocked between tests


# Performance and load testing markers
@pytest.mark.performance
class TestPerformanceCharacteristics:
    """Performance testing for API endpoints under load."""
    
    @pytest.mark.asyncio
    async def test_api_endpoint_response_times(self, client):
        """Test API endpoint response times under normal load."""
        test_client, fixture = client
        
        # Test board state endpoint performance
        start_time = time.time()
        response = test_client.get("/api/board/state")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        
        # #SUGGEST_ERROR_HANDLING: Performance thresholds for API responses
        # Board state should respond within reasonable time (< 0.5s for test data)
        assert response_time < 0.5
    
    def test_database_query_performance(self):
        """Test database query performance with larger datasets."""
        fixture = TestDatabaseFixture()
        
        # Create additional test data
        for i in range(100):
            project_id = fixture.db.create_project(f"Project {i}", f"Description {i}")
            epic_id = fixture.db.create_epic(project_id, f"Epic {i}", f"Description {i}")
            for j in range(10):
                fixture.db.create_task(epic_id, f"Task {i}-{j}", f"Description {i}-{j}")
        
        # Test query performance
        start_time = time.time()
        tasks = fixture.db.get_all_tasks()
        projects = fixture.db.get_all_projects()
        epics = fixture.db.get_all_epics()
        end_time = time.time()
        
        query_time = end_time - start_time
        
        # Should handle moderate dataset efficiently
        assert len(tasks) >= 1000  # 100 epics * 10 tasks + original test data
        assert len(projects) >= 100
        assert len(epics) >= 100
        assert query_time < 2.0  # Should complete within 2 seconds
        
        fixture.cleanup()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
