"""
Integration test fixtures and configuration.

Provides fixtures needed for comprehensive integration testing scenarios.
"""

import pytest
import sys
import importlib.util
from pathlib import Path

# Import project components  
project_root = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(project_root))

# Import from the specific conftest module to avoid circular imports
project_manager_test_path = Path(__file__).parent.parent / "project_manager"
conftest_path = project_manager_test_path / "conftest.py"
spec = importlib.util.spec_from_file_location("project_manager_conftest", conftest_path)
project_manager_conftest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project_manager_conftest)

IntegrationTestDatabase = project_manager_conftest.IntegrationTestDatabase
WebSocketTestClient = project_manager_conftest.WebSocketTestClient  
CLITestProcess = project_manager_conftest.CLITestProcess


@pytest.fixture
def integration_db():
    """Provide isolated integration test database."""
    test_db = IntegrationTestDatabase()
    yield test_db
    test_db.cleanup()


@pytest.fixture
async def websocket_client():
    """Provide WebSocket test client with automatic cleanup."""
    client = WebSocketTestClient()
    yield client
    await client.disconnect()


@pytest.fixture  
def cli_process():
    """Provide CLI process manager for integration tests."""
    process_manager = CLITestProcess()
    yield process_manager
    process_manager.stop()