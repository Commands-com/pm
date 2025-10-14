"""
Knowledge management MCP tools.

Provides tools for creating, retrieving, updating knowledge items and
managing knowledge logs for project documentation and context.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from .base import BaseTool

# Configure logging for knowledge tool operations
logger = logging.getLogger(__name__)

class GetKnowledgeTool(BaseTool):
    """
    MCP tool to retrieve knowledge items with flexible filtering options.
    
    Supports filtering by knowledge_id, category, project/epic/task associations,
    hierarchical parent relationships, and activity status. Returns knowledge items
    with full metadata including relationships to projects/epics/tasks.
    
    Standard Mode Implementation:
    - Comprehensive input validation for all filter parameters
    - JSON response formatting with proper error handling
    - Support for hierarchical knowledge organization
    - Integration with project management context
    """
    
    async def apply(
        self, 
        knowledge_id: Optional[str] = None,
        category: Optional[str] = None,
        project_id: Optional[str] = None,
        epic_id: Optional[str] = None,
        task_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        limit: Optional[str] = None,
        include_inactive: Optional[str] = "false"
    ) -> str:
        """
        Retrieve knowledge items with flexible filtering.
        
        Args:
            knowledge_id: Specific knowledge item ID to retrieve (optional)
            category: Filter by category (optional)
            project_id: Filter by project association (optional)
            epic_id: Filter by epic association (optional)
            task_id: Filter by task association (optional)
            parent_id: Filter by parent knowledge item (optional)
            limit: Maximum number of results to return (optional)
            include_inactive: Include inactive knowledge items (default: false)
            
        Returns:
            JSON string with knowledge items list or error response
        """
        try:
            # Standard Mode: Input validation and type conversion
            parsed_knowledge_id = None
            if knowledge_id is not None:
                try:
                    parsed_knowledge_id = int(knowledge_id)
                except ValueError:
                    return self._format_error_response(f"Invalid knowledge_id '{knowledge_id}'. Must be an integer.")
            
            parsed_project_id = None
            if project_id is not None:
                try:
                    parsed_project_id = int(project_id)
                except ValueError:
                    return self._format_error_response(f"Invalid project_id '{project_id}'. Must be an integer.")
            
            parsed_epic_id = None
            if epic_id is not None:
                try:
                    parsed_epic_id = int(epic_id)
                except ValueError:
                    return self._format_error_response(f"Invalid epic_id '{epic_id}'. Must be an integer.")
            
            parsed_task_id = None
            if task_id is not None:
                try:
                    parsed_task_id = int(task_id)
                except ValueError:
                    return self._format_error_response(f"Invalid task_id '{task_id}'. Must be an integer.")
            
            parsed_parent_id = None
            if parent_id is not None:
                try:
                    parsed_parent_id = int(parent_id)
                except ValueError:
                    return self._format_error_response(f"Invalid parent_id '{parent_id}'. Must be an integer.")
            
            parsed_limit = None
            if limit is not None:
                try:
                    parsed_limit = int(limit)
                    if parsed_limit <= 0:
                        return self._format_error_response(f"Invalid limit '{limit}'. Must be a positive integer.")
                except ValueError:
                    return self._format_error_response(f"Invalid limit '{limit}'. Must be an integer.")
            
            # Parse include_inactive boolean
            parsed_include_inactive = False
            if include_inactive is not None:
                if include_inactive.lower() in ['true', '1', 'yes', 'on']:
                    parsed_include_inactive = True
                elif include_inactive.lower() in ['false', '0', 'no', 'off']:
                    parsed_include_inactive = False
                else:
                    return self._format_error_response(f"Invalid include_inactive '{include_inactive}'. Must be true/false.")
            
            # Retrieve knowledge items from database
            knowledge_items = self.db.get_knowledge(
                knowledge_id=parsed_knowledge_id,
                category=category,
                project_id=parsed_project_id,
                epic_id=parsed_epic_id,
                task_id=parsed_task_id,
                parent_id=parsed_parent_id,
                limit=parsed_limit,
                include_inactive=parsed_include_inactive
            )
            
            # Broadcast retrieval event for dashboard updates
            await self._broadcast_event({
                "type": "knowledge_query",
                "filters": {
                    "knowledge_id": parsed_knowledge_id,
                    "category": category,
                    "project_id": parsed_project_id,
                    "epic_id": parsed_epic_id,
                    "task_id": parsed_task_id,
                    "parent_id": parsed_parent_id,
                    "limit": parsed_limit,
                    "include_inactive": parsed_include_inactive
                },
                "result_count": len(knowledge_items),
                "timestamp": datetime.now(timezone.utc).isoformat() + 'Z'
            })
            
            return self._format_success_response(
                f"Retrieved {len(knowledge_items)} knowledge items",
                knowledge_items=knowledge_items,
                total_count=len(knowledge_items),
                filters_applied={
                    "knowledge_id": parsed_knowledge_id,
                    "category": category,
                    "project_id": parsed_project_id,
                    "epic_id": parsed_epic_id,
                    "task_id": parsed_task_id,
                    "parent_id": parsed_parent_id,
                    "limit": parsed_limit,
                    "include_inactive": parsed_include_inactive
                }
            )
            
        except Exception as e:
            logger.error(f"Error in GetKnowledgeTool: {e}")
            return self._format_error_response(f"Failed to retrieve knowledge items: {str(e)}")


class UpsertKnowledgeTool(BaseTool):
    """
    MCP tool to create or update knowledge items with comprehensive metadata support.
    
    Supports both create (knowledge_id=None) and update operations with automatic
    change tracking, versioning, and audit logging. Integrates with project management
    hierarchy and provides flexible tagging and categorization.
    
    Standard Mode Implementation:
    - Comprehensive input validation and type conversion
    - Automatic change detection and audit logging
    - Version control for knowledge items
    - JSON validation for structured fields
    - WebSocket broadcasting for real-time updates
    """
    
    async def apply(
        self,
        knowledge_id: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[str] = None,
        parent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        epic_id: Optional[str] = None,
        task_id: Optional[str] = None,
        priority: Optional[str] = "0",
        is_active: Optional[str] = "true",
        created_by: Optional[str] = None,
        metadata: Optional[str] = None
    ) -> str:
        """
        Create or update a knowledge item.
        
        Args:
            knowledge_id: ID for update, omit for create (optional)
            title: Knowledge item title (required for create)
            content: Knowledge item content (required for create)
            category: Category classification (optional)
            tags: JSON array of tags ["tag1", "tag2"] (optional)
            parent_id: Parent knowledge item ID for hierarchy (optional)
            project_id: Associated project ID (optional)
            epic_id: Associated epic ID (optional)  
            task_id: Associated task ID (optional)
            priority: Priority level 0-5 (default: 0)
            is_active: Whether item is active (default: true)
            created_by: Creator identifier (optional)
            metadata: JSON object with additional metadata (optional)
            
        Returns:
            JSON string with operation result or error response
        """
        try:
            # Standard Mode: Input validation and type conversion
            parsed_knowledge_id = None
            if knowledge_id is not None:
                try:
                    parsed_knowledge_id = int(knowledge_id)
                except ValueError:
                    return self._format_error_response(f"Invalid knowledge_id '{knowledge_id}'. Must be an integer.")
            
            parsed_parent_id = None
            if parent_id is not None:
                try:
                    parsed_parent_id = int(parent_id)
                except ValueError:
                    return self._format_error_response(f"Invalid parent_id '{parent_id}'. Must be an integer.")
            
            parsed_project_id = None
            if project_id is not None:
                try:
                    parsed_project_id = int(project_id)
                except ValueError:
                    return self._format_error_response(f"Invalid project_id '{project_id}'. Must be an integer.")
            
            parsed_epic_id = None
            if epic_id is not None:
                try:
                    parsed_epic_id = int(epic_id)
                except ValueError:
                    return self._format_error_response(f"Invalid epic_id '{epic_id}'. Must be an integer.")
            
            parsed_task_id = None
            if task_id is not None:
                try:
                    parsed_task_id = int(task_id)
                except ValueError:
                    return self._format_error_response(f"Invalid task_id '{task_id}'. Must be an integer.")
            
            parsed_priority = 0
            if priority is not None:
                try:
                    parsed_priority = int(priority)
                    if parsed_priority < 0 or parsed_priority > 5:
                        return self._format_error_response(f"Priority must be between 0 and 5, got {parsed_priority}")
                except ValueError:
                    return self._format_error_response(f"Invalid priority '{priority}'. Must be an integer.")
            
            parsed_is_active = True
            if is_active is not None:
                if is_active.lower() in ['true', '1', 'yes', 'on']:
                    parsed_is_active = True
                elif is_active.lower() in ['false', '0', 'no', 'off']:
                    parsed_is_active = False
                else:
                    return self._format_error_response(f"Invalid is_active '{is_active}'. Must be true/false.")
            
            # Parse JSON fields
            parsed_tags = None
            if tags is not None:
                try:
                    parsed_tags = json.loads(tags)
                    if not isinstance(parsed_tags, list):
                        return self._format_error_response("Tags must be a JSON array of strings")
                except json.JSONDecodeError as e:
                    return self._format_error_response(f"Invalid tags JSON: {e}")
            
            parsed_metadata = None
            if metadata is not None:
                try:
                    parsed_metadata = json.loads(metadata)
                    if not isinstance(parsed_metadata, dict):
                        return self._format_error_response("Metadata must be a JSON object")
                except json.JSONDecodeError as e:
                    return self._format_error_response(f"Invalid metadata JSON: {e}")
            
            # Validate required fields for create operation
            if parsed_knowledge_id is None:
                if not title:
                    return self._format_error_response("Title is required when creating new knowledge items")
                if not content:
                    return self._format_error_response("Content is required when creating new knowledge items")
            
            # Create or update knowledge item
            result = self.db.upsert_knowledge(
                knowledge_id=parsed_knowledge_id,
                title=title,
                content=content,
                category=category,
                tags=parsed_tags,
                parent_id=parsed_parent_id,
                project_id=parsed_project_id,
                epic_id=parsed_epic_id,
                task_id=parsed_task_id,
                priority=parsed_priority,
                is_active=parsed_is_active,
                created_by=created_by,
                metadata=parsed_metadata
            )
            
            # Broadcast upsert event for dashboard updates
            await self._broadcast_event({
                "type": "knowledge_upserted",
                "operation": result["operation"],
                "knowledge_id": result["knowledge_id"],
                "knowledge_item": result["knowledge_item"],
                "timestamp": datetime.now(timezone.utc).isoformat() + 'Z'
            })
            
            return self._format_success_response(
                f"Knowledge item {result['operation']} successfully",
                operation=result["operation"],
                knowledge_id=result["knowledge_id"],
                knowledge_item=result["knowledge_item"]
            )
            
        except Exception as e:
            logger.error(f"Error in UpsertKnowledgeTool: {e}")
            return self._format_error_response(f"Failed to upsert knowledge item: {str(e)}")


class AppendKnowledgeLogTool(BaseTool):
    """
    MCP tool to append log entries to knowledge items for audit trail.
    
    Provides capability to log various actions performed on knowledge items
    such as viewing, referencing, exporting, or custom actions. Updates the
    knowledge item's last activity timestamp and maintains audit trail.
    
    Standard Mode Implementation:
    - Input validation for knowledge_id and action_type
    - Verification that target knowledge item exists and is active
    - JSON validation for metadata field
    - WebSocket broadcasting for real-time activity updates
    """
    
    async def apply(
        self,
        knowledge_id: str,
        action_type: str,
        change_reason: Optional[str] = None,
        created_by: Optional[str] = None,
        metadata: Optional[str] = None
    ) -> str:
        """
        Append a log entry to a knowledge item.
        
        Args:
            knowledge_id: ID of the knowledge item to log (required)
            action_type: Type of action (viewed, referenced, exported, etc.) (required)
            change_reason: Reason for the action/change (optional)
            created_by: User who performed the action (optional)
            metadata: JSON object with additional metadata (optional)
            
        Returns:
            JSON string with log entry result or error response
        """
        try:
            # Standard Mode: Input validation and type conversion
            try:
                parsed_knowledge_id = int(knowledge_id)
            except ValueError:
                return self._format_error_response(f"Invalid knowledge_id '{knowledge_id}'. Must be an integer.")
            
            if not action_type:
                return self._format_error_response("action_type is required")
            
            # Parse metadata JSON if provided
            parsed_metadata = None
            if metadata is not None:
                try:
                    parsed_metadata = json.loads(metadata)
                    if not isinstance(parsed_metadata, dict):
                        return self._format_error_response("Metadata must be a JSON object")
                except json.JSONDecodeError as e:
                    return self._format_error_response(f"Invalid metadata JSON: {e}")
            
            # Append the log entry
            result = self.db.append_knowledge_log(
                knowledge_id=parsed_knowledge_id,
                action_type=action_type,
                change_reason=change_reason,
                created_by=created_by,
                metadata=parsed_metadata
            )
            
            # Broadcast log event for dashboard updates
            await self._broadcast_event({
                "type": "knowledge_log_added",
                "log_id": result["log_id"],
                "knowledge_id": result["knowledge_id"],
                "knowledge_title": result["knowledge_title"],
                "action_type": result["action_type"],
                "created_by": result["created_by"],
                "timestamp": result["created_at"]
            })
            
            return self._format_success_response(
                f"Log entry added to knowledge item '{result['knowledge_title']}'",
                log_id=result["log_id"],
                knowledge_id=result["knowledge_id"],
                knowledge_title=result["knowledge_title"],
                action_type=result["action_type"],
                change_reason=result["change_reason"],
                created_at=result["created_at"],
                created_by=result["created_by"]
            )
            
        except Exception as e:
            logger.error(f"Error in AppendKnowledgeLogTool: {e}")
            return self._format_error_response(f"Failed to append knowledge log: {str(e)}")


class GetKnowledgeLogsTool(BaseTool):
    """
    MCP tool to retrieve log entries for knowledge items.
    
    Provides capability to query the audit trail of a knowledge item with
    optional filtering by action type and result limiting. Returns log entries
    in reverse chronological order (newest first).
    
    Standard Mode Implementation:
    - Input validation for knowledge_id and optional parameters
    - Support for filtering by action type
    - Configurable result limiting for performance
    - JSON parsing of stored metadata fields
    """
    
    async def apply(
        self,
        knowledge_id: str,
        limit: Optional[str] = "50",
        action_type: Optional[str] = None
    ) -> str:
        """
        Retrieve log entries for a knowledge item.
        
        Args:
            knowledge_id: ID of the knowledge item (required)
            limit: Maximum number of log entries to return (default: 50)
            action_type: Filter by specific action type (optional)
            
        Returns:
            JSON string with log entries list or error response
        """
        try:
            # Standard Mode: Input validation and type conversion
            try:
                parsed_knowledge_id = int(knowledge_id)
            except ValueError:
                return self._format_error_response(f"Invalid knowledge_id '{knowledge_id}'. Must be an integer.")
            
            parsed_limit = 50
            if limit is not None:
                try:
                    parsed_limit = int(limit)
                    if parsed_limit <= 0:
                        return self._format_error_response(f"Invalid limit '{limit}'. Must be a positive integer.")
                    if parsed_limit > 1000:
                        return self._format_error_response(f"Invalid limit '{limit}'. Maximum allowed is 1000.")
                except ValueError:
                    return self._format_error_response(f"Invalid limit '{limit}'. Must be an integer.")
            
            # Retrieve log entries
            log_entries = self.db.get_knowledge_logs(
                knowledge_id=parsed_knowledge_id,
                limit=parsed_limit,
                action_type=action_type
            )
            
            # Broadcast retrieval event for dashboard updates
            await self._broadcast_event({
                "type": "knowledge_logs_queried",
                "knowledge_id": parsed_knowledge_id,
                "action_type": action_type,
                "result_count": len(log_entries),
                "limit": parsed_limit,
                "timestamp": datetime.now(timezone.utc).isoformat() + 'Z'
            })
            
            return self._format_success_response(
                f"Retrieved {len(log_entries)} log entries for knowledge item {parsed_knowledge_id}",
                knowledge_id=parsed_knowledge_id,
                log_entries=log_entries,
                total_count=len(log_entries),
                limit=parsed_limit,
                action_type=action_type
            )
            
        except Exception as e:
            logger.error(f"Error in GetKnowledgeLogsTool: {e}")
            return self._format_error_response(f"Failed to retrieve knowledge logs: {str(e)}")


# Tool registry for MCP server integration
# Standard Mode: Provide clear interface for tool registration and discovery
