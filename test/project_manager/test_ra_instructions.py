"""
Tests for RA Instructions System Integration

Comprehensive test suite for Response Awareness methodology system instructions,
FastMCP integration, prompt snapshot functionality, and task log tracking.

Standard Mode Implementation:
- Unit tests for RA instructions formatting and validation
- Integration tests for FastMCP instructions parameter
- Tests for prompt snapshot capture and storage
- Task log prompt audit trail verification
- Manual MCP client validation scenarios
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, List

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(project_root))

from task_manager.ra_instructions import (
    RAInstructionsManager, 
    get_ra_instructions, 
    validate_task_ra_compliance,
    get_mode_for_complexity,
    ra_instructions_manager
)
from task_manager.mcp_server import ProjectManagerMCPServer, create_mcp_server
from task_manager.database import TaskDatabase
from task_manager.api import ConnectionManager
from task_manager.tools import CreateTaskTool


class TestRAInstructionsManager:
    """Test suite for RAInstructionsManager class functionality."""
    
    def test_initialization(self):
        """Test RAInstructionsManager initialization and metadata."""
        manager = RAInstructionsManager()
        
        assert manager.version == "3.0.0"
        assert isinstance(manager.last_updated, str)
        
        # Verify timestamp format
        try:
            datetime.fromisoformat(manager.last_updated.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Invalid timestamp format in last_updated")

    def test_get_full_instructions(self):
        """Test comprehensive RA methodology instructions generation."""
        manager = RAInstructionsManager()
        instructions = manager.get_full_instructions()
        
        # Standard Mode: Verify all required instruction components
        assert "CRITICAL: You MUST use Response Awareness" in instructions
        assert "PROJECT MANAGER MCP SYSTEM" in instructions
        assert "SYSTEM HIERARCHY: Project → Epic → Tasks" in instructions
        
        # Verify complexity assessment guidance
        assert "1. ASSESS COMPLEXITY (1-10 scale)" in instructions
        assert "1-3: Simple Mode" in instructions
        assert "4-6: Standard Mode" in instructions
        assert "7-8: RA-Light Mode" in instructions
        assert "9-10: RA-Full Mode" in instructions
        
        # Verify MCP tool guidance
        assert "create_task" in instructions
        assert "update_task" in instructions
        assert "acquire_task_lock" in instructions
        
        # Verify RA tag taxonomy
        assert "#COMPLETION_DRIVE_IMPL" in instructions
        assert "#COMPLETION_DRIVE_INTEGRATION" in instructions
        assert "#SUGGEST_ERROR_HANDLING" in instructions
        assert "#PATTERN_CONFLICT" in instructions
        
        # Verify version information
        assert manager.version in instructions
        assert manager.last_updated in instructions

    def test_get_concise_instructions(self):
        """Test concise RA methodology instructions for performance contexts."""
        manager = RAInstructionsManager()
        concise = manager.get_concise_instructions()
        
        # Should contain key elements but be shorter
        assert len(concise) < len(manager.get_full_instructions())
        assert "RA METHODOLOGY" in concise
        assert "COMPLEXITY MODES" in concise
        assert "MCP TOOLS" in concise
        assert "RA TAGS" in concise
        assert manager.version in concise

    def test_get_tag_taxonomy(self):
        """Test RA tag taxonomy structure and completeness."""
        manager = RAInstructionsManager()
        taxonomy = manager.get_tag_taxonomy()
        
        # Verify expected categories
        expected_categories = [
            "implementation_tags",
            "pattern_detection_tags", 
            "conflict_tags",
            "suggestion_tags"
        ]
        
        for category in expected_categories:
            assert category in taxonomy
            assert isinstance(taxonomy[category], dict)
        
        # Verify specific tags exist
        impl_tags = taxonomy["implementation_tags"]
        assert "COMPLETION_DRIVE_IMPL" in impl_tags
        assert "COMPLETION_DRIVE_INTEGRATION" in impl_tags
        assert "CONTEXT_DEGRADED" in impl_tags
        
        suggest_tags = taxonomy["suggestion_tags"]
        assert "SUGGEST_ERROR_HANDLING" in suggest_tags
        assert "SUGGEST_VALIDATION" in suggest_tags

    def test_validate_ra_compliance(self):
        """Test RA methodology compliance validation."""
        manager = RAInstructionsManager()
        
        # Test valid RA-light task
        valid_task = {
            "ra_mode": "ra-light",
            "ra_score": 7,
            "ra_tags": ["#COMPLETION_DRIVE_IMPL: OAuth library selection"],
            "name": "Test task"
        }
        
        result = manager.validate_ra_compliance(valid_task)
        assert result["compliant"] is True
        assert len(result["errors"]) == 0
        
        # Test invalid score
        invalid_score_task = {
            "ra_mode": "standard",
            "ra_score": 15,  # Invalid: > 10
            "ra_tags": []
        }
        
        result = manager.validate_ra_compliance(invalid_score_task)
        assert result["compliant"] is False
        assert any("Invalid RA score" in error for error in result["errors"])
        
        # Test missing tags for RA mode
        missing_tags_task = {
            "ra_mode": "ra-light",
            "ra_score": 8,
            "ra_tags": []  # Should have tags for ra-light
        }
        
        result = manager.validate_ra_compliance(missing_tags_task)
        assert len(result["warnings"]) > 0
        assert any("should include assumption tags" in warning for warning in result["warnings"])

    def test_get_mode_guidelines(self):
        """Test mode guidelines generation for different complexity scores."""
        manager = RAInstructionsManager()
        
        # Test simple mode (score 1-3)
        simple_guidelines = manager.get_mode_guidelines(2)
        assert simple_guidelines["mode"] == "simple"
        assert simple_guidelines["tagging_required"] is False
        assert simple_guidelines["testing_level"] == "Basic unit tests"
        
        # Test standard mode (score 4-6)
        standard_guidelines = manager.get_mode_guidelines(5)
        assert standard_guidelines["mode"] == "standard"
        assert standard_guidelines["tagging_required"] is False
        assert "integration tests" in standard_guidelines["testing_level"]
        
        # Test RA-light mode (score 7-8)
        ra_light_guidelines = manager.get_mode_guidelines(7)
        assert ra_light_guidelines["mode"] == "ra-light"
        assert ra_light_guidelines["tagging_required"] is True
        assert ra_light_guidelines["coordination_required"] is True
        
        # Test RA-full mode (score 9-10)
        ra_full_guidelines = manager.get_mode_guidelines(10)
        assert ra_full_guidelines["mode"] == "ra-full"
        assert ra_full_guidelines["tagging_required"] is True
        assert "Multi-agent orchestration" in ra_full_guidelines["approach"]

    def test_capture_prompt_snapshot(self):
        """Test prompt snapshot capture functionality."""
        manager = RAInstructionsManager()
        snapshot = manager.capture_prompt_snapshot("test_context")
        
        # Parse JSON snapshot
        snapshot_data = json.loads(snapshot)
        
        assert "timestamp" in snapshot_data
        assert snapshot_data["context"] == "test_context"
        assert snapshot_data["ra_version"] == manager.version
        assert snapshot_data["instructions_type"] == "full_ra_methodology"
        
        # Verify timestamp format
        try:
            datetime.fromisoformat(snapshot_data["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Invalid timestamp in prompt snapshot")

    def test_get_instructions_metadata(self):
        """Test instructions metadata retrieval."""
        manager = RAInstructionsManager()
        metadata = manager.get_instructions_metadata()
        
        assert metadata["version"] == manager.version
        assert "features" in metadata
        assert "supported_modes" in metadata
        assert "tag_categories" in metadata
        
        # Verify supported modes
        expected_modes = ["simple", "standard", "ra-light", "ra-full"]
        assert metadata["supported_modes"] == expected_modes
        
        # Verify feature list
        features = metadata["features"]
        assert "comprehensive_ra_workflow" in features
        assert "mcp_tool_integration" in features
        assert "complexity_assessment" in features


class TestRAInstructionsHelpers:
    """Test suite for RA instructions helper functions."""
    
    def test_get_ra_instructions_full(self):
        """Test full format instructions retrieval."""
        instructions = get_ra_instructions("full")
        
        assert isinstance(instructions, str)
        assert len(instructions) > 1000  # Should be comprehensive
        assert "Response Awareness" in instructions

    def test_get_ra_instructions_concise(self):
        """Test concise format instructions retrieval."""
        instructions = get_ra_instructions("concise")
        
        assert isinstance(instructions, str)
        assert len(instructions) < len(get_ra_instructions("full"))
        assert "RA METHODOLOGY" in instructions

    def test_get_ra_instructions_invalid_format(self):
        """Test invalid format handling."""
        with pytest.raises(ValueError) as exc_info:
            get_ra_instructions("invalid_format")
        
        assert "Unsupported format_type" in str(exc_info.value)

    def test_validate_task_ra_compliance(self):
        """Test task compliance validation helper."""
        task_data = {
            "ra_mode": "standard",
            "ra_score": 5,
            "ra_tags": []
        }
        
        result = validate_task_ra_compliance(task_data)
        assert isinstance(result, dict)
        assert "compliant" in result
        assert "warnings" in result
        assert "errors" in result

    def test_get_mode_for_complexity(self):
        """Test mode determination helper function."""
        assert get_mode_for_complexity(1) == "simple"
        assert get_mode_for_complexity(3) == "simple" 
        assert get_mode_for_complexity(4) == "standard"
        assert get_mode_for_complexity(6) == "standard"
        assert get_mode_for_complexity(7) == "ra-light"
        assert get_mode_for_complexity(8) == "ra-light"
        assert get_mode_for_complexity(9) == "ra-full"
        assert get_mode_for_complexity(10) == "ra-full"
        
        # Test invalid scores
        with pytest.raises(ValueError):
            get_mode_for_complexity(0)
        
        with pytest.raises(ValueError):
            get_mode_for_complexity(11)


class TestMCPServerRAIntegration:
    """Test suite for FastMCP server RA instructions integration."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock TaskDatabase for testing."""
        database = MagicMock(spec=TaskDatabase)
        return database
    
    @pytest.fixture  
    def mock_websocket_manager(self):
        """Mock ConnectionManager for testing."""
        manager = MagicMock(spec=ConnectionManager)
        manager.optimized_broadcast = AsyncMock()
        return manager

    def test_mcp_server_instructions_integration(self, mock_database, mock_websocket_manager):
        """Test that MCP server properly integrates RA instructions."""
        # Create MCP server
        server = ProjectManagerMCPServer(
            database=mock_database,
            websocket_manager=mock_websocket_manager,
            server_name="Test Server",
            server_version="1.0.0"
        )
        
        # Verify server description updated
        assert "Response Awareness (RA) methodology" in server._server_instructions
        assert "coordination capabilities" in server._server_instructions

    @patch('task_manager.mcp_server.get_ra_instructions')
    async def test_fastmcp_server_creation_with_instructions(
        self, 
        mock_get_instructions,
        mock_database, 
        mock_websocket_manager
    ):
        """Test that FastMCP server is created with RA instructions."""
        # Mock instructions
        test_instructions = "Test RA Instructions"
        mock_get_instructions.return_value = test_instructions
        
        server = ProjectManagerMCPServer(
            database=mock_database,
            websocket_manager=mock_websocket_manager
        )
        
        # Mock FastMCP creation but allow _create_server to run
        with patch('task_manager.mcp_server.FastMCP') as mock_fastmcp:
            mock_fastmcp.return_value = MagicMock()
            
            await server._create_server()
            
            # Verify instructions were retrieved
            mock_get_instructions.assert_called_once_with(format_type="full")
            
            # Verify FastMCP was created with instructions
            mock_fastmcp.assert_called_once()
            call_args = mock_fastmcp.call_args
            assert 'instructions' in call_args.kwargs
            assert call_args.kwargs['instructions'] == test_instructions

    def test_server_info_includes_ra_integration(self, mock_database, mock_websocket_manager):
        """Test that server info reflects RA integration."""
        server = ProjectManagerMCPServer(
            database=mock_database,
            websocket_manager=mock_websocket_manager
        )
        
        server_info = server.get_server_info()
        
        # Verify server information includes RA context
        assert "instructions" in server_info
        assert "Response Awareness" in server_info["instructions"]


class TestCreateTaskRAIntegration:
    """Test suite for CreateTaskTool RA integration."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock TaskDatabase for testing."""
        database = MagicMock(spec=TaskDatabase)
        database.create_task_with_ra_metadata = MagicMock(return_value=123)
        database.add_task_log_entry = MagicMock(return_value=1)
        database.upsert_project_with_status = MagicMock(return_value=(1, True))
        database.upsert_epic_with_status = MagicMock(return_value=(1, True))
        return database
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock ConnectionManager for testing."""
        manager = MagicMock(spec=ConnectionManager)
        manager.optimized_broadcast = AsyncMock()
        return manager

    async def test_prompt_snapshot_integration(self, mock_database, mock_websocket_manager):
        """Test that CreateTaskTool integrates with RA prompt snapshot capture."""
        tool = CreateTaskTool(mock_database, mock_websocket_manager)
        
        # Test task creation without explicit prompt snapshot
        result_json = await tool.apply(
            name="Test Task",
            epic_name="Test Epic", 
            project_name="Test Project",
            ra_mode="ra-light",
            ra_score=7
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        
        # Verify database methods were called
        assert mock_database.create_task_with_ra_metadata.called
        assert mock_database.add_task_log_entry.call_count == 2  # create + prompt entries

    async def test_prompt_log_entry_creation(self, mock_database, mock_websocket_manager):
        """Test that prompt-specific log entries are created."""
        tool = CreateTaskTool(mock_database, mock_websocket_manager)
        
        await tool.apply(
            name="Test Task",
            epic_name="Test Epic",
            project_name="Test Project", 
            ra_mode="standard"
        )
        
        # Verify add_task_log_entry was called twice
        assert mock_database.add_task_log_entry.call_count == 2
        
        # Check the log entry calls
        calls = mock_database.add_task_log_entry.call_args_list
        
        # First call should be for task creation
        assert calls[0][0][1] == 'create'  # kind parameter
        
        # Second call should be for prompt tracking
        assert calls[1][0][1] == 'prompt'  # kind parameter
        
        # Verify prompt log payload structure
        prompt_payload = calls[1][0][2]  # payload parameter
        assert 'prompt_snapshot' in prompt_payload
        assert 'ra_mode' in prompt_payload
        assert 'instructions_version' in prompt_payload

    @patch('task_manager.tools.ra_instructions_manager.capture_prompt_snapshot')
    async def test_prompt_snapshot_capture_called(
        self, 
        mock_capture,
        mock_database, 
        mock_websocket_manager
    ):
        """Test that prompt snapshot capture is called during task creation."""
        mock_capture.return_value = '{"test": "snapshot"}'
        
        tool = CreateTaskTool(mock_database, mock_websocket_manager)
        
        await tool.apply(
            name="Test Task",
            epic_name="Test Epic",
            project_name="Test Project"
        )
        
        # Verify prompt snapshot capture was called
        mock_capture.assert_called_once_with("task_creation")

    async def test_explicit_prompt_snapshot_preserved(
        self, 
        mock_database, 
        mock_websocket_manager
    ):
        """Test that explicitly provided prompt snapshots are preserved."""
        tool = CreateTaskTool(mock_database, mock_websocket_manager)
        
        explicit_snapshot = "Explicit prompt snapshot"
        
        await tool.apply(
            name="Test Task",
            epic_name="Test Epic",
            project_name="Test Project",
            prompt_snapshot=explicit_snapshot
        )
        
        # Verify the explicit snapshot was used in database call
        call_kwargs = mock_database.create_task_with_ra_metadata.call_args.kwargs
        assert call_kwargs['prompt_snapshot'] == explicit_snapshot


class TestRAInstructionsIntegrationScenarios:
    """Integration test scenarios for complete RA workflow."""
    
    def test_complexity_assessment_to_mode_mapping(self):
        """Test complete complexity assessment to RA mode workflow."""
        test_cases = [
            (1, "simple", False),
            (3, "simple", False), 
            (4, "standard", False),
            (6, "standard", False),
            (7, "ra-light", True),
            (8, "ra-light", True),
            (9, "ra-full", True),
            (10, "ra-full", True)
        ]
        
        for score, expected_mode, should_tag in test_cases:
            mode = get_mode_for_complexity(score)
            guidelines = ra_instructions_manager.get_mode_guidelines(score)
            
            assert mode == expected_mode
            assert guidelines["mode"] == expected_mode
            assert guidelines["tagging_required"] == should_tag

    def test_instructions_contain_all_mcp_tools(self):
        """Test that instructions reference all available MCP tools."""
        instructions = get_ra_instructions("full")
        
        # Standard Mode: Verify all MCP tools are documented
        expected_tools = [
            "create_task",
            "update_task",
            "get_task_details",
            "acquire_task_lock",
            "update_task_status", 
            "release_task_lock",
            "get_available_tasks",
            "list_projects",
            "list_epics",
            "list_tasks"
        ]
        
        for tool in expected_tools:
            assert tool in instructions, f"Tool {tool} missing from instructions"

    def test_ra_tag_format_validation(self):
        """Test RA tag format validation across different patterns."""
        manager = RAInstructionsManager()
        
        # Valid tags
        valid_tags = [
            "#COMPLETION_DRIVE_IMPL: OAuth library selection",
            "#SUGGEST_ERROR_HANDLING: token refresh scenarios",
            "#PATTERN_CONFLICT: multiple auth patterns valid",
            "#CONTEXT_DEGRADED: unclear requirements interpretation"
        ]
        
        task_with_valid_tags = {
            "ra_mode": "ra-light",
            "ra_score": 7,
            "ra_tags": valid_tags
        }
        
        result = manager.validate_ra_compliance(task_with_valid_tags)
        # Should not have warnings about tag format
        tag_warnings = [w for w in result["warnings"] if "doesn't follow standard RA format" in w]
        assert len(tag_warnings) == 0
        
        # Invalid tags (missing colon and description)
        invalid_tags = [
            "#COMPLETION_DRIVE_IMPL",  # Missing colon and description
            "SUGGEST_ERROR_HANDLING: desc",  # Missing hash
            "#INVALID_TAG: description"  # Not in taxonomy
        ]
        
        task_with_invalid_tags = {
            "ra_mode": "ra-light", 
            "ra_score": 7,
            "ra_tags": invalid_tags
        }
        
        result = manager.validate_ra_compliance(task_with_invalid_tags)
        # Should have warnings about tag format
        tag_warnings = [w for w in result["warnings"] if "doesn't follow standard RA format" in w]
        assert len(tag_warnings) > 0


# Standard Mode Implementation Notes:
# 1. Comprehensive test coverage for all RA instructions functionality
# 2. Integration tests verify FastMCP server instructions parameter
# 3. CreateTaskTool integration tested with mocking for isolation  
# 4. Prompt snapshot functionality validated with capture and storage
# 5. Task log audit trail verified with proper kind="prompt" entries
# 6. RA compliance validation tested across multiple scenarios
# 7. Mode determination logic validated for all complexity ranges
# 8. Tag format validation ensures proper RA methodology compliance
# 9. Mock objects provide isolation while testing integration points
# 10. Error scenarios and edge cases covered for robust validation
