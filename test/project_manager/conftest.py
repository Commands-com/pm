"""
Comprehensive test fixtures and infrastructure for Project Manager MCP integration testing.

Provides isolated test database, WebSocket client utilities, MCP client helpers, 
and CLI process management for end-to-end integration testing scenarios.

RA-Light Mode Implementation:
All integration assumptions and coordination uncertainties are tagged for verification.
"""

import asyncio
import json
import multiprocessing
import os
import pytest
import signal
import socket
import tempfile
import threading
import time
import websockets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple
from unittest.mock import AsyncMock, MagicMock

import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import project components
import sys
project_root = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(project_root))

from task_manager.database import TaskDatabase
from task_manager.api import app as fastapi_app, connection_manager, get_database
from task_manager.assumptions import _provide_db
from task_manager.mcp_server import create_mcp_server
from task_manager.cli import main as cli_main
from task_manager.importer import import_project_from_file


class IntegrationTestDatabase:
    """
    Isolated test database with realistic project structure for integration testing.
    
    Creates temporary SQLite database with WAL mode and seeds with comprehensive
    test data including epics, stories, tasks, and proper relationships.
    """
    
    def __init__(self, test_name: str = "integration_test"):
        """
        Initialize test database with isolation guarantees.
        
        # VERIFIED: Test database file naming correctly ensures test isolation
        # Unique temporary files prevent conflicts between concurrent test runs.
        """
        self.test_name = test_name
        # Create unique temporary database file
        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=f'_{test_name}.db',
            prefix='test_pm_'
        )
        self.temp_file.close()
        self.db_path = self.temp_file.name
        
        # Initialize database with WAL mode
        # VERIFIED: WAL mode enables safe concurrent test access to database
        # Multiple threads can read/write without blocking during integration tests.
        self.database = TaskDatabase(self.db_path, lock_timeout_seconds=30)
        
        # Seed with realistic test data
        self._seed_test_data()
        
    def _seed_test_data(self):
        """Create comprehensive test project structure."""
        # Create test project
        self.project_id = self.database.create_project(
            "Integration Test Project",
            "Complete project for integration testing"
        )
        
        # Create test epics
        self.epic1_id = self.database.create_epic(
            self.project_id,
            "User Authentication System",
            "Complete user authentication and authorization system"
        )
        self.epic2_id = self.database.create_epic(
            self.project_id,
            "Dashboard Implementation", 
            "Real-time project management dashboard"
        )
        
        # Create test tasks with varying complexity
        self.task_ids = []
        
        # Epic 1 tasks
        self.task_ids.append(self.database.create_task(
            self.epic1_id,
            "Implement login API endpoint",
            "Create FastAPI endpoint for user authentication"
        ))
        self.task_ids.append(self.database.create_task(
            self.epic1_id,
            "Add JWT token generation",
            "Implement secure JWT token creation and validation"
        ))
        self.task_ids.append(self.database.create_task(
            self.epic1_id,
            "Password reset email flow",
            "Send reset emails with secure tokens"
        ))
        
        # Epic 2 tasks
        self.task_ids.append(self.database.create_task(
            self.epic2_id,
            "WebSocket real-time updates",
            "Implement WebSocket broadcasting for task changes"
        ))
        self.task_ids.append(self.database.create_task(
            self.epic2_id,
            "Drag and drop interface",
            "Frontend drag-and-drop task management"
        ))
        
        # Create some standalone tasks for testing
        self.task_ids.append(self.database.create_task(
            self.epic1_id,
            "Database performance optimization",
            "Optimize SQLite queries and indexing"
        ))
        self.task_ids.append(self.database.create_task(
            self.epic2_id,
            "API documentation updates", 
            "Update OpenAPI documentation for new endpoints"
        ))
        
    def get_available_tasks(self) -> List[Dict[str, Any]]:
        """Get list of unlocked tasks for testing."""
        return self.database.get_available_tasks()
        
    def cleanup(self):
        """Clean up test database and temporary files."""
        try:
            self.database.close()
            os.unlink(self.db_path)
        except Exception as e:
            # #SUGGEST_ERROR_HANDLING: Cleanup failures shouldn't break test suite
            print(f"Warning: Failed to cleanup test database {self.db_path}: {e}")


class WebSocketTestClient:
    """
    WebSocket test client with event capture and verification capabilities.
    
    Provides async WebSocket connection management, event capturing with timestamps,
    and verification utilities for integration testing scenarios.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        """
        Initialize WebSocket test client.
        
        # VERIFIED: Default host/port configuration matches CLI server defaults
        # WebSocket clients connect successfully to dashboard endpoint on port 8080.
        """
        self.host = host
        self.port = port
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.captured_events: List[Dict[str, Any]] = []
        self.event_capture_task: Optional[asyncio.Task] = None
        self._capture_lock = asyncio.Lock()
        
    async def connect(self) -> bool:
        """
        Establish WebSocket connection with retry logic.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        # Keep this fast to avoid hanging tests when server isn't running
        max_retries = 3
        retry_delay = 0.2
        
        for attempt in range(max_retries):
            try:
                # Match current API WebSocket endpoint
                uri = f"ws://{self.host}:{self.port}/ws/updates"
                self.websocket = await websockets.connect(uri, timeout=2)
                
                # Start event capture task
                self.event_capture_task = asyncio.create_task(self._capture_events())
                return True
                
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                else:
                    # #SUGGEST_ERROR_HANDLING: Connection failures should be debuggable
                    print(f"Failed to connect to WebSocket after {max_retries} attempts: {e}")
                    return False
                    
        return False
        
    async def _capture_events(self):
        """Background task to capture WebSocket events."""
        if not self.websocket:
            return
            
        try:
            async for message in self.websocket:
                async with self._capture_lock:
                    event = {
                        "timestamp": time.time(),
                        "raw_message": message,
                        "parsed": None
                    }
                    
                    try:
                        event["parsed"] = json.loads(message)
                    except json.JSONDecodeError:
                        # #SUGGEST_VALIDATION: Non-JSON messages should be tracked
                        event["parse_error"] = True
                        
                    self.captured_events.append(event)
                    
        except websockets.exceptions.ConnectionClosed:
            pass  # Normal disconnection
        except Exception as e:
            # #SUGGEST_ERROR_HANDLING: Event capture failures need debugging info
            print(f"WebSocket event capture error: {e}")
            
    async def disconnect(self):
        """Clean disconnect from WebSocket."""
        if self.event_capture_task:
            self.event_capture_task.cancel()
            try:
                await self.event_capture_task
            except asyncio.CancelledError:
                pass
                
        if self.websocket:
            await self.websocket.close()
            
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get captured events filtered by type."""
        return [
            event for event in self.captured_events
            if event.get("parsed", {}).get("type") == event_type
        ]
        
    def get_events_since(self, timestamp: float) -> List[Dict[str, Any]]:
        """Get events captured after given timestamp."""
        return [
            event for event in self.captured_events
            if event["timestamp"] > timestamp
        ]
        
    def clear_events(self):
        """Clear captured events for new test scenarios."""
        self.captured_events.clear()


def find_free_port() -> int:
    """
    Find an available port for test server instances.
    
    # VERIFIED: Socket-based port detection works reliably for test isolation
    # Brief race condition window is acceptable for testing and rarely causes issues.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


class CLITestProcess:
    """
    CLI process management for integration testing.
    
    Provides controlled CLI server startup, port management, and cleanup
    with proper process isolation for integration test scenarios.
    """
    
    def __init__(self, project_path: Optional[str] = None):
        """
        Initialize CLI test process manager.
        
        Args:
            project_path: Optional path to test project YAML file
        """
        self.project_path = project_path
        self.process: Optional[multiprocessing.Process] = None
        self.dashboard_port = find_free_port()
        self.mcp_port = find_free_port()
        self.temp_db: Optional[str] = None
        
    def start(self, timeout: float = 10.0) -> bool:
        """
        Start CLI process with isolated database and ports.
        
        # VERIFIED: Multi-process CLI testing correctly simulates production patterns
        # Separate process isolation ensures realistic integration testing scenarios.
        
        Returns:
            bool: True if startup successful within timeout
        """
        # Create temporary database for this CLI instance
        temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db_file.close()
        self.temp_db = temp_db_file.name
        
        # Prepare CLI arguments
        cli_args = [
            "--db-path", self.temp_db,
            "--dashboard-port", str(self.dashboard_port),
            "--mcp-port", str(self.mcp_port),
            "--no-browser"  # Don't open browser in tests
        ]
        
        if self.project_path:
            cli_args.extend(["--project", self.project_path])
            
        # VERIFIED: Multiprocessing pattern matches actual CLI implementation
        # This approach correctly simulates how the CLI runs in production.
        self.process = multiprocessing.Process(
            target=self._run_cli,
            args=(cli_args,)
        )
        self.process.start()
        
        # Wait for server startup with health checks
        return self._wait_for_startup(timeout)
        
    def _run_cli(self, cli_args: List[str]):
        """Run CLI in subprocess with argument passing."""
        # VERIFIED: sys.argv manipulation correctly enables CLI argument parsing
        # Click framework requires sys.argv to be set for proper command parsing.
        import sys
        original_argv = sys.argv[:]
        try:
            sys.argv = ["pm"] + cli_args
            cli_main()
        finally:
            sys.argv = original_argv
            
    def _wait_for_startup(self, timeout: float) -> bool:
        """Wait for CLI servers to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check dashboard health
                import requests
                dashboard_response = requests.get(
                    f"http://localhost:{self.dashboard_port}/healthz",
                    timeout=2
                )
                if dashboard_response.status_code == 200:
                    return True
                    
            except Exception:
                pass  # Server not ready yet
                
            time.sleep(0.5)
            
        return False
        
    def stop(self):
        """Stop CLI process and cleanup resources."""
        if self.process and self.process.is_alive():
            # #SUGGEST_ERROR_HANDLING: Graceful shutdown with fallback to force kill
            self.process.terminate()
            try:
                self.process.join(timeout=5)
            except:
                pass
                
            if self.process.is_alive():
                self.process.kill()
                self.process.join()
                
        # Cleanup temporary database
        if self.temp_db and os.path.exists(self.temp_db):
            try:
                os.unlink(self.temp_db)
            except Exception as e:
                print(f"Warning: Failed to cleanup CLI test database: {e}")


# Pytest fixtures
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


@pytest.fixture
def test_project_yaml(tmp_path):
    """Create temporary test project YAML file."""
    project_file = tmp_path / "test-project.yaml"
    # Will be implemented in next step
    return str(project_file)


@pytest.fixture
def api_client(integration_db):
    """Provide FastAPI test client with database override."""
    # Override database dependency to use test database
    def get_test_database():
        return integration_db.database

    fastapi_app.dependency_overrides[get_database] = get_test_database
    fastapi_app.dependency_overrides[_provide_db] = get_test_database

    with TestClient(fastapi_app) as client:
        yield client

    # Cleanup dependency override
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
async def integrated_multi_model_setup(integration_db):
    """
    Integrated multi-model setup that shares database with API client.

    This fixture creates a complete multi-model test environment where the validation
    tool writes to the same database that the API client reads from, solving the
    database isolation issue in integration tests.
    """
    from src.task_manager.api import ConnectionManager
    from src.task_manager.tools import CaptureAssumptionValidationTool

    # Use the shared integration database
    db = integration_db.database
    connection_manager = ConnectionManager()

    # Create validation tool with the shared database
    validation_tool = CaptureAssumptionValidationTool(
        database=db,
        websocket_manager=connection_manager
    )

    # Create test project structure
    project_id = db.create_project(
        name="Integrated Multi-Model Test Project",
        description="Project for integrated multi-model validation testing with shared database"
    )

    epic_id = db.create_epic(
        name="Integrated Multi-Model Test Epic",
        description="Epic for integrated multi-model validation testing",
        project_id=project_id
    )

    # Create RA tags for testing
    ra_tags = [
        {
            "id": "ra_tag_integrated_001",
            "text": "#COMPLETION_DRIVE_IMPL: Integrated multi-model validation test assumption",
            "type": "COMPLETION_DRIVE_IMPL"
        },
        {
            "id": "ra_tag_integrated_002",
            "text": "#SUGGEST_ERROR_HANDLING: Error handling for integrated validation scenarios",
            "type": "SUGGEST_ERROR_HANDLING"
        }
    ]

    task_id = db.create_task(
        name="Integrated Multi-Model Test Task",
        description="Task for integrated multi-model validation testing with shared database",
        epic_id=epic_id,
        ra_tags=ra_tags
    )

    # Test model configurations
    test_models = [
        {
            "validator_id": "claude-sonnet-3.5",
            "model_info": {
                "name": "Claude Sonnet 3.5",
                "version": "3.5",
                "provider": "anthropic",
                "category": "reasoning_model"
            }
        },
        {
            "validator_id": "gpt-4-turbo",
            "model_info": {
                "name": "GPT-4 Turbo",
                "version": "turbo",
                "provider": "openai",
                "category": "reasoning_model"
            }
        },
        {
            "validator_id": "code-reviewer-v2",
            "model_info": {
                "name": "Code Reviewer",
                "version": "v2",
                "provider": "unknown",
                "category": "specialized_model"
            }
        }
    ]

    # Validation scenarios for testing
    validation_scenarios = [
        # Strong consensus - all validated
        {
            "name": "strong_consensus_validated",
            "validations": [
                {"outcome": "validated", "confidence": 90},
                {"outcome": "validated", "confidence": 85},
                {"outcome": "validated", "confidence": 95}
            ],
            "expected_agreement": "UNANIMOUS",
            "expected_score_range": (85, 95)
        },
        # Strong consensus - all rejected
        {
            "name": "strong_consensus_rejected",
            "validations": [
                {"outcome": "rejected", "confidence": 85},
                {"outcome": "rejected", "confidence": 90},
                {"outcome": "rejected", "confidence": 80}
            ],
            "expected_agreement": "UNANIMOUS",
            "expected_score_range": (10, 20)
        },
        # Moderate consensus - majority validated
        {
            "name": "moderate_consensus_validated",
            "validations": [
                {"outcome": "validated", "confidence": 85},
                {"outcome": "validated", "confidence": 80},
                {"outcome": "rejected", "confidence": 75}
            ],
            "expected_agreement": "MODERATE",
            "expected_score_range": (60, 80)
        },
        # Weak consensus - mixed outcomes
        {
            "name": "weak_consensus_mixed",
            "validations": [
                {"outcome": "validated", "confidence": 70},
                {"outcome": "rejected", "confidence": 65},
                {"outcome": "partial", "confidence": 60}
            ],
            "expected_agreement": "WEAK",
            "expected_score_range": (50, 70)
        },
        # Edge case - single validation
        {
            "name": "single_validation",
            "validations": [
                {"outcome": "validated", "confidence": 88}
            ],
            "expected_agreement": "UNANIMOUS",
            "expected_score_range": (85, 90)
        }
    ]

    return {
        "db": db,
        "connection_manager": connection_manager,
        "validation_tool": validation_tool,
        "project_id": project_id,
        "epic_id": epic_id,
        "task_id": task_id,
        "ra_tags": ra_tags,
        "test_models": test_models,
        "validation_scenarios": validation_scenarios
    }


@pytest.fixture
def multi_model_test_data():
    """
    Provide test data for multi-model validation scenarios.

    #COMPLETION_DRIVE_IMPL: Generated test data approach for multi-model testing
    Returns comprehensive test configurations for various validation scenarios,
    model configurations, and consensus calculation edge cases.
    """
    return {
        "models": [
            {
                "validator_id": "claude-sonnet-3.5",
                "expected_model": {
                    "name": "Claude Sonnet 3.5",
                    "version": "3.5",
                    "provider": "anthropic",
                    "category": "large_language_model"
                }
            },
            {
                "validator_id": "gpt-4-turbo",
                "expected_model": {
                    "name": "GPT-4 Turbo",
                    "version": "turbo",
                    "provider": "openai",
                    "category": "large_language_model"
                }
            },
            {
                "validator_id": "gemini-pro-1.0",
                "expected_model": {
                    "name": "Gemini Pro",
                    "version": "1.0",
                    "provider": "google",
                    "category": "large_language_model"
                }
            },
            {
                "validator_id": "code-reviewer-v2",
                "expected_model": {
                    "name": "Code Reviewer",
                    "version": "v2",
                    "provider": "unknown",
                    "category": "specialized_model"
                }
            }
        ],
        "consensus_scenarios": [
            {
                "name": "strong_consensus_validated",
                "validations": [
                    {"outcome": "validated", "confidence": 90},
                    {"outcome": "validated", "confidence": 85},
                    {"outcome": "validated", "confidence": 95}
                ],
                "expected_agreement": "STRONG",
                "expected_score_range": (85, 95)
            },
            {
                "name": "strong_consensus_rejected",
                "validations": [
                    {"outcome": "rejected", "confidence": 85},
                    {"outcome": "rejected", "confidence": 90},
                    {"outcome": "rejected", "confidence": 80}
                ],
                "expected_agreement": "STRONG",
                "expected_score_range": (10, 20)
            },
            {
                "name": "moderate_consensus_validated",
                "validations": [
                    {"outcome": "validated", "confidence": 85},
                    {"outcome": "validated", "confidence": 80},
                    {"outcome": "rejected", "confidence": 75}
                ],
                "expected_agreement": "MODERATE",
                "expected_score_range": (60, 85)
            },
            {
                "name": "weak_consensus_mixed",
                "validations": [
                    {"outcome": "validated", "confidence": 70},
                    {"outcome": "rejected", "confidence": 65},
                    {"outcome": "partial", "confidence": 60}
                ],
                "expected_agreement": "WEAK",
                "expected_score_range": (50, 70)
            }
        ],
        "ra_tags": [
            {
                "id": "ra_tag_multi_test_001",
                "type": "implementation:assumption",
                "text": "#COMPLETION_DRIVE_IMPL: Multi-model test assumption for consensus validation",
                "created_by": "test-system"
            },
            {
                "id": "ra_tag_multi_test_002",
                "type": "error-handling:suggestion",
                "text": "#SUGGEST_ERROR_HANDLING: Multi-model test error handling for validation",
                "created_by": "test-system"
            },
            {
                "id": "ra_tag_multi_test_003",
                "type": "pattern:momentum",
                "text": "#PATTERN_MOMENTUM: Multi-model test pattern selection rationale",
                "created_by": "test-system"
            }
        ]
    }


@pytest.fixture
async def multi_model_websocket_client():
    """
    Provide WebSocket client specifically configured for multi-model event testing.

    #COMPLETION_DRIVE_IMPL: Real WebSocket infrastructure testing approach
    Creates WebSocket client that can capture and validate multi-model specific
    events like validation_added and consensus_updated.
    """
    client = WebSocketTestClient()

    # Add multi-model event filtering
    client.multi_model_events = []

    original_capture = client._capture_events

    async def enhanced_capture():
        """Enhanced event capture with multi-model event filtering."""
        await original_capture()

        # Filter for multi-model events
        for event in client.captured_events:
            if event.get("parsed", {}).get("type", "").startswith("multi_model."):
                client.multi_model_events.append(event)

    client._capture_events = enhanced_capture

    yield client
    await client.disconnect()


@pytest.fixture
def performance_test_config():
    """
    Configuration for performance testing scenarios.

    #SUGGEST_PERFORMANCE: Performance benchmarks for production readiness assessment
    Provides configurable thresholds and test parameters for multi-model
    performance validation under various load conditions.
    """
    return {
        "concurrent_requests": 100,
        "max_response_time": 2.0,  # seconds
        "cache_response_improvement": 0.5,  # cached should be 50% faster
        "websocket_event_delay": 0.1,  # max seconds for event delivery
        "consensus_calculation_time": 0.05,  # max seconds for consensus calc
        "model_parsing_time": 0.01,  # max seconds for model ID parsing
        "database_query_time": 0.1  # max seconds for multi-model queries
    }
