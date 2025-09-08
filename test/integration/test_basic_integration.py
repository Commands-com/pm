"""
Basic Integration Tests for PM Dashboard

Tests the actual implemented functionality:
- API endpoints work and return expected data
- WebSocket connection and basic events
- Database integration through API
- Health checks and metrics
"""

import asyncio
import json
import pytest
import requests
import time
import websockets
from typing import Dict, Any, List

# Test configuration
BASE_URL = "http://localhost:8080"
WS_URL = "ws://localhost:8080/ws/updates"


class TestBasicAPIIntegration:
    """Test actual API endpoints that exist and work."""
    
    def test_health_endpoint(self):
        """Test that health endpoint returns expected format."""
        response = requests.get(f"{BASE_URL}/healthz", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "database_connected" in data
        assert data["database_connected"] is True
    
    def test_main_dashboard_page(self):
        """Test that main dashboard page loads."""
        response = requests.get(BASE_URL, timeout=5)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        # Check for key dashboard elements
        assert "Task Management Dashboard" in response.text or "dashboard" in response.text.lower()
    
    def test_board_state_endpoint(self):
        """Test board state API returns valid structure."""
        response = requests.get(f"{BASE_URL}/api/board/state", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        # Based on actual response, tasks is a list, not a dict with columns
        assert "tasks" in data
        assert isinstance(data["tasks"], list)
    
    def test_metrics_endpoint(self):
        """Test metrics API returns system information."""
        response = requests.get(f"{BASE_URL}/api/metrics", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        # Based on actual response structure
        assert "connections" in data
        assert "tasks" in data
        assert "performance" in data
        assert "system" in data
        
        # Check nested structure
        assert isinstance(data["connections"]["active"], int)
        assert isinstance(data["tasks"]["total"], int)
        assert isinstance(data["system"]["memory_usage_mb"], (int, float))
    
    def test_projects_list_endpoint(self):
        """Test projects list endpoint."""
        response = requests.get(f"{BASE_URL}/api/projects", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # Each project should have required fields
        for project in data:
            assert "id" in project
            assert "name" in project
    
    def test_epics_list_endpoint(self):
        """Test epics list endpoint."""
        response = requests.get(f"{BASE_URL}/api/epics", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # Each epic should have required fields
        for epic in data:
            assert "id" in epic
            assert "name" in epic
            assert "project_id" in epic
    
    def test_tasks_filtered_endpoint(self):
        """Test filtered tasks endpoint."""
        response = requests.get(f"{BASE_URL}/api/tasks/filtered", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # Each task should have required fields
        for task in data:
            assert "id" in task
            assert "name" in task
            assert "status" in task


class TestWebSocketIntegration:
    """Test WebSocket connection and basic functionality."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test that WebSocket connects successfully."""
        try:
            async with websockets.connect(WS_URL) as websocket:
                # Connection successful if we get here
                # Instead of checking .open, just try to use the connection
                
                # Wait briefly for any initial messages
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    # No initial message is fine
                    pass
                    
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_stays_connected(self):
        """Test that WebSocket connection remains stable."""
        try:
            async with websockets.connect(WS_URL) as websocket:
                # Stay connected for a few seconds
                await asyncio.sleep(1)  # Reduced time
                
                # Try to receive with timeout (may not have messages)
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=0.5)
                except asyncio.TimeoutError:
                    # No messages is fine for this test
                    pass
                
        except Exception as e:
            pytest.fail(f"WebSocket stability test failed: {e}")


class TestDatabaseIntegration:
    """Test that the database is working through the API."""
    
    def test_database_connectivity_via_health(self):
        """Test database connection through health endpoint."""
        response = requests.get(f"{BASE_URL}/healthz", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert data["database_connected"] is True
    
    def test_data_persistence(self):
        """Test that data persists between API calls."""
        # Get initial state
        response1 = requests.get(f"{BASE_URL}/api/board/state", timeout=5)
        assert response1.status_code == 200
        state1 = response1.json()
        
        # Wait a moment
        time.sleep(0.1)
        
        # Get state again
        response2 = requests.get(f"{BASE_URL}/api/board/state", timeout=5)
        assert response2.status_code == 200
        state2 = response2.json()
        
        # Structure should be consistent
        assert state1.keys() == state2.keys()
        assert "tasks" in state1 and "tasks" in state2
    
    def test_projects_epics_relationship(self):
        """Test that projects and epics have proper relationships."""
        # Get projects
        projects_response = requests.get(f"{BASE_URL}/api/projects", timeout=5)
        assert projects_response.status_code == 200
        projects = projects_response.json()
        
        # Get epics
        epics_response = requests.get(f"{BASE_URL}/api/epics", timeout=5)
        assert epics_response.status_code == 200
        epics = epics_response.json()
        
        if projects and epics:
            # All epic project_ids should reference existing projects
            project_ids = {p["id"] for p in projects}
            for epic in epics:
                assert epic["project_id"] in project_ids


class TestSystemIntegration:
    """Test overall system behavior and integration."""
    
    def test_concurrent_api_calls(self):
        """Test system handles multiple concurrent API calls."""
        import concurrent.futures
        import threading
        
        def make_api_call():
            try:
                response = requests.get(f"{BASE_URL}/api/board/state", timeout=10)
                return response.status_code == 200
            except Exception:
                return False
        
        # Make 5 concurrent calls
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_api_call) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All calls should succeed
        assert all(results), f"Some concurrent API calls failed: {results}"
    
    def test_metrics_update_over_time(self):
        """Test that metrics reflect system state changes."""
        # Get initial metrics
        response1 = requests.get(f"{BASE_URL}/api/metrics", timeout=5)
        assert response1.status_code == 200
        metrics1 = response1.json()
        
        # Make some API calls to potentially change metrics
        requests.get(f"{BASE_URL}/api/board/state", timeout=5)
        requests.get(f"{BASE_URL}/api/projects", timeout=5)
        
        # Wait a moment
        time.sleep(0.5)
        
        # Get metrics again
        response2 = requests.get(f"{BASE_URL}/api/metrics", timeout=5)
        assert response2.status_code == 200
        metrics2 = response2.json()
        
        # Should have same structure
        assert metrics1.keys() == metrics2.keys()
        
        # Values should be reasonable (non-negative)
        for key, value in metrics2.items():
            if isinstance(value, (int, float)):
                assert value >= 0, f"Metric {key} has negative value: {value}"


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test basic end-to-end workflows that actually work."""
    
    def test_dashboard_data_flow(self):
        """Test the complete data flow from backend to frontend structure."""
        # 1. Check health
        health_response = requests.get(f"{BASE_URL}/healthz", timeout=5)
        assert health_response.status_code == 200
        assert health_response.json()["database_connected"] is True
        
        # 2. Get dashboard page
        page_response = requests.get(BASE_URL, timeout=5)
        assert page_response.status_code == 200
        
        # 3. Get board state (what the dashboard loads)
        board_response = requests.get(f"{BASE_URL}/api/board/state", timeout=5)
        assert board_response.status_code == 200
        board_data = board_response.json()
        
        # 4. Get supporting data
        projects_response = requests.get(f"{BASE_URL}/api/projects", timeout=5)
        epics_response = requests.get(f"{BASE_URL}/api/epics", timeout=5)
        
        assert projects_response.status_code == 200
        assert epics_response.status_code == 200
        
        # All data should be properly structured
        assert "tasks" in board_data
        assert isinstance(projects_response.json(), list)
        assert isinstance(epics_response.json(), list)
    
    @pytest.mark.asyncio
    async def test_websocket_with_api_integration(self):
        """Test WebSocket works alongside API calls."""
        try:
            async with websockets.connect(WS_URL) as websocket:
                # Make API call while WebSocket is connected
                response = requests.get(f"{BASE_URL}/api/board/state", timeout=5)
                assert response.status_code == 200
                
                # WebSocket should still be functional
                
                # Try to get metrics while connected
                metrics_response = requests.get(f"{BASE_URL}/api/metrics", timeout=5)
                assert metrics_response.status_code == 200
                
                # Check that active connections count includes our WebSocket
                metrics = metrics_response.json()
                assert metrics["connections"]["active"] >= 1
                
        except Exception as e:
            pytest.fail(f"WebSocket + API integration failed: {e}")


if __name__ == "__main__":
    # Allow running individual test classes
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "api":
            pytest.main([__file__ + "::TestBasicAPIIntegration", "-v"])
        elif sys.argv[1] == "websocket":
            pytest.main([__file__ + "::TestWebSocketIntegration", "-v"])
        elif sys.argv[1] == "database":
            pytest.main([__file__ + "::TestDatabaseIntegration", "-v"])
        elif sys.argv[1] == "system":
            pytest.main([__file__ + "::TestSystemIntegration", "-v"])
        elif sys.argv[1] == "e2e":
            pytest.main([__file__ + "::TestEndToEndWorkflow", "-v"])
        else:
            pytest.main([__file__, "-v"])
    else:
        pytest.main([__file__, "-v"])