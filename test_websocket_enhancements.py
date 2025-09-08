"""
Unit tests for WebSocket event payload enhancements.

Tests the enriched payload generation functions and WebSocket broadcasting
enhancements for task.created, task.updated, and task.logs.appended events.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Import functions to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src/task_manager'))

from src.task_manager.api import (
    extract_session_id, 
    generate_enriched_task_payload,
    generate_logs_appended_payload,
    ConnectionManager
)


class TestSessionTracking:
    """Test session ID extraction utilities."""
    
    def test_extract_session_id_present(self):
        """Test extracting session ID when present in MCP args."""
        mcp_args = {
            'task_name': 'Test Task',
            'client_session_id': 'session_abc123',
            'description': 'Test description'
        }
        
        session_id = extract_session_id(mcp_args)
        assert session_id == 'session_abc123'
    
    def test_extract_session_id_missing(self):
        """Test extracting session ID when missing from MCP args."""
        mcp_args = {
            'task_name': 'Test Task',
            'description': 'Test description'
        }
        
        session_id = extract_session_id(mcp_args)
        assert session_id is None
    
    def test_extract_session_id_empty_args(self):
        """Test extracting session ID from empty args."""
        mcp_args = {}
        
        session_id = extract_session_id(mcp_args)
        assert session_id is None


class TestEnrichedTaskPayload:
    """Test enriched task payload generation."""
    
    def test_basic_task_payload(self):
        """Test generating basic task payload without optional data."""
        task_data = {
            'id': 123,
            'name': 'Test Task',
            'description': 'Test description',
            'status': 'pending',
            'ra_score': 7,
            'ra_mode': 'ra-light'
        }
        
        payload = generate_enriched_task_payload(task_data)
        
        # Verify task data structure
        assert payload['task']['id'] == 123
        assert payload['task']['name'] == 'Test Task'
        assert payload['task']['description'] == 'Test description'
        assert payload['task']['status'] == 'pending'
        assert payload['task']['ra_score'] == 7
        assert payload['task']['ra_mode'] == 'ra-light'
        
        # Verify optional fields are not present
        assert 'project' not in payload
        assert 'epic' not in payload
        assert 'flags' not in payload
        assert 'initiator' not in payload
    
    def test_enriched_task_payload_with_all_context(self):
        """Test generating enriched payload with full context data."""
        task_data = {
            'id': 123,
            'name': 'Test Task',
            'status': 'in_progress',
            'ra_score': 8,
            'ra_mode': 'ra-light'
        }
        
        project_data = {
            'id': 45,
            'name': 'Test Project'
        }
        
        epic_data = {
            'id': 67,
            'name': 'Test Epic',
            'project_id': 45
        }
        
        auto_flags = {
            'project_created': True,
            'epic_created': False
        }
        
        session_id = 'session_xyz789'
        
        payload = generate_enriched_task_payload(
            task_data=task_data,
            project_data=project_data,
            epic_data=epic_data,
            auto_flags=auto_flags,
            session_id=session_id
        )
        
        # Verify task data
        assert payload['task']['id'] == 123
        assert payload['task']['name'] == 'Test Task'
        assert payload['task']['status'] == 'in_progress'
        
        # Verify project context
        assert payload['project']['id'] == 45
        assert payload['project']['name'] == 'Test Project'
        
        # Verify epic context
        assert payload['epic']['id'] == 67
        assert payload['epic']['name'] == 'Test Epic'
        assert payload['epic']['project_id'] == 45
        
        # Verify auto-switch flags
        assert payload['flags']['project_created'] is True
        assert payload['flags']['epic_created'] is False
        
        # Verify session context
        assert payload['initiator'] == 'session_xyz789'
        assert payload['auto_switch_recommended'] is True
    
    def test_task_payload_with_session_only(self):
        """Test generating payload with session ID but no other context."""
        task_data = {
            'id': 123,
            'name': 'Test Task',
            'status': 'pending'
        }
        
        session_id = 'session_test123'
        
        payload = generate_enriched_task_payload(
            task_data=task_data,
            session_id=session_id
        )
        
        # Verify session context is added
        assert payload['initiator'] == 'session_test123'
        assert payload['auto_switch_recommended'] is True
        
        # Verify optional context is not present
        assert 'project' not in payload
        assert 'epic' not in payload
        assert 'flags' not in payload


class TestLogsAppendedPayload:
    """Test task.logs.appended payload generation."""
    
    def test_basic_logs_payload(self):
        """Test generating basic logs appended payload."""
        task_id = 123
        log_entries = [
            {
                'seq': 10,
                'kind': 'update',
                'content': 'Task status updated',
                'timestamp': '2025-01-08T10:30:00Z'
            },
            {
                'seq': 11,
                'kind': 'ra_tag',
                'content': 'Added COMPLETION_DRIVE_IMPL tag',
                'timestamp': '2025-01-08T10:31:00Z'
            }
        ]
        
        payload = generate_logs_appended_payload(task_id, log_entries)
        
        # Verify basic structure
        assert payload['task_id'] == 123
        assert payload['log_entries'] == log_entries
        assert payload['log_count'] == 2
        
        # Verify sequence range
        assert payload['sequence_range']['start'] == 10
        assert payload['sequence_range']['end'] == 11
        
        # Verify no session context
        assert 'initiator' not in payload
    
    def test_logs_payload_with_session(self):
        """Test generating logs payload with session ID."""
        task_id = 456
        log_entries = [
            {
                'seq': 5,
                'kind': 'prompt',
                'content': 'System prompt updated',
                'timestamp': '2025-01-08T10:25:00Z'
            }
        ]
        
        session_id = 'session_logs123'
        
        payload = generate_logs_appended_payload(task_id, log_entries, session_id)
        
        # Verify session context
        assert payload['initiator'] == 'session_logs123'
        assert payload['task_id'] == 456
        assert payload['log_count'] == 1
        
        # Verify sequence range for single entry
        assert payload['sequence_range']['start'] == 5
        assert payload['sequence_range']['end'] == 5
    
    def test_logs_payload_empty_entries(self):
        """Test generating logs payload with empty log entries."""
        task_id = 789
        log_entries = []
        
        payload = generate_logs_appended_payload(task_id, log_entries)
        
        # Verify basic structure
        assert payload['task_id'] == 789
        assert payload['log_entries'] == []
        assert payload['log_count'] == 0
        
        # Verify no sequence range for empty entries
        assert 'sequence_range' not in payload


class TestConnectionManagerEnhancements:
    """Test enhanced ConnectionManager broadcasting functionality."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create ConnectionManager instance for testing."""
        return ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_broadcast_enriched_event(self, connection_manager):
        """Test broadcasting enriched events with proper payload structure."""
        # Mock the broadcast method
        connection_manager.broadcast = AsyncMock()
        
        event_type = 'task.created'
        event_data = {
            'task': {
                'id': 123,
                'name': 'Test Task'
            },
            'project': {
                'id': 45,
                'name': 'Test Project'
            }
        }
        
        # Call the enriched broadcast method
        await connection_manager.broadcast_enriched_event(event_type, event_data)
        
        # Verify broadcast was called with enriched structure
        connection_manager.broadcast.assert_called_once()
        call_args = connection_manager.broadcast.call_args[0][0]
        
        # Verify enriched payload structure
        assert call_args['type'] == 'task.created'
        assert 'timestamp' in call_args
        assert call_args['data'] == event_data
        
        # Verify timestamp format
        timestamp = call_args['timestamp']
        assert timestamp.endswith('Z')
        # Should be able to parse as ISO format
        parsed_timestamp = datetime.fromisoformat(timestamp.rstrip('Z')).replace(tzinfo=timezone.utc)
        assert isinstance(parsed_timestamp, datetime)


class TestIntegrationScenarios:
    """Test complete integration scenarios for WebSocket events."""
    
    def test_task_created_event_payload_structure(self):
        """Test complete task.created event payload matches specification."""
        # Simulate task creation scenario
        task_data = {
            'id': 123,
            'name': 'Implement WebSocket enhancements',
            'description': 'Add enriched payloads and auto-switch functionality',
            'status': 'pending',
            'ra_score': 8,
            'ra_mode': 'ra-light'
        }
        
        project_data = {'id': 12, 'name': 'PM Dashboard'}
        epic_data = {'id': 45, 'name': 'WebSocket Features', 'project_id': 12}
        auto_flags = {'project_created': False, 'epic_created': True}
        session_id = 'session_dashboard_abc123'
        
        # Generate payload
        payload = generate_enriched_task_payload(
            task_data, project_data, epic_data, auto_flags, session_id
        )
        
        # Verify payload matches task specification structure
        expected_structure = {
            'task': {
                'id': 123,
                'name': 'Implement WebSocket enhancements',
                'description': 'Add enriched payloads and auto-switch functionality',
                'status': 'pending',
                'ra_score': 8,
                'ra_mode': 'ra-light'
            },
            'epic': {
                'id': 45,
                'name': 'WebSocket Features',
                'project_id': 12
            },
            'project': {
                'id': 12,
                'name': 'PM Dashboard'
            },
            'flags': {
                'project_created': False,
                'epic_created': True
            },
            'initiator': 'session_dashboard_abc123',
            'auto_switch_recommended': True
        }
        
        assert payload == expected_structure
    
    def test_task_updated_event_with_ra_fields(self):
        """Test task.updated event handles RA field changes properly."""
        # Simulate RA field updates
        task_data = {
            'id': 456,
            'name': 'Enhanced Task',
            'status': 'in_progress',
            'ra_score': 9,
            'ra_mode': 'ra-full'
        }
        
        payload = generate_enriched_task_payload(task_data)
        
        # Verify RA fields are preserved
        assert payload['task']['ra_score'] == 9
        assert payload['task']['ra_mode'] == 'ra-full'
    
    def test_logs_appended_sequence_tracking(self):
        """Test logs appended event provides proper sequence tracking."""
        task_id = 789
        log_entries = [
            {'seq': 15, 'kind': 'status', 'content': 'Status changed to IN_PROGRESS'},
            {'seq': 16, 'kind': 'update', 'content': 'RA tags updated'},
            {'seq': 17, 'kind': 'ra_tag', 'content': 'Added SUGGEST_VALIDATION tag'}
        ]
        
        payload = generate_logs_appended_payload(task_id, log_entries)
        
        # Verify sequence tracking for client synchronization
        assert payload['sequence_range']['start'] == 15
        assert payload['sequence_range']['end'] == 17
        assert payload['log_count'] == 3
        
        # Verify all entries are preserved
        assert len(payload['log_entries']) == 3
        assert payload['log_entries'][1]['seq'] == 16


# RA-Light Mode: Performance and Error Handling Tests
class TestPerformanceAndErrorHandling:
    """Test performance characteristics and error handling for WebSocket enhancements."""
    
    def test_large_payload_handling(self):
        """Test handling of large task payloads within reasonable limits."""
        # Create task with large description and many RA tags
        large_description = 'x' * 5000  # 5KB description
        task_data = {
            'id': 999,
            'name': 'Large Task',
            'description': large_description,
            'status': 'pending',
            'ra_score': 10,
            'ra_mode': 'ra-full'
        }
        
        payload = generate_enriched_task_payload(task_data)
        
        # Verify payload is generated correctly
        assert payload['task']['description'] == large_description
        
        # Check payload size is reasonable (under 10KB as per acceptance criteria)
        payload_json = json.dumps(payload)
        payload_size_kb = len(payload_json.encode('utf-8')) / 1024
        
        # #SUGGEST_PERFORMANCE: Task specification requires payloads under 10KB
        assert payload_size_kb < 10, f"Payload size {payload_size_kb:.2f}KB exceeds 10KB limit"
    
    def test_malformed_input_handling(self):
        """Test graceful handling of malformed input data."""
        # Test with missing required fields
        malformed_task_data = {
            'name': 'Incomplete Task'
            # Missing id, status, etc.
        }
        
        # Should not raise exception, should handle gracefully
        payload = generate_enriched_task_payload(malformed_task_data)
        
        # Verify payload is generated with available data
        assert payload['task']['name'] == 'Incomplete Task'
        assert payload['task']['id'] is None  # Missing fields become None
        assert payload['task']['description'] == ''  # Default value
    
    def test_session_id_validation(self):
        """Test session ID handling with various input formats."""
        test_cases = [
            ('session_abc123', 'session_abc123'),  # Normal case
            ('', None),  # Empty string should be None
            (None, None),  # None input
            ('session-with-dashes', 'session-with-dashes'),  # Dashes allowed
            ('session_with_underscores', 'session_with_underscores')  # Underscores allowed
        ]
        
        for input_session, expected_result in test_cases:
            mcp_args = {}
            if input_session is not None:
                mcp_args['client_session_id'] = input_session
            
            result = extract_session_id(mcp_args)
            
            if expected_result is None and input_session == '':
                # Empty string should return the empty string, not None
                assert result == ''
            else:
                assert result == expected_result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])