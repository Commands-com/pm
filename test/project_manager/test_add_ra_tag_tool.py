"""
Tests for AddRATagTool MCP Tool

Clean, comprehensive tests for the add_ra_tag MCP tool matching the actual implementation.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.task_manager.tools_lib import AddRATagTool
from src.task_manager.database import TaskDatabase


class TestAddRATagTool:
    """Test AddRATagTool functionality."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock database for testing."""
        db = MagicMock(spec=TaskDatabase)
        return db
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager for testing."""
        return AsyncMock()
    
    @pytest.fixture
    def add_ra_tag_tool(self, mock_database, mock_websocket_manager):
        """Create AddRATagTool instance for testing."""
        return AddRATagTool(mock_database, mock_websocket_manager)
    
    @pytest.mark.asyncio
    async def test_missing_task_id(self, add_ra_tag_tool):
        """Test with missing task_id."""
        result = await add_ra_tag_tool.apply(
            task_id="",
            ra_tag_text="#COMPLETION_DRIVE_IMPL: Test"
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is False
        assert "task_id is required" in result_data['message']
    
    @pytest.mark.asyncio
    async def test_missing_ra_tag_text(self, add_ra_tag_tool):
        """Test with missing ra_tag_text."""
        result = await add_ra_tag_tool.apply(
            task_id="1",
            ra_tag_text=""
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is False
        assert "ra_tag_text is required" in result_data['message']
    
    @pytest.mark.asyncio
    async def test_invalid_task_id(self, add_ra_tag_tool):
        """Test with invalid task_id format."""
        result = await add_ra_tag_tool.apply(
            task_id="invalid",
            ra_tag_text="#COMPLETION_DRIVE_IMPL: Test"
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is False
        assert "Invalid task_id" in result_data['message']
    
    @pytest.mark.asyncio
    async def test_invalid_ra_tag_format_no_hash(self, add_ra_tag_tool):
        """Test with RA tag not starting with #."""
        result = await add_ra_tag_tool.apply(
            task_id="1",
            ra_tag_text="COMPLETION_DRIVE_IMPL: Test"
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is False
        assert "must start with '#'" in result_data['message']
    
    @pytest.mark.asyncio
    async def test_invalid_ra_tag_format_no_colon(self, add_ra_tag_tool):
        """Test with RA tag missing colon."""
        result = await add_ra_tag_tool.apply(
            task_id="1",
            ra_tag_text="#COMPLETION_DRIVE_IMPL"
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is False
        assert "must contain ':'" in result_data['message']
    
    @pytest.mark.asyncio
    async def test_task_not_found(self, add_ra_tag_tool, mock_database):
        """Test with non-existent task."""
        mock_database.get_task_by_id.return_value = None
        
        result = await add_ra_tag_tool.apply(
            task_id="999",
            ra_tag_text="#COMPLETION_DRIVE_IMPL: Test"
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is False
        assert "Task 999 not found" in result_data['message']
    
    @pytest.mark.asyncio
    async def test_invalid_line_number(self, add_ra_tag_tool, mock_database):
        """Test with invalid line number."""
        mock_database.get_task_by_id.return_value = {'id': 1, 'name': 'Test Task'}
        
        result = await add_ra_tag_tool.apply(
            task_id="1",
            ra_tag_text="#COMPLETION_DRIVE_IMPL: Test",
            line_number=-1
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is False
        assert "must be a positive integer" in result_data['message']
    
    @pytest.mark.asyncio
    @patch('src.task_manager.context_utils.create_enriched_context')
    @patch('src.task_manager.ra_tag_utils.normalize_ra_tag')
    async def test_successful_creation(self, mock_normalize, mock_create_context, add_ra_tag_tool, mock_database, mock_websocket_manager):
        """Test successful RA tag creation."""
        # Setup mocks
        mock_database.get_task_by_id.return_value = {
            'id': 1, 
            'name': 'Test Task',
            'ra_tags': '[]'
        }
        mock_database.update_task_ra_fields.return_value = True
        mock_create_context.return_value = {
            'git_branch': 'main',
            'git_commit': 'abc123'
        }
        mock_normalize.return_value = ('implementation:assumption', '#COMPLETION_DRIVE_IMPL: Test functionality')
        
        result = await add_ra_tag_tool.apply(
            task_id="1",
            ra_tag_text="#COMPLETION_DRIVE_IMPL: Test functionality",
            agent_id="test-agent"
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is True
        assert result_data['task_id'] == 1
        assert result_data['ra_tag_type'] == 'implementation:assumption'
        assert result_data['ra_tag_text'] == '#COMPLETION_DRIVE_IMPL: Test functionality'
        assert result_data['created_by'] == 'test-agent'
        assert 'ra_tag_id' in result_data
        assert result_data['ra_tag_id'].startswith('ra_tag_')
        
        # Verify database call
        mock_database.update_task_ra_fields.assert_called_once()
        
        # Verify websocket broadcast
        mock_websocket_manager.broadcast.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.task_manager.context_utils.create_enriched_context')
    @patch('src.task_manager.ra_tag_utils.normalize_ra_tag')
    async def test_with_existing_tags(self, mock_normalize, mock_create_context, add_ra_tag_tool, mock_database):
        """Test adding tag to task with existing tags."""
        existing_tags = [
            {
                'id': 'ra_tag_existing',
                'type': 'error-handling:suggestion',
                'text': '#SUGGEST_ERROR_HANDLING: Existing tag',
                'created_at': '2025-09-11T10:00:00.000000+00:00'
            }
        ]
        
        mock_database.get_task_by_id.return_value = {
            'id': 1,
            'name': 'Test Task',
            'ra_tags': json.dumps(existing_tags)
        }
        mock_database.update_task_ra_fields.return_value = True
        mock_create_context.return_value = {}
        mock_normalize.return_value = ('implementation:assumption', '#COMPLETION_DRIVE_IMPL: New tag')
        
        result = await add_ra_tag_tool.apply(
            task_id="1",
            ra_tag_text="#COMPLETION_DRIVE_IMPL: New tag"
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is True
        
        # Verify database was called with updated tags
        call_args = mock_database.update_task_ra_fields.call_args[1]
        updated_tags = call_args['ra_tags']
        assert len(updated_tags) == 2
        assert any(tag['text'] == '#COMPLETION_DRIVE_IMPL: New tag' for tag in updated_tags)
    
    @pytest.mark.asyncio
    @patch('src.task_manager.context_utils.create_enriched_context')
    async def test_database_save_failure(self, mock_create_context, add_ra_tag_tool, mock_database):
        """Test handling database save failure."""
        mock_database.get_task_by_id.return_value = {'id': 1, 'name': 'Test Task', 'ra_tags': '[]'}
        mock_database.update_task_ra_fields.return_value = False  # Simulate save failure
        mock_create_context.return_value = {}
        
        result = await add_ra_tag_tool.apply(
            task_id="1",
            ra_tag_text="#COMPLETION_DRIVE_IMPL: Test"
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is False
        assert "Failed to save RA tag to database" in result_data['message']
    
    @pytest.mark.asyncio
    @patch('src.task_manager.context_utils.create_enriched_context')
    async def test_with_malformed_existing_tags(self, mock_create_context, add_ra_tag_tool, mock_database):
        """Test handling malformed existing tags JSON."""
        mock_database.get_task_by_id.return_value = {
            'id': 1,
            'name': 'Test Task',
            'ra_tags': 'invalid json'
        }
        mock_database.update_task_ra_fields.return_value = True
        mock_create_context.return_value = {}
        
        result = await add_ra_tag_tool.apply(
            task_id="1",
            ra_tag_text="#COMPLETION_DRIVE_IMPL: Test"
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is True
        
        # Should handle malformed JSON gracefully
        call_args = mock_database.update_task_ra_fields.call_args[1]
        updated_tags = call_args['ra_tags']
        assert len(updated_tags) == 1
    
    @pytest.mark.asyncio
    async def test_exception_handling(self, add_ra_tag_tool, mock_database):
        """Test exception handling."""
        mock_database.get_task_by_id.side_effect = Exception("Database error")
        
        result = await add_ra_tag_tool.apply(
            task_id="1",
            ra_tag_text="#COMPLETION_DRIVE_IMPL: Test"
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is False
        assert "Failed to create RA tag" in result_data['message']
    
    @pytest.mark.asyncio
    @patch('src.task_manager.context_utils.create_enriched_context')
    async def test_without_websocket_manager(self, mock_create_context, mock_database):
        """Test creation without WebSocket manager."""
        mock_database.get_task_by_id.return_value = {'id': 1, 'name': 'Test Task', 'ra_tags': '[]'}
        mock_database.update_task_ra_fields.return_value = True
        mock_create_context.return_value = {}
        
        # Create tool without WebSocket manager
        tool = AddRATagTool(mock_database, None)
        
        result = await tool.apply(
            task_id="1",
            ra_tag_text="#COMPLETION_DRIVE_IMPL: Test"
        )
        
        result_data = json.loads(result)
        assert result_data['success'] is True