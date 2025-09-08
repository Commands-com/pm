"""
MCP Tools Implementation for Project Manager

Provides Model Context Protocol (MCP) tools for AI agents to interact with
the project management system. Implements atomic task locking, status updates,
and real-time WebSocket broadcasting for dashboard synchronization.

Key Features:
- BaseTool abstract class with database and WebSocket integration
- GetAvailableTasks: Query tasks with lock filtering
- AcquireTaskLock: Atomic lock acquisition with status change to IN_PROGRESS
- UpdateTaskStatus: Status updates with lock validation and auto-release
- ReleaseTaskLock: Explicit lock release with agent validation
- JSON response formatting for all tool operations
- WebSocket broadcasting for real-time dashboard updates
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from .database import TaskDatabase
from .api import ConnectionManager

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


class GetAvailableTasks(BaseTool):
    """
    MCP tool to retrieve available tasks filtered by status and lock status.
    
    Returns tasks that are available for agent assignment, excluding locked tasks
    by default unless explicitly requested. Supports status filtering to get
    tasks in specific states (TODO, IN_PROGRESS, DONE, etc.).
    
    Standard Mode Implementation:
    - Validates status parameter against known values
    - Excludes locked tasks unless include_locked=True
    - Returns comprehensive task information including availability status
    - Handles database errors gracefully with detailed error responses
    """
    
    async def apply(self, status: str = "ALL", include_locked: bool = False, 
                   limit: Optional[int] = None) -> str:
        """
        Get available tasks filtered by status and lock status.
        
        Args:
            status: Task status to filter by (default: "TODO")
            include_locked: Whether to include locked tasks (default: False)
            limit: Maximum number of tasks to return (optional)
            
        Returns:
            JSON string with list of available tasks or error response
        """
        try:
            # Validate status parameter
            # Standard Mode: Input validation with helpful error messages
            valid_statuses = ['ALL', 'pending', 'in_progress', 'completed', 'blocked', 'TODO', 'DONE', 'IN_PROGRESS', 'REVIEW']
            if status not in valid_statuses:
                return self._format_error_response(
                    f"Invalid status '{status}'. Valid options: {', '.join(valid_statuses)}"
                )
            
            # Normalize status values for database compatibility
            # Database uses different status naming convention than MCP interface
            status_mapping = {
                'TODO': 'pending',
                'DONE': 'completed',
                'IN_PROGRESS': 'in_progress',
                'REVIEW': 'review'
            }
            db_status = status_mapping.get(status, status)
            
            # Get tasks from database
            # Standard Mode Assumption: Database method provides all necessary task data
            if status == 'ALL':
                all_tasks = self.db.get_all_tasks()
                tasks = all_tasks
            elif db_status == 'pending':
                # Use existing get_available_tasks for pending tasks
                tasks = self.db.get_available_tasks(limit=limit)
            else:
                # Get all tasks and filter by status
                all_tasks = self.db.get_all_tasks()
                tasks = [task for task in all_tasks if task['status'] == db_status]
                if limit:
                    tasks = tasks[:limit]
            
            # Filter out locked tasks unless explicitly requested
            if not include_locked:
                current_time = datetime.now(timezone.utc).isoformat() + 'Z'
                available_tasks = []
                
                for task in tasks:
                    # Check if task is currently locked
                    is_locked = (
                        task.get('lock_holder') is not None and
                        task.get('lock_expires_at') is not None and
                        task.get('lock_expires_at') > current_time
                    )
                    
                    if not is_locked:
                        # Add availability metadata for client consumption
                        task_copy = task.copy()
                        task_copy['available'] = True
                        available_tasks.append(task_copy)
                
                tasks = available_tasks
            else:
                # Include locked tasks but mark availability status
                current_time = datetime.now(timezone.utc).isoformat() + 'Z'
                for task in tasks:
                    is_locked = (
                        task.get('lock_holder') is not None and
                        task.get('lock_expires_at') is not None and
                        task.get('lock_expires_at') > current_time
                    )
                    task['available'] = not is_locked
            
            logger.info(f"Retrieved {len(tasks)} available tasks with status '{status}'")
            return json.dumps(tasks)
            
        except Exception as e:
            # Standard Mode: Comprehensive error handling with logging
            logger.error(f"Failed to get available tasks: {e}")
            return self._format_error_response(
                "Failed to retrieve available tasks",
                error_details=str(e)
            )


class AcquireTaskLock(BaseTool):
    """
    MCP tool for atomic task lock acquisition with status change to IN_PROGRESS.
    
    Atomically acquires a lock on the specified task and sets its status to
    IN_PROGRESS. This prevents other agents from modifying the task while work
    is in progress. Uses database atomic operations to prevent race conditions.
    
    Standard Mode Implementation:
    - Validates task exists before attempting lock acquisition
    - Uses atomic database operations to prevent race conditions
    - Automatically sets task status to IN_PROGRESS on successful lock
    - Broadcasts lock acquisition events for real-time dashboard updates
    - Provides detailed error information when lock acquisition fails
    """
    
    async def apply(self, task_id: str, agent_id: str, timeout: int = 300) -> str:
        """
        Atomically acquire lock on a task and set status to IN_PROGRESS.
        
        Args:
            task_id: ID of the task to lock (string, will be converted to int)
            agent_id: ID of the agent requesting the lock
            timeout: Lock timeout in seconds (default: 300 = 5 minutes)
            
        Returns:
            JSON string with success/failure status and lock information
        """
        try:
            # Validate and convert task_id
            # Standard Mode: Input validation with type conversion
            try:
                task_id_int = int(task_id)
            except ValueError:
                return self._format_error_response(f"Invalid task_id '{task_id}'. Must be a number.")
            
            # Validate agent_id
            if not agent_id or not agent_id.strip():
                return self._format_error_response("agent_id cannot be empty")
            
            agent_id = agent_id.strip()
            
            # Validate timeout
            if timeout <= 0 or timeout > 3600:  # Max 1 hour
                return self._format_error_response("timeout must be between 1 and 3600 seconds")
            
            # Check if task exists first
            # Standard Mode: Pre-validation to provide helpful error messages
            lock_status = self.db.get_task_lock_status(task_id_int)
            if "error" in lock_status:
                return self._format_error_response(f"Task {task_id} not found")
            
            # Check if task is already locked
            if lock_status["is_locked"]:
                return self._format_error_response(
                    f"Task {task_id} is already locked",
                    lock_holder=lock_status["lock_holder"],
                    expires_at=lock_status["lock_expires_at"]
                )
            
            # Attempt atomic lock acquisition
            # Database method handles atomicity and race condition prevention
            success = self.db.acquire_task_lock_atomic(task_id_int, agent_id, timeout)
            
            if success:
                # Update task status to IN_PROGRESS after successful lock
                # Standard Mode Assumption: Status should change to IN_PROGRESS when locked
                status_result = self.db.update_task_status(task_id_int, 'in_progress', agent_id)
                
                if not status_result.get('success'):
                    # If status update fails, release the lock to maintain consistency
                    self.db.release_lock(task_id_int, agent_id)
                    return self._format_error_response(
                        f"Lock acquired but failed to set status to IN_PROGRESS: {status_result.get('error')}"
                    )
                
                # Broadcast lock acquisition event
                await self._broadcast_event(
                    "task.locked",
                    task_id=task_id_int,
                    agent_id=agent_id,
                    status="IN_PROGRESS",
                    timeout=timeout
                )
                
                logger.info(f"Task {task_id} locked by agent {agent_id} with {timeout}s timeout")
                
                return self._format_success_response(
                    f"Acquired lock on task {task_id}",
                    task_id=task_id_int,
                    agent_id=agent_id,
                    timeout=timeout,
                    expires_at=(datetime.now(timezone.utc) + timedelta(seconds=timeout)).isoformat() + 'Z'
                )
            else:
                # Lock acquisition failed - task may have been locked by another agent
                # Check current lock status for detailed error response
                current_lock_status = self.db.get_task_lock_status(task_id_int)
                
                if current_lock_status.get("is_locked"):
                    return self._format_error_response(
                        f"Failed to acquire lock on task {task_id}. Task is locked by another agent.",
                        lock_holder=current_lock_status.get("lock_holder"),
                        expires_at=current_lock_status.get("lock_expires_at")
                    )
                else:
                    return self._format_error_response(f"Failed to acquire lock on task {task_id}")
                    
        except Exception as e:
            # Standard Mode: Comprehensive error handling with logging
            logger.error(f"Failed to acquire lock on task {task_id}: {e}")
            return self._format_error_response(
                f"Failed to acquire lock on task {task_id}",
                error_details=str(e)
            )


class UpdateTaskStatus(BaseTool):
    """
    MCP tool for updating task status with lock validation and auto-release.
    
    Updates task status while validating that the requesting agent holds the
    lock on the task. Automatically releases the lock when status is changed
    to DONE, allowing other agents to access the completed task.
    
    Standard Mode Implementation:
    - Validates lock ownership before allowing status updates
    - Supports status transition validation
    - Auto-releases lock when status changes to DONE/completed
    - Broadcasts status change events for real-time dashboard updates
    - Provides detailed validation error messages
    """
    
    async def apply(self, task_id: str, status: str, agent_id: str) -> str:
        """
        Update task status with lock validation and optional auto-release.
        
        Args:
            task_id: ID of the task to update (string, will be converted to int)
            status: New status for the task
            agent_id: ID of the agent requesting the update
            
        Returns:
            JSON string with success/failure status and updated task information
        """
        try:
            # Validate and convert task_id
            try:
                task_id_int = int(task_id)
            except ValueError:
                return self._format_error_response(f"Invalid task_id '{task_id}'. Must be a number.")
            
            # Validate agent_id
            if not agent_id or not agent_id.strip():
                return self._format_error_response("agent_id cannot be empty")
            
            agent_id = agent_id.strip()
            
            # Validate status
            # Standard Mode: Input validation with helpful error messages
            valid_statuses = ['pending', 'in_progress', 'completed', 'blocked', 'TODO', 'DONE', 'IN_PROGRESS']
            if status not in valid_statuses:
                return self._format_error_response(
                    f"Invalid status '{status}'. Valid options: {', '.join(valid_statuses)}"
                )
            
            # Normalize status values for database compatibility
            status_mapping = {
                'TODO': 'pending',
                'DONE': 'completed',
                'IN_PROGRESS': 'in_progress'
            }
            db_status = status_mapping.get(status, status)
            
            # Validate lock ownership before allowing status update
            # This prevents unauthorized status changes and race conditions
            lock_status = self.db.get_task_lock_status(task_id_int)
            if "error" in lock_status:
                return self._format_error_response(f"Task {task_id} not found")
            
            if not lock_status["is_locked"] or lock_status["lock_holder"] != agent_id:
                if not lock_status["is_locked"]:
                    error_msg = f"Task {task_id} must be locked by requesting agent to update status"
                else:
                    error_msg = f"Task {task_id} is locked by different agent: {lock_status['lock_holder']}"
                
                return self._format_error_response(
                    error_msg,
                    lock_holder=lock_status.get("lock_holder"),
                    expires_at=lock_status.get("lock_expires_at")
                )
            
            # Update task status using database method with lock validation
            result = self.db.update_task_status(task_id_int, db_status, agent_id)
            
            if result["success"]:
                # Check if we should auto-release lock when task is completed
                # Standard Mode Assumption: DONE/completed tasks should release locks automatically
                lock_released = False
                if db_status in ['completed', 'DONE']:
                    release_success = self.db.release_lock(task_id_int, agent_id)
                    if release_success:
                        lock_released = True
                        logger.info(f"Auto-released lock on task {task_id} after completion")
                
                # Map database status to UI/UX status vocabulary
                ui_status_map = {
                    'pending': 'TODO',
                    'in_progress': 'IN_PROGRESS',
                    'completed': 'DONE',
                    'review': 'REVIEW',
                    'TODO': 'TODO',
                    'IN_PROGRESS': 'IN_PROGRESS',
                    'DONE': 'DONE',
                    'REVIEW': 'REVIEW'
                }
                ui_status = ui_status_map.get(db_status, db_status)

                # Broadcast status change event
                await self._broadcast_event(
                    "task.status_changed",
                    task_id=task_id_int,
                    status=ui_status,
                    agent_id=agent_id,
                    lock_released=lock_released
                )
                
                # Also broadcast lock release event if applicable
                if lock_released:
                    await self._broadcast_event(
                        "task.unlocked",
                        task_id=task_id_int,
                        agent_id=agent_id,
                        reason="auto_release_on_completion"
                    )
                
                logger.info(f"Task {task_id} status updated to '{db_status}' by agent {agent_id}")
                
                response_data = {
                    "task_id": task_id_int,
                    "status": db_status,
                    "agent_id": agent_id
                }
                
                if lock_released:
                    response_data["lock_released"] = True
                    response_data["message"] = f"Task {task_id} status updated to {db_status} and lock auto-released"
                else:
                    response_data["message"] = f"Task {task_id} status updated to {db_status}"
                
                return self._format_success_response(**response_data)
                
            else:
                # Status update failed
                return self._format_error_response(
                    result.get("error", f"Failed to update task {task_id} status")
                )
                
        except Exception as e:
            # Standard Mode: Comprehensive error handling with logging
            logger.error(f"Failed to update task {task_id} status: {e}")
            return self._format_error_response(
                f"Failed to update task {task_id} status",
                error_details=str(e)
            )


class ReleaseTaskLock(BaseTool):
    """
    MCP tool for explicit task lock release with agent validation.
    
    Allows agents to explicitly release locks on tasks when work is complete
    or when the agent needs to abandon the task. Validates that the requesting
    agent owns the lock before releasing it.
    
    Standard Mode Implementation:
    - Validates agent owns the lock before release
    - Provides detailed error messages for unauthorized release attempts
    - Broadcasts lock release events for real-time dashboard updates
    - Handles edge cases like expired locks gracefully
    """
    
    async def apply(self, task_id: str, agent_id: str) -> str:
        """
        Release lock on a task with agent ownership validation.
        
        Args:
            task_id: ID of the task to unlock (string, will be converted to int)
            agent_id: ID of the agent releasing the lock
            
        Returns:
            JSON string with success/failure status and lock release information
        """
        try:
            # Validate and convert task_id
            try:
                task_id_int = int(task_id)
            except ValueError:
                return self._format_error_response(f"Invalid task_id '{task_id}'. Must be a number.")
            
            # Validate agent_id
            if not agent_id or not agent_id.strip():
                return self._format_error_response("agent_id cannot be empty")
            
            agent_id = agent_id.strip()
            
            # Check current lock status for validation and detailed error messages
            lock_status = self.db.get_task_lock_status(task_id_int)
            if "error" in lock_status:
                return self._format_error_response(f"Task {task_id} not found")
            
            # Validate that the task is actually locked
            if not lock_status["is_locked"]:
                return self._format_error_response(f"Task {task_id} is not currently locked")
            
            # Validate agent ownership
            if lock_status["lock_holder"] != agent_id:
                return self._format_error_response(
                    f"Cannot release lock on task {task_id}. Lock is held by agent '{lock_status['lock_holder']}'",
                    lock_holder=lock_status["lock_holder"],
                    expires_at=lock_status["lock_expires_at"]
                )
            
            # Attempt to release the lock
            # Database method validates agent ownership again for security
            success = self.db.release_lock(task_id_int, agent_id)
            
            if success:
                # Broadcast lock release event
                await self._broadcast_event(
                    "task.unlocked",
                    task_id=task_id_int,
                    agent_id=agent_id,
                    reason="explicit_release"
                )
                
                logger.info(f"Task {task_id} lock released by agent {agent_id}")
                
                return self._format_success_response(
                    f"Released lock on task {task_id}",
                    task_id=task_id_int,
                    agent_id=agent_id
                )
            else:
                # This should not happen if our validation above passed
                # But database operation might fail for other reasons
                return self._format_error_response(
                    f"Failed to release lock on task {task_id}. Agent may not own the lock."
                )
                
        except Exception as e:
            # Standard Mode: Comprehensive error handling with logging
            logger.error(f"Failed to release lock on task {task_id}: {e}")
            return self._format_error_response(
                f"Failed to release lock on task {task_id}",
                error_details=str(e)
            )


# Tool registry for MCP server integration
# Standard Mode: Provide clear interface for tool registration and discovery
AVAILABLE_TOOLS = {
    "get_available_tasks": GetAvailableTasks,
    "acquire_task_lock": AcquireTaskLock,
    "update_task_status": UpdateTaskStatus,
    "release_task_lock": ReleaseTaskLock
}


def create_tool_instance(tool_name: str, database: TaskDatabase, 
                        websocket_manager: ConnectionManager) -> BaseTool:
    """
    Factory function to create tool instances with dependencies.
    
    Provides a clean interface for MCP server integration to create
    tool instances with proper dependency injection.
    
    Args:
        tool_name: Name of the tool to create
        database: TaskDatabase instance for data operations
        websocket_manager: ConnectionManager for real-time broadcasting
        
    Returns:
        Configured tool instance ready for use
        
    Raises:
        KeyError: If tool_name is not found in AVAILABLE_TOOLS
    """
    if tool_name not in AVAILABLE_TOOLS:
        raise KeyError(f"Unknown tool '{tool_name}'. Available tools: {list(AVAILABLE_TOOLS.keys())}")
    
    tool_class = AVAILABLE_TOOLS[tool_name]
    return tool_class(database, websocket_manager)


# Standard Mode Implementation Notes:
# 1. All tools inherit from BaseTool for consistent interface and shared functionality
# 2. JSON response formatting standardized across all tools
# 3. Comprehensive input validation with helpful error messages
# 4. Database integration uses existing atomic operations for thread safety
# 5. WebSocket broadcasting is non-blocking and error-resilient
# 6. Lock validation prevents unauthorized operations and race conditions
# 7. Auto-release functionality reduces manual lock management overhead
# 8. Extensive logging for debugging and monitoring tool operations
# 9. Error handling preserves tool functionality even when subsystems fail
# 10. Tool registry enables clean MCP server integration patterns
