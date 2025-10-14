"""
Base classes and utilities for MCP tools.

Provides the abstract BaseTool class with database and WebSocket integration,
shared utilities, and common functionality for all tool implementations.
"""

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from ..database import TaskDatabase
from ..api import ConnectionManager

# Configure logging for tool operations
logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """
    Abstract base class for MCP tools with database and WebSocket integration.

    Provides common functionality for database access, WebSocket broadcasting,
    and JSON response formatting. All MCP tools inherit from this base class
    to ensure consistent behavior and integration patterns.

    Standard Mode Assumptions:
    - Database instance is provided during tool initialization
    - WebSocket manager is shared across all tools for broadcasting
    - JSON responses follow standardized success/error format
    - All tool operations are async to support non-blocking database operations
    """

    def __init__(self, database: TaskDatabase, websocket_manager: ConnectionManager):
        """
        Initialize tool with database and WebSocket dependencies.

        Args:
            database: TaskDatabase instance for data operations
            websocket_manager: ConnectionManager for real-time broadcasting
        """
        self.db = database
        self.websocket_manager = websocket_manager

    @abstractmethod
    async def apply(self, **kwargs) -> str:
        """
        Apply the tool operation with provided parameters.

        All MCP tools must implement this method to define their specific
        functionality. Returns JSON-formatted string for client consumption.

        Returns:
            JSON string with operation results or error information
        """
        pass

    def _format_success_response(self, message: str, **kwargs) -> str:
        """
        Format successful operation response as JSON.

        Standard format for all successful tool operations includes
        success flag, message, and any additional data fields.

        Args:
            message: Success message for the operation
            **kwargs: Additional data fields to include in response

        Returns:
            JSON string with success response
        """
        response = {
            "success": True,
            "message": message,
            **kwargs
        }
        return json.dumps(response)

    def _format_error_response(self, message: str, **kwargs) -> str:
        """
        Format error response as JSON.

        Standard format for all error responses includes success flag,
        error message, and any additional context information.

        Args:
            message: Error message explaining the failure
            **kwargs: Additional error context (e.g., lock_holder, expires_at)

        Returns:
            JSON string with error response
        """
        response = {
            "success": False,
            "message": message,
            **kwargs
        }
        return json.dumps(response)

    async def _broadcast_event(self, event_type: str, **event_data):
        """
        Broadcast event to WebSocket clients asynchronously.

        Handles WebSocket broadcasting without blocking tool operations.
        Errors in broadcasting do not affect tool functionality.

        Args:
            event_type: Type of event for client handling
            **event_data: Event-specific data fields
        """
        try:
            event = {
                "type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat() + 'Z',
                **event_data
            }
            # Prefer optimized broadcaster when available
            if hasattr(self.websocket_manager, "optimized_broadcast"):
                await self.websocket_manager.optimized_broadcast(event)
            else:
                await self.websocket_manager.broadcast(event)
        except Exception as e:
            # WebSocket errors should not affect tool operations
            # Standard Mode: Comprehensive error handling without blocking
            logger.warning(f"Failed to broadcast event {event_type}: {e}")

    def _parse_boolean(self, value: Optional[str], default: bool = True) -> bool:
        """
        Parse string boolean value to actual boolean.

        Supports MCP parameter flexibility by accepting both string and boolean inputs.
        Handles common string representations like "true"/"false", "1"/"0", "yes"/"no".

        Args:
            value: String value to parse (None for default)
            default: Default value if None provided

        Returns:
            Boolean value
        """
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
