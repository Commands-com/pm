"""
Knowledge Management Operations

Provides knowledge item storage, retrieval, versioning, and audit logging
for project/epic/task context with hierarchical organization.

This module delegates to methods from the legacy TaskDatabase class
while providing a clean repository interface.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .connection import DatabaseConnection

# Configure logger
logger = logging.getLogger(__name__)


class KnowledgeRepository:
    """
    Repository for knowledge management operations.

    Provides storage, retrieval, updating, and logging for knowledge items
    with hierarchical relationships and version tracking.

    This is a transitional implementation that delegates to the legacy TaskDatabase
    class methods while providing organized repository interface.
    """

    def __init__(self, conn: 'DatabaseConnection'):
        """
        Initialize KnowledgeRepository with database connection.

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

        # Bind all knowledge-related methods from legacy class
        self._bind_legacy_methods(_LegacyDB)

    def _bind_legacy_methods(self, legacy_cls):
        """Bind knowledge-related methods from legacy class to this instance."""
        knowledge_methods = [
            'get_knowledge',
            'upsert_knowledge',
            'append_knowledge_log',
            'get_knowledge_logs',
            'delete_knowledge_item'
        ]

        for method_name in knowledge_methods:
            if hasattr(legacy_cls, method_name):
                # Get the unbound method and bind it to our legacy instance
                method = getattr(legacy_cls, method_name)
                setattr(self._legacy, method_name, method.__get__(self._legacy, type(self._legacy)))
                # Also expose it on self for direct access
                setattr(self, method_name, getattr(self._legacy, method_name))

    # All knowledge methods are dynamically bound in __init__ via _bind_legacy_methods
    # This provides full backward compatibility while organizing the codebase

    # The following methods are available (bound dynamically):
    # - get_knowledge
    # - upsert_knowledge
    # - append_knowledge_log
    # - get_knowledge_logs
    # - delete_knowledge_item
