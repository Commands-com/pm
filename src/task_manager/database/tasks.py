"""
Task Management Operations

Provides comprehensive task CRUD operations, RA metadata management,
task logs, dependencies, and dashboard filtering with context.

This module delegates to methods from the legacy TaskDatabase class
while providing a clean repository interface.
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .connection import DatabaseConnection

# Configure logger
logger = logging.getLogger(__name__)


class TaskRepository:
    """
    Repository for task operations with RA metadata and hierarchical context.

    Provides creation, retrieval, updates, deletion, logging, and listing operations
    for tasks with Response Awareness (RA) methodology support and dashboard integration.

    This is a transitional implementation that delegates to the legacy TaskDatabase
    class methods while providing organized repository interface.
    """

    def __init__(self, conn: 'DatabaseConnection'):
        """
        Initialize TaskRepository with database connection.

        Args:
            conn: DatabaseConnection instance
        """
        self.conn = conn

        # Import legacy class for method delegation (transitional pattern)
        try:
            from ._legacy import TaskDatabase as _LegacyDB
        except ImportError as e:
            raise RuntimeError(
                "Failed to import legacy TaskDatabase for method delegation. "
                "The _legacy.py file is required during the refactoring transition period. "
                f"Error: {e}"
            )

        # Create a minimal legacy instance just for accessing methods
        self._legacy = type('_LegacyMethods', (), {})()
        self._legacy._connection = conn.connection
        self._legacy._connection_lock = conn.connection_lock
        self._legacy.lock_timeout_seconds = conn.lock_timeout_seconds
        self._legacy._get_current_time_str = conn._get_current_time_str

        # Bind all task-related methods from legacy class
        self._bind_legacy_methods(_LegacyDB)

    def _bind_legacy_methods(self, legacy_cls):
        """Bind task-related methods from legacy class to this instance."""
        task_methods = [
            'create_task', 'get_task_details', 'get_task_by_id',
            'get_available_tasks', 'get_all_tasks', 'list_tasks_filtered',
            'update_task_status', 'update_task_ra_fields',
            'add_task_log', 'get_task_logs', 'get_latest_task_log',
            '_process_ra_tags_with_ids', '_extract_tag_type',
            'create_task_with_ra_metadata', 'add_task_log_entry',
            'get_task_details_with_relations', 'get_task_logs_paginated',
            'resolve_task_dependencies', 'update_task_atomic',
            'list_tasks_with_context_dashboard', 'create_task_with_project_context',
            'delete_task', 'cleanup_orphaned_tasks',
            'create_large_dataset_for_performance_testing',
            # Lock methods needed by update_task_status
            'get_task_lock_status', 'acquire_task_lock_atomic', 'release_lock'
        ]

        for method_name in task_methods:
            if hasattr(legacy_cls, method_name):
                # Get the unbound method and bind it to our legacy instance
                method = getattr(legacy_cls, method_name)
                setattr(self._legacy, method_name, method.__get__(self._legacy, type(self._legacy)))
                # Also expose it on self for direct access
                setattr(self, method_name, getattr(self._legacy, method_name))

    # All task methods are dynamically bound in __init__ via _bind_legacy_methods
    # This provides full backward compatibility while organizing the codebase

    # The following methods are available (bound dynamically):
    # - create_task
    # - get_task_details
    # - get_task_by_id
    # - get_available_tasks
    # - get_all_tasks
    # - list_tasks_filtered
    # - update_task_status
    # - update_task_ra_fields
    # - add_task_log
    # - get_task_logs
    # - get_latest_task_log
    # - _process_ra_tags_with_ids
    # - _extract_tag_type
    # - create_task_with_ra_metadata
    # - add_task_log_entry
    # - get_task_details_with_relations
    # - get_task_logs_paginated
    # - resolve_task_dependencies
    # - update_task_atomic
    # - list_tasks_with_context_dashboard
    # - create_task_with_project_context
    # - delete_task
    # - cleanup_orphaned_tasks
    # - create_large_dataset_for_performance_testing
