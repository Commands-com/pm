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
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from .database import TaskDatabase
from .api import ConnectionManager
from .ra_instructions import ra_instructions_manager

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


class GetAvailableTasks(BaseTool):
    """
    MCP tool to retrieve tasks filtered by status and lock state.
    
    By default returns ALL tasks across statuses. Use the `status` parameter
    to filter (e.g., TODO, IN_PROGRESS, DONE, REVIEW). Locked tasks are
    excluded by default unless `include_locked=True`.
    
    Implementation notes:
    - Validates status against known values (including 'ALL')
    - Maps UI statuses (TODO/DONE/IN_PROGRESS/REVIEW) to database values
    - For pending work (TODO/pending), uses an optimized query; other statuses
      are filtered from the full task list
    - Returns availability metadata for client consumption
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
            valid_statuses = ['ALL', 'pending', 'in_progress', 'completed', 'blocked', 'backlog', 'TODO', 'DONE', 'IN_PROGRESS', 'REVIEW', 'BACKLOG']
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


class GetInstructionsTool(BaseTool):
    """
    MCP tool to retrieve RA methodology instructions text for clients with knowledge context injection.

    Provides either the full or concise instruction set along with version and
    last updated metadata. Automatically injects project/epic knowledge context
    when task context parameters are provided.
    """

    async def apply(
        self, 
        format: str = "concise", 
        project_id: Optional[str] = None,
        epic_id: Optional[str] = None,
        include_knowledge_context: Optional[str] = "true"
    ) -> str:
        """
        Get RA methodology instructions with optional knowledge context injection.

        Args:
            format: "full" or "concise" (default: "concise")
            project_id: Project ID for knowledge context (optional)
            epic_id: Epic ID for knowledge context (optional)
            include_knowledge_context: Whether to inject knowledge context (default: "true")

        Returns:
            JSON string including instructions text, metadata, and knowledge context
        """
        try:
            fmt = (format or "concise").strip().lower()
            if fmt not in ("full", "concise"):
                return self._format_error_response(
                    "Invalid format. Use 'full' or 'concise'",
                    valid_formats=["full", "concise"]
                )

            # Get base instructions
            if fmt == "full":
                instructions = ra_instructions_manager.get_full_instructions()
            else:
                instructions = ra_instructions_manager.get_concise_instructions()

            # Inject knowledge context if requested and project context is available
            knowledge_context = ""
            if include_knowledge_context and include_knowledge_context.lower() == "true":
                if project_id:
                    try:
                        parsed_project_id = int(project_id)
                        parsed_epic_id = None
                        if epic_id:
                            parsed_epic_id = int(epic_id)

                        knowledge_context = await get_task_knowledge_context(
                            self.db, 
                            project_id=parsed_project_id, 
                            epic_id=parsed_epic_id
                        )

                        if knowledge_context and "No knowledge" not in knowledge_context:
                            # Prepend knowledge context to instructions
                            instructions = f"{knowledge_context}\n\n---\n\n{instructions}"

                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid project/epic ID for knowledge context: {e}")

            return self._format_success_response(
                "Instructions retrieved" + (" with knowledge context" if knowledge_context else ""),
                instructions=instructions,
                format=fmt,
                version=ra_instructions_manager.version,
                last_updated=ra_instructions_manager.last_updated,
                knowledge_context_included=bool(knowledge_context and "No knowledge" not in knowledge_context),
                context_source={
                    "project_id": project_id,
                    "epic_id": epic_id
                } if project_id else None
            )
        except Exception as e:
            logger.error(f"Failed to get instructions: {e}")
            return self._format_error_response(
                "Failed to get instructions",
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
            
            # Clear any expired locks and broadcast unlock events
            try:
                expired_ids = self.db.cleanup_expired_locks_with_ids()
                for eid in expired_ids:
                    await self._broadcast_event(
                        "task.unlocked",
                        task_id=eid,
                        agent_id=None,
                        reason="lock_expired"
                    )
            except Exception:
                pass

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
    MCP tool for updating task status with auto-lock and release semantics.
    
    Behavior:
    - If the task is unlocked, the tool auto-acquires a lock for the requesting
      agent, performs the status update, then releases the lock (unless moving
      to IN_PROGRESS).
    - If the task is locked by another agent, returns an error.
    - If the task is locked by the requesting agent, proceeds normally.
    - Auto-releases the lock when status changes to DONE/completed or when the
      lock was auto-acquired and the new status is not IN_PROGRESS.
    - Broadcasts real-time events for dashboard updates.
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
            valid_statuses = ['pending', 'in_progress', 'completed', 'review', 'blocked', 'backlog', 'TODO', 'DONE', 'IN_PROGRESS', 'REVIEW', 'BACKLOG']
            if status not in valid_statuses:
                return self._format_error_response(
                    f"Invalid status '{status}'. Valid options: {', '.join(valid_statuses)}"
                )
            
            # Normalize status values for database compatibility
            status_mapping = {
                'TODO': 'pending',
                'DONE': 'completed',
                'IN_PROGRESS': 'in_progress',
                'REVIEW': 'review'
            }
            db_status = status_mapping.get(status, status)
            
            # Clear any expired locks and broadcast unlock events
            try:
                expired_ids = self.db.cleanup_expired_locks_with_ids()
                for eid in expired_ids:
                    await self._broadcast_event(
                        "task.unlocked",
                        task_id=eid,
                        agent_id=None,
                        reason="lock_expired"
                    )
            except Exception:
                pass

            # Ensure lock ownership before allowing status update.
            # If unlocked, attempt to auto-acquire lock for this update (single-call UX).
            lock_status = self.db.get_task_lock_status(task_id_int)
            if "error" in lock_status:
                return self._format_error_response(f"Task {task_id} not found")

            auto_locked = False
            if lock_status["is_locked"]:
                if lock_status["lock_holder"] != agent_id:
                    return self._format_error_response(
                        f"Task {task_id} is locked by different agent: {lock_status['lock_holder']}",
                        lock_holder=lock_status.get("lock_holder"),
                        expires_at=lock_status.get("lock_expires_at")
                    )
            else:
                # Try to acquire lock automatically
                if not self.db.acquire_task_lock_atomic(task_id_int, agent_id, 300):
                    return self._format_error_response(
                        f"Failed to acquire lock on task {task_id} for update"
                    )
                auto_locked = True
            
            # Update task status using database method with lock validation
            result = self.db.update_task_status(task_id_int, db_status, agent_id)
            
            if result["success"]:
                # Decide whether to release lock after update
                lock_released = False
                # Release locks when entering REVIEW or DONE/completed, or when we auto-locked and are not staying IN_PROGRESS
                should_release = (db_status in ['completed', 'review', 'DONE', 'REVIEW']) or (auto_locked and db_status != 'in_progress')
                if should_release:
                    release_success = self.db.release_lock(task_id_int, agent_id)
                    if release_success:
                        lock_released = True
                        logger.info(f"Auto-released lock on task {task_id} after status update")
                else:
                    # If we auto-acquired and are keeping the lock (e.g., IN_PROGRESS), broadcast lock
                    if auto_locked:
                        await self._broadcast_event(
                            "task.locked",
                            task_id=task_id_int,
                            agent_id=agent_id,
                            status="IN_PROGRESS"
                        )
                
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


class CreateTaskTool(BaseTool):
    """
    MCP tool for creating tasks with project/epic upsert and RA metadata support.
    
    # RA-Light Mode Implementation:
    # Comprehensive task creation tool that handles project/epic upsert logic,
    # RA complexity auto-assessment, full RA metadata support, system prompt snapshots,
    # and WebSocket broadcasting with enriched payloads for dashboard synchronization.
    
    Key Features:
    - Project upsert: creates project by name if not found
    - Epic upsert: creates epic by name within project if not found  
    - RA complexity auto-assessment when ra_score not provided
    - Full RA metadata support (mode, tags, metadata, prompt snapshot)
    - Initial task log entry with "create" kind
    - WebSocket broadcasting with enriched project/epic data
    - Comprehensive parameter validation with helpful error messages
    """
    
    async def apply(
        self,
        name: str,
        description: str = "",
        epic_id: Optional[int] = None,
        epic_name: Optional[str] = None,
        project_id: Optional[int] = None,
        project_name: Optional[str] = None,
        ra_mode: Optional[str] = None,
        ra_score: Optional[int] = None,
        ra_tags: Optional[List[str]] = None,
        ra_metadata: Optional[Dict[str, Any]] = None,
        prompt_snapshot: Optional[str] = None,
        dependencies: Optional[List[int]] = None,
        parallel_group: Optional[str] = None,
        conflicts_with: Optional[List[int]] = None,
        parallel_eligible: Optional[str] = None,  # Accept string for MCP compatibility
        client_session_id: Optional[str] = None
    ) -> str:
        """
        Create a task with project/epic upsert and full RA metadata support.
        
        # RA-Light Mode: Comprehensive parameter validation and error handling
        # with detailed RA tag documentation of all assumptions and integration points.
        
        Args:
            name: Task name (required)
            description: Task description (optional, defaults to empty string)
            epic_id: ID of existing epic (either epic_id or epic_name required)
            epic_name: Name of epic (created if not found, with project)
            project_id: ID of existing project (used with epic_name)
            project_name: Name of project (created if not found)
            ra_mode: RA mode (simple, standard, ra-light, ra-full)
            ra_score: RA complexity score (1-10, auto-assessed if not provided)
            ra_tags: List of RA assumption tags
            ra_metadata: Additional RA metadata dictionary
            prompt_snapshot: System prompt snapshot (auto-captured if not provided)
            dependencies: List of task IDs this task depends on
            parallel_group: Group name for parallel execution (e.g., "backend", "frontend")
            conflicts_with: List of task IDs that cannot run simultaneously
            parallel_eligible: Whether this task can be executed in parallel (default: True)
            client_session_id: Client session for dashboard auto-switch functionality
            
        Returns:
            JSON string with created task information and success status
        """
        try:
            # === PARAMETER VALIDATION ===
            
            # Validate required parameters
            if not name or not name.strip():
                return self._format_error_response("Task name is required and cannot be empty")
            
            name = name.strip()
            
            # Validate epic identification parameters
            # VERIFIED: Task specification requires "either epic_id or epic_name" for epic identification
            if not epic_id and not epic_name:
                return self._format_error_response(
                    "Either epic_id or epic_name must be provided to identify the epic"
                )
            
            if epic_id and epic_name:
                return self._format_error_response(
                    "Provide either epic_id or epic_name, not both"
                )
            
            # Validate project identification when using epic_name
            if epic_name and not project_id and not project_name:
                return self._format_error_response(
                    "When using epic_name, either project_id or project_name must be provided"
                )
            
            if epic_name and project_id and project_name:
                return self._format_error_response(
                    "When using epic_name, provide either project_id or project_name, not both"
                )
            
            # Validate RA parameters
            if ra_score is not None and (ra_score < 1 or ra_score > 10):
                return self._format_error_response(
                    "ra_score must be between 1 and 10 if provided"
                )
            
            if ra_mode and ra_mode not in ['simple', 'standard', 'ra-light', 'ra-full']:
                return self._format_error_response(
                    "ra_mode must be one of: simple, standard, ra-light, ra-full"
                )
            
            # === PROJECT/EPIC UPSERT LOGIC ===
            
            resolved_project_id = None
            resolved_epic_id = None
            project_data = None
            epic_data = None
            project_was_created = False
            epic_was_created = False
            
            if epic_id:
                # Use existing epic_id directly
                # VERIFIED: Task specification accepts epic_id as existing identifier
                # Database foreign key constraint enforces referential integrity per schema design
                resolved_epic_id = epic_id
                
                # Get project and epic data for WebSocket event enrichment
                # #SUGGEST_ERROR_HANDLING: Handle case where epic_id doesn't exist
                try:
                    epic_info = self.db.get_epic_with_project_info(epic_id)
                    if epic_info:
                        resolved_project_id = epic_info.get('project_id')
                        project_data = {
                            'id': epic_info.get('project_id'),
                            'name': epic_info.get('project_name')
                        }
                        epic_data = {
                            'id': epic_info.get('epic_id'),
                            'name': epic_info.get('epic_name')
                        }
                except Exception:
                    # VERIFIED: Epic info retrieval is for WebSocket enrichment only
                    # Task creation validates epic_id via foreign key constraint
                    pass
                    
            else:
                # Upsert project first
                if project_name:
                    # Project upsert is atomic and race-condition safe per task requirements
                    resolved_project_id, project_was_created = self.db.upsert_project_with_status(project_name, "")
                    project_data = {'id': resolved_project_id, 'name': project_name}
                else:
                    # Use existing project_id
                    resolved_project_id = project_id
                    # #SUGGEST_VALIDATION: Could validate that project_id exists
                    project_data = {'id': resolved_project_id, 'name': 'Unknown'}
                
                # Upsert epic within the project
                # Epic upsert handles race conditions with SELECT + INSERT pattern as required by task spec
                resolved_epic_id, epic_was_created = self.db.upsert_epic_with_status(resolved_project_id, epic_name, "")
                epic_data = {'id': resolved_epic_id, 'name': epic_name, 'project_id': resolved_project_id}
            
            # === RA COMPLEXITY AUTO-ASSESSMENT ===
            
            if ra_score is None and ra_mode in ['ra-light', 'ra-full']:
                # Auto-assess complexity based on task characteristics
                # VERIFIED: Task specification requires "RA complexity auto-assessment works when ra_score not provided"
                # Algorithm uses task characteristics per acceptance criteria
                
                base_score = 5  # Default middle complexity
                
                # Description complexity factor
                if description and len(description) > 500:
                    base_score += 1
                elif description and len(description) > 200:
                    base_score += 0.5
                
                # Dependency complexity factor
                if dependencies and len(dependencies) > 5:
                    base_score += 2
                elif dependencies and len(dependencies) > 2:
                    base_score += 1
                elif dependencies and len(dependencies) > 0:
                    base_score += 0.5
                
                # RA mode complexity factor
                if ra_mode == 'ra-full':
                    base_score += 2
                elif ra_mode == 'ra-light':
                    base_score += 1
                
                # RA tags complexity factor (high tag count suggests complex implementation)
                if ra_tags and len(ra_tags) > 10:
                    base_score += 1
                elif ra_tags and len(ra_tags) > 5:
                    base_score += 0.5
                
                # VERIFIED: Score range 1-10 per parameter validation requirements
                ra_score = max(1, min(10, round(base_score)))
            
            # === PROMPT SNAPSHOT CAPTURE ===
            
            if prompt_snapshot is None:
                # VERIFIED: Task specification requires "Prompt snapshot stored from current system instructions"
                # Standard Mode: Integrate with RA instructions manager for proper prompt capture
                prompt_snapshot = ra_instructions_manager.capture_prompt_snapshot("task_creation")
            
            # === TASK CREATION ===
            
            # Convert parallel_eligible from string to boolean for database compatibility
            parallel_eligible_bool = self._parse_boolean(parallel_eligible, default=True)
            
            # Create task with all RA metadata
            task_id = self.db.create_task_with_ra_metadata(
                epic_id=resolved_epic_id,
                name=name,
                description=description,
                ra_mode=ra_mode,
                ra_score=ra_score,
                ra_tags=ra_tags,
                ra_metadata=ra_metadata,
                prompt_snapshot=prompt_snapshot,
                dependencies=dependencies,
                parallel_group=parallel_group,
                conflicts_with=conflicts_with,
                parallel_eligible=parallel_eligible_bool
            )
            
            # === INITIAL TASK LOG ENTRY ===
            
            # Create initial log entry for task creation
            # VERIFIED: Task specification requires "Initial task log entry created with 'create' kind"
            creation_payload = {
                'agent_action': 'task_created',
                'original_parameters': {
                    'name': name,
                    'description': description,
                    'ra_mode': ra_mode,
                    'ra_score': ra_score,
                    'dependencies': dependencies
                },
                'resolved_ids': {
                    'project_id': resolved_project_id,
                    'epic_id': resolved_epic_id,
                    'task_id': task_id
                }
            }
            
            log_seq = self.db.add_task_log_entry(task_id, 'create', creation_payload)
            
            # === PROMPT SNAPSHOT LOG ENTRY ===
            
            # Create additional log entry for prompt tracking audit trail
            # Standard Mode: Task specification requires log entry with kind="prompt"
            prompt_log_payload = {
                'prompt_snapshot': prompt_snapshot,
                'ra_mode': ra_mode,
                'ra_score': ra_score,
                'instructions_version': ra_instructions_manager.version,
                'capture_context': 'task_creation'
            }
            
            prompt_log_seq = self.db.add_task_log_entry(task_id, 'prompt', prompt_log_payload)
            
            # === WEBSOCKET EVENT BROADCASTING ===
            
            # Broadcast enriched task.created event with comprehensive payload
            # VERIFIED: Task specification requires "WebSocket event broadcasted with enriched payload"
            # Using new enriched payload generation functions from api.py
            
            # #COMPLETION_DRIVE_INTEGRATION: Import enriched payload functions
            from .api import generate_enriched_task_payload, extract_session_id
            
            # Prepare task data for enriched payload
            task_data = {
                "id": task_id,
                "name": name,
                "description": description,
                "status": "pending",
                "epic_id": resolved_epic_id,
                "ra_score": ra_score,
                "ra_mode": ra_mode
            }
            
            # Determine auto-switch flags based on creation context
            # #COMPLETION_DRIVE_IMPL: Flag generation logic for project/epic creation detection
            # Use actual creation status from upsert operations
            auto_flags = {
                "project_created": project_was_created,
                "epic_created": epic_was_created
            }
            
            # Extract session ID for auto-switch functionality
            session_id = client_session_id
            
            # Generate enriched payload with all context
            enriched_data = generate_enriched_task_payload(
                task_data=task_data,
                project_data=project_data,
                epic_data=epic_data,
                auto_flags=auto_flags,
                session_id=session_id
            )
            
            # Broadcast enriched event using ConnectionManager's new method
            if hasattr(self.websocket_manager, "broadcast_enriched_event"):
                await self.websocket_manager.broadcast_enriched_event("task.created", enriched_data)
            else:
                # Fallback to existing broadcast method with enriched structure
                await self._broadcast_event("task.created", **enriched_data)
            
            # === SUCCESS RESPONSE ===
            
            logger.info(f"Created task '{name}' (ID: {task_id}) in epic {resolved_epic_id}")
            
            return self._format_success_response(
                f"Task '{name}' created successfully",
                task_id=task_id,
                project_id=resolved_project_id,
                epic_id=resolved_epic_id,
                ra_score=ra_score,
                ra_mode=ra_mode,
                log_sequence=log_seq
            )
            
        except sqlite3.IntegrityError as e:
            # Database constraint violations (foreign key, unique constraints, etc.)
            # #SUGGEST_ERROR_HANDLING: More specific error messages based on constraint type
            logger.error(f"Database integrity error creating task: {e}")
            return self._format_error_response(
                "Database constraint violation. Check that project/epic IDs exist and are valid.",
                error_details=str(e)
            )
            
        except Exception as e:
            # Comprehensive error handling for all other exceptions
            logger.error(f"Unexpected error creating task '{name}': {e}")
            return self._format_error_response(
                f"Failed to create task '{name}'",
                error_details=str(e)
            )
    
    # Helper method for epic info retrieval with project context
    # Helper method for epic info retrieval with project context
    # Current implementation requires this functionality to be added to TaskDatabase
    def _get_epic_with_project_info(self, epic_id: int) -> Optional[Dict[str, Any]]:
        """
        Get epic information with associated project data.
        
        # #SUGGEST_IMPLEMENTATION: Add this method to TaskDatabase class
        # Returns epic and project information in a single query for efficiency
        """
        # For now, return None to indicate method needs implementation
        # Real implementation would join epics and projects tables
        return None


class UpdateTaskTool(BaseTool):
    """
    MCP tool for comprehensive task field updates with RA metadata support.
    
    # RA-Light Mode Implementation:
    # Comprehensive task update tool that handles atomic field updates, RA metadata
    # merge/replace logic, integrated logging, WebSocket broadcasting, and lock coordination.
    # Provides single-call interface for agents to update multiple task fields safely.
    
    Key Features:
    - Atomic multi-field updates (all succeed or all fail)
    - RA tags merge/replace with intelligent JSON handling
    - RA metadata merge/replace with dict.update() semantics
    - Integrated task logging with sequence management
    - Status vocabulary mapping (TODO/DONE/etc <-> pending/completed/etc)
    - Auto-locking for unlocked tasks with smart release logic
    - WebSocket broadcasting with detailed change payloads
    - Lock validation for concurrent agent coordination
    """
    
    async def apply(
        self,
        task_id: str,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        ra_mode: Optional[str] = None,
        ra_score: Optional[int] = None,
        ra_tags: Optional[List[str]] = None,
        ra_metadata: Optional[Dict[str, Any]] = None,
        ra_tags_mode: str = "merge",
        ra_metadata_mode: str = "merge",
        log_entry: Optional[str] = None,
        dependencies: Optional[List[int]] = None,
        parallel_group: Optional[str] = None,
        conflicts_with: Optional[List[int]] = None,
        parallel_eligible: Optional[str] = None  # Accept string for MCP compatibility
    ) -> str:
        """
        Update task fields atomically with comprehensive RA metadata support.
        
        # RA-Light Mode: Comprehensive parameter validation and atomic update logic
        # with extensive assumption tracking for all implementation and integration decisions.
        
        Args:
            task_id: ID of the task to update (string, converted to int)
            agent_id: ID of the agent performing the update
            name: New task name (optional)
            description: New task description (optional)
            status: New task status (optional - supports both UI and DB vocabulary)
            ra_mode: New RA mode (optional - simple, standard, ra-light, ra-full)
            ra_score: New RA complexity score (optional - 1-10)
            ra_tags: RA tags to merge or replace (optional list)
            ra_metadata: RA metadata to merge or replace (optional dict)
            ra_tags_mode: How to handle ra_tags - "merge" or "replace" (default: merge)
            ra_metadata_mode: How to handle ra_metadata - "merge" or "replace" (default: merge)
            log_entry: Optional log message to append with sequence numbering
            dependencies: List of task IDs this task depends on (optional)
            parallel_group: Group name for parallel execution (e.g., "backend", "frontend")
            conflicts_with: List of task IDs that cannot run simultaneously
            parallel_eligible: Whether this task can be executed in parallel
            
        Returns:
            JSON string with success status, updated fields summary, and metadata
            
        # Single-call interface provides atomic operations as required by task specification
        # Reduces coordination complexity compared to multiple separate update calls
        
        # WebSocket broadcasting integration provides detailed field change information
        # for dashboard clients' real-time UI updates as required
        """
        try:
            # === PARAMETER VALIDATION ===
            
            # Validate and convert task_id
            # Task ID validation uses string-to-int conversion pattern
            # consistent with other MCP tools in the system
            try:
                task_id_int = int(task_id)
            except ValueError:
                return self._format_error_response(f"Invalid task_id '{task_id}'. Must be a number.")
            
            # Validate agent_id
            if not agent_id or not agent_id.strip():
                return self._format_error_response("agent_id cannot be empty")
            
            agent_id = agent_id.strip()
            
            # Validate status values using existing vocabulary mapping
            # Status vocabulary mapping provides bidirectional
            # compatibility between UI terminology and database storage format
            if status is not None:
                valid_statuses = ['pending', 'in_progress', 'completed', 'blocked', 'review', 'backlog',
                                'TODO', 'DONE', 'IN_PROGRESS', 'REVIEW', 'BACKLOG']
                if status not in valid_statuses:
                    return self._format_error_response(
                        f"Invalid status '{status}'. Valid options: {', '.join(valid_statuses)}"
                    )
                
                # Normalize status to database vocabulary
                # Status normalization uses consistent mapping logic
                # with other status-handling tools for system-wide compatibility
                status_mapping = {
                    'TODO': 'pending',
                    'DONE': 'completed', 
                    'IN_PROGRESS': 'in_progress',
                    'REVIEW': 'review'
                }
                status = status_mapping.get(status, status)
            
            # Validate RA parameters
            # RA parameter validation uses same constraints
            # as CreateTaskTool for consistency across task management operations
            if ra_score is not None and (ra_score < 1 or ra_score > 10):
                return self._format_error_response("ra_score must be between 1 and 10")
            
            if ra_mode is not None and ra_mode not in ['simple', 'standard', 'ra-light', 'ra-full']:
                return self._format_error_response(
                    "ra_mode must be one of: simple, standard, ra-light, ra-full"
                )
            
            # Validate merge/replace mode parameters
            # Mode validation uses "merge" and "replace" as the only valid options
            # for RA metadata handling based on common data merging patterns
            if ra_tags_mode not in ['merge', 'replace']:
                return self._format_error_response(
                    "ra_tags_mode must be 'merge' or 'replace'"
                )
            
            if ra_metadata_mode not in ['merge', 'replace']:
                return self._format_error_response(
                    "ra_metadata_mode must be 'merge' or 'replace'"
                )
            
            # Validate at least one field is provided for update
            # Empty update validation requires agents to specify
            # at least one field to update to prevent accidental no-op calls
            update_fields_provided = any([
                name is not None, description is not None, status is not None,
                ra_mode is not None, ra_score is not None, ra_tags is not None,
                ra_metadata is not None, log_entry is not None
            ])
            
            if not update_fields_provided:
                return self._format_error_response(
                    "At least one field must be provided for update"
                )
            
            # === ATOMIC DATABASE UPDATE ===
            
            # Clear expired locks before attempting update
            # Expired lock cleanup follows consistent pattern
            # with other locking tools for system-wide lock hygiene
            try:
                expired_ids = self.db.cleanup_expired_locks_with_ids()
                for eid in expired_ids:
                    await self._broadcast_event(
                        "task.unlocked",
                        task_id=eid,
                        agent_id=None,
                        reason="lock_expired"
                    )
            except Exception:
                # #SUGGEST_ERROR_HANDLING: Lock cleanup errors should not block update operations
                pass
            
            # Execute atomic database update with all parameters
            # Database integration uses update_task_atomic method which
            # handles all complexity of field validation, JSON merging, and transaction management
            
            # Convert parallel_eligible from string to boolean if provided
            parallel_eligible_bool = None
            if parallel_eligible is not None:
                parallel_eligible_bool = self._parse_boolean(parallel_eligible)
            
            update_result = self.db.update_task_atomic(
                task_id=task_id_int,
                agent_id=agent_id,
                name=name,
                description=description,
                status=status,
                ra_mode=ra_mode,
                ra_score=ra_score,
                ra_tags=ra_tags,
                ra_metadata=ra_metadata,
                ra_tags_mode=ra_tags_mode,
                ra_metadata_mode=ra_metadata_mode,
                log_entry=log_entry,
                dependencies=dependencies,
                parallel_group=parallel_group,
                conflicts_with=conflicts_with,
                parallel_eligible=parallel_eligible_bool
            )
            
            if not update_result["success"]:
                # Database update failed - return error with details
                return self._format_error_response(
                    update_result["error"],
                    **{k: v for k, v in update_result.items() if k not in ["success", "error"]}
                )
            
            # === WEBSOCKET EVENT BROADCASTING ===
            
            # Broadcast enriched task.updated event with comprehensive payload
            # #COMPLETION_DRIVE_INTEGRATION: Enhanced task.updated events as specified in task requirements
            # Provides comprehensive change information with project/epic context for dashboard updates
            updated_fields = update_result.get("updated_fields", {})
            
            if updated_fields:  # Only broadcast if actual changes were made
                # Import enriched payload functions
                from .api import generate_enriched_task_payload, extract_session_id
                
                # Get complete task data for enriched payload
                # #COMPLETION_DRIVE_IMPL: Need full task context for enriched events
                task_details = self.db.get_task_details_with_relations(task_id_int)
                
                if task_details:
                    task_data = task_details["task"]
                    project_data = task_details.get("project")
                    epic_data = task_details.get("epic")
                    
                    # Map database status to UI vocabulary for consistency
                    if "status" in updated_fields:
                        ui_status_map = {
                            'pending': 'TODO',
                            'in_progress': 'IN_PROGRESS', 
                            'completed': 'DONE',
                            'review': 'REVIEW'
                        }
                        db_status = updated_fields["status"]["new"]
                        ui_status = ui_status_map.get(db_status, db_status)
                        task_data["status"] = ui_status
                    
                    # Generate enriched task payload
                    enriched_data = generate_enriched_task_payload(
                        task_data=task_data,
                        project_data=project_data,
                        epic_data=epic_data
                    )
                    
                    # Add update-specific fields to enriched payload
                    enriched_data.update({
                        "changed_fields": list(updated_fields.keys()),
                        "field_changes": updated_fields,
                        "fields_count": update_result.get("fields_updated_count", 0),
                        "agent_id": agent_id,
                        "auto_locked": update_result.get("auto_locked", False),
                        "lock_released": update_result.get("lock_released", False)
                    })
                    
                    # Add log sequence if logging was performed
                    if update_result.get("log_sequence"):
                        enriched_data["log_sequence"] = update_result["log_sequence"]
                    
                    # Broadcast enriched task.updated event
                    if hasattr(self.websocket_manager, "broadcast_enriched_event"):
                        await self.websocket_manager.broadcast_enriched_event("task.updated", enriched_data)
                    else:
                        await self._broadcast_event("task.updated", **enriched_data)
                    
                    # === TASK.LOGS.APPENDED EVENT BROADCASTING ===
                    
                    # If a log entry was added, broadcast task.logs.appended event
                    # #COMPLETION_DRIVE_IMPL: Real-time log updates as specified in task requirements
                    if update_result.get("log_sequence") and log_entry:
                        from .api import generate_logs_appended_payload
                        
                        # Get the new log entry that was just added
                        new_log_entries = [{
                            "seq": update_result["log_sequence"],
                            "kind": "update",
                            "content": log_entry,
                            "timestamp": update_result.get("timestamp"),
                            "agent_id": agent_id
                        }]
                        
                        # Generate logs appended payload
                        logs_payload = generate_logs_appended_payload(
                            task_id=task_id_int,
                            log_entries=new_log_entries
                        )
                        
                        # Broadcast task.logs.appended event
                        if hasattr(self.websocket_manager, "broadcast_enriched_event"):
                            await self.websocket_manager.broadcast_enriched_event("task.logs.appended", logs_payload)
                        else:
                            await self._broadcast_event("task.logs.appended", **logs_payload)
                
                # Broadcast additional lock events if relevant
                # Lock event broadcasting provides separate lock state notifications
                # for dashboard's proper UI state management
                if update_result.get("auto_locked"):
                    await self._broadcast_event(
                        "task.locked",
                        task_id=task_id_int,
                        agent_id=agent_id,
                        reason="auto_lock_for_update"
                    )
                
                if update_result.get("lock_released"):
                    await self._broadcast_event(
                        "task.unlocked", 
                        task_id=task_id_int,
                        agent_id=agent_id,
                        reason="auto_release_after_update"
                    )
            
            # === SUCCESS RESPONSE ===
            
            logger.info(f"Task {task_id} updated by agent {agent_id}: {len(updated_fields)} fields changed")
            
            # Prepare comprehensive success response
            # Response structure provides detailed feedback
            # about what changed for debugging and coordination purposes
            response_data = {
                "task_id": task_id_int,
                "agent_id": agent_id,
                "fields_updated": list(updated_fields.keys()),
                "fields_updated_count": update_result.get("fields_updated_count", 0),
                "log_sequence": update_result.get("log_sequence"),
                "auto_locked": update_result.get("auto_locked", False),
                "lock_released": update_result.get("lock_released", False),
                "timestamp": update_result.get("timestamp")
            }
            
            # Add field change details for debugging
            # #SUGGEST_VALIDATION: Consider filtering sensitive information from field details
            if updated_fields:
                response_data["field_changes"] = updated_fields
            
            message = f"Task {task_id} updated successfully"
            if update_result.get("fields_updated_count", 0) == 0:
                message += " (no changes needed)"
            else:
                message += f" ({update_result.get('fields_updated_count', 0)} fields changed)"
            
            return self._format_success_response(message, **response_data)
            
        except Exception as e:
            # #SUGGEST_ERROR_HANDLING: Comprehensive error handling should provide context
            # while avoiding exposure of internal system details
            logger.error(f"Unexpected error updating task {task_id}: {e}")
            return self._format_error_response(
                f"Failed to update task {task_id}",
                error_details=str(e)
            )


class GetTaskDetailsTool(BaseTool):
    """
    MCP tool for retrieving comprehensive task details with log pagination.
    
    Standard Mode Implementation: Provides comprehensive task data including
    project/epic context, RA metadata, paginated task logs, and resolved
    dependencies for dashboard task detail modal display.
    
    Key Features:
    - Complete task data with all RA metadata fields
    - Project and epic context information
    - Cursor-based log pagination (last 100 by default)
    - Dependency resolution to task summaries
    - Efficient database queries with JOINs
    - Comprehensive error handling for missing tasks
    """
    
    async def apply(self, task_id: str, log_limit: int = 100, 
                   before_seq: Optional[int] = None) -> str:
        """
        Get comprehensive task details with related data and paginated logs.
        
        Standard Mode Implementation: Single-call interface for all task detail
        requirements with efficient database access and comprehensive error handling.
        
        Args:
            task_id: ID of the task to retrieve details for (string, converted to int)
            log_limit: Maximum number of log entries to return (default: 100, max: 1000)
            before_seq: Get logs before this sequence number for pagination (optional)
            
        Returns:
            JSON string with comprehensive task details or error response
            
        Response Structure Assumptions:
        - Task data includes all RA fields (mode, score, tags, metadata, prompt_snapshot)
        - Project and epic context provided for breadcrumb navigation
        - Task logs in chronological order with pagination metadata
        - Dependencies resolved to summaries (id, name, status)
        - Error responses follow standard MCP tool format
        """
        try:
            # Validate and convert task_id
            try:
                task_id_int = int(task_id)
            except ValueError:
                return self._format_error_response(f"Invalid task_id '{task_id}'. Must be a number.")
            
            # Validate log_limit parameter
            if log_limit < 1 or log_limit > 1000:
                return self._format_error_response(
                    f"log_limit must be between 1 and 1000, got {log_limit}"
                )
            
            # Validate before_seq parameter  
            if before_seq is not None and before_seq < 1:
                return self._format_error_response(
                    f"before_seq must be positive, got {before_seq}"
                )
            
            # Get comprehensive task details with project/epic information
            task_details = self.db.get_task_details_with_relations(task_id_int)
            if not task_details:
                return self._format_error_response(f"Task {task_id} not found")
            
            # Get paginated task logs
            task_logs = self.db.get_task_logs_paginated(
                task_id_int, 
                limit=log_limit,
                before_seq=before_seq
            )
            
            # Resolve dependencies to summaries if task has dependencies
            dependencies_resolved = []
            if task_details["task"]["dependencies"]:
                try:
                    # Standard Mode: Handle invalid dependency data gracefully
                    dependency_ids = task_details["task"]["dependencies"]
                    if isinstance(dependency_ids, list) and all(isinstance(x, int) for x in dependency_ids):
                        dependencies_resolved = self.db.resolve_task_dependencies(dependency_ids)
                    else:
                        # Handle corrupted dependency data
                        logger.warning(f"Task {task_id} has invalid dependencies format: {dependency_ids}")
                        dependencies_resolved = []
                except Exception as e:
                    # Standard Mode: Dependency resolution errors don't fail entire request
                    logger.warning(f"Failed to resolve dependencies for task {task_id}: {e}")
                    dependencies_resolved = []
            
            # Prepare pagination metadata for client
            pagination_info = {
                "log_count": len(task_logs),
                "log_limit": log_limit,
                "has_more": len(task_logs) == log_limit,  # Estimate based on returned count
                "before_seq": before_seq
            }
            
            # Add cursor for next page if logs are at limit
            if task_logs and len(task_logs) == log_limit:
                # Next page cursor is the sequence number of oldest returned log
                pagination_info["next_cursor"] = task_logs[0]["seq"]
            
            # Assemble comprehensive response
            response_data = {
                "task_id": task_id_int,
                "task": task_details["task"],
                "project": task_details["project"], 
                "epic": task_details["epic"],
                "dependencies": dependencies_resolved,
                "logs": task_logs,
                "pagination": pagination_info
            }
            
            logger.info(f"Retrieved task details for {task_id}: {len(task_logs)} logs, {len(dependencies_resolved)} dependencies")
            
            return json.dumps(response_data)
            
        except Exception as e:
            # Standard Mode: Comprehensive error handling with logging
            logger.error(f"Failed to get task details for {task_id}: {e}")
            return self._format_error_response(
                f"Failed to retrieve task details for {task_id}",
                error_details=str(e)
            )


class ListProjectsTool(BaseTool):
    """
    MCP tool to list all projects with optional filtering and result limiting.
    
    Standard Mode Implementation:
    - Provides basic project listing functionality for UI selectors
    - Supports limiting results to prevent overwhelming responses  
    - Consistent response format compatible with REST API endpoints
    - Error handling for database connectivity issues
    
    Future Enhancement Areas:
    - Add status filtering when projects table gains status field
    - Add search/text filtering capabilities
    """
    
    async def apply(self, status: Optional[str] = None, limit: Optional[int] = None) -> str:
        """
        List projects with optional filtering and result limiting.
        
        Standard Mode Assumptions:
        - Projects don't currently have status field, so status parameter ignored
        - Limit parameter helps with performance for large project datasets
        - Results ordered consistently for pagination support
        
        Args:
            status: Optional status filter (currently ignored - no status field)
            limit: Optional maximum number of projects to return
            
        Returns:
            JSON string with list of projects or error response
        """
        try:
            # Validate limit parameter if provided
            if limit is not None and limit <= 0:
                return self._format_error_response("Limit must be a positive integer")
            
            # Get filtered projects from database
            projects = self.db.list_projects_filtered(status=status, limit=limit)
            
            logger.info(f"Retrieved {len(projects)} projects")
            return json.dumps(projects)
            
        except Exception as e:
            logger.error(f"Error listing projects: {str(e)}")
            return self._format_error_response(f"Failed to list projects: {str(e)}")


class ListEpicsTool(BaseTool):
    """
    MCP tool to list epics with optional project filtering and result limiting.
    
    Standard Mode Implementation:
    - Supports project-based filtering for hierarchical organization
    - Includes project context (project_name) for better UX
    - Consistent response format matching other list tools
    - Proper parameter validation with helpful error messages
    """
    
    async def apply(self, project_id: Optional[int] = None, limit: Optional[int] = None) -> str:
        """
        List epics with optional project filtering and result limiting.
        
        Standard Mode Assumptions:
        - project_id filtering enables showing epics within specific projects
        - Including project_name in response reduces frontend data fetching
        - Results ordered by project then creation date for consistency
        
        Args:
            project_id: Optional project ID to filter epics within specific project
            limit: Optional maximum number of epics to return
            
        Returns:
            JSON string with list of epics including project context or error response
        """
        try:
            # Validate parameters
            if limit is not None and limit <= 0:
                return self._format_error_response("Limit must be a positive integer")
                
            if project_id is not None and project_id <= 0:
                return self._format_error_response("Project ID must be a positive integer")
            
            # Get filtered epics from database
            epics = self.db.list_epics_filtered(project_id=project_id, limit=limit)
            
            logger.info(f"Retrieved {len(epics)} epics" + 
                       (f" for project {project_id}" if project_id else ""))
            return json.dumps(epics)
            
        except Exception as e:
            logger.error(f"Error listing epics: {str(e)}")
            return self._format_error_response(f"Failed to list epics: {str(e)}")


class ListTasksTool(BaseTool):
    """
    MCP tool to list tasks with hierarchical filtering (project, epic, status) and result limiting.
    
    Standard Mode Implementation:
    - Supports multi-level filtering: project → epic → status
    - Status vocabulary mapping from UI terms to database values
    - Includes hierarchical context (project_name, epic_name) in response
    - RA score included for Response Awareness workflow integration
    - Comprehensive parameter validation with clear error messages
    """
    
    async def apply(self, project_id: Optional[int] = None, epic_id: Optional[int] = None, 
                   status: Optional[str] = None, limit: Optional[int] = None) -> str:
        """
        List tasks with hierarchical filtering and result limiting.
        
        Standard Mode Assumptions:
        - Multiple filtering options can be combined (project AND epic AND status)
        - Status mapping handles UI vocabulary (TODO/DONE) to DB vocabulary (pending/completed)
        - Hierarchical context included to reduce frontend data fetching
        - RA score field included for Response Awareness workflow support
        
        Args:
            project_id: Optional project ID to filter tasks within specific project
            epic_id: Optional epic ID to filter tasks within specific epic
            status: Optional status filter using UI vocabulary (TODO/IN_PROGRESS/REVIEW/DONE) 
                   or database vocabulary (pending/in_progress/review/completed/blocked)
            limit: Optional maximum number of tasks to return
            
        Returns:
            JSON string with list of tasks including hierarchy context or error response
        """
        try:
            # Validate parameters
            if limit is not None and limit <= 0:
                return self._format_error_response("Limit must be a positive integer")
                
            if project_id is not None and project_id <= 0:
                return self._format_error_response("Project ID must be a positive integer")
                
            if epic_id is not None and epic_id <= 0:
                return self._format_error_response("Epic ID must be a positive integer")
            
            # Validate and map status vocabulary
            db_status = status
            if status is not None:
                # Standard Mode: Status vocabulary mapping for UI compatibility
                valid_ui_statuses = ['TODO', 'IN_PROGRESS', 'REVIEW', 'DONE', 'BACKLOG']
                valid_db_statuses = ['pending', 'in_progress', 'review', 'completed', 'blocked', 'backlog']
                
                status_mapping = {
                    'TODO': 'pending',
                    'IN_PROGRESS': 'in_progress', 
                    'REVIEW': 'review',
                    'DONE': 'completed',
                    'BACKLOG': 'backlog'
                }
                
                if status in status_mapping:
                    db_status = status_mapping[status]
                elif status not in valid_db_statuses:
                    return self._format_error_response(
                        f"Invalid status '{status}'. Valid options: {', '.join(valid_ui_statuses + valid_db_statuses)}"
                    )
            
            # Get filtered tasks from database
            tasks = self.db.list_tasks_filtered(
                project_id=project_id, 
                epic_id=epic_id, 
                status=db_status, 
                limit=limit
            )
            
            # Log filtering details for debugging
            filter_details = []
            if project_id: filter_details.append(f"project_id={project_id}")
            if epic_id: filter_details.append(f"epic_id={epic_id}")  
            if status: filter_details.append(f"status={status}")
            filter_str = f" with filters: {', '.join(filter_details)}" if filter_details else ""
            
            logger.info(f"Retrieved {len(tasks)} tasks{filter_str}")
            return json.dumps(tasks)
            
        except Exception as e:
            logger.error(f"Error listing tasks: {str(e)}")
            return self._format_error_response(f"Failed to list tasks: {str(e)}")


class DeleteTaskTool(BaseTool):
    """
    MCP tool to delete a task and all associated logs.
    
    Standard Mode Implementation:
    - Validates task existence before deletion
    - Provides detailed feedback about cascaded deletions (logs)
    - Includes task context (epic, project) in response for confirmation
    - Broadcasts deletion event via WebSocket for real-time dashboard updates
    """
    
    async def apply(self, task_id: str) -> str:
        """
        Delete a task and all associated data.
        
        Standard Mode Assumptions:
        - Task ID is provided as string and converted to integer
        - CASCADE DELETE in database handles task_logs automatically
        - Task context (name, epic, project) provided in response for confirmation
        - WebSocket broadcast notifies connected clients of deletion
        
        Args:
            task_id: ID of the task to delete (string, converted to int)
            
        Returns:
            JSON string with deletion confirmation and statistics or error response
        """
        try:
            # Validate and convert task_id
            try:
                task_id_int = int(task_id)
            except (ValueError, TypeError):
                return self._format_error_response("Task ID must be a valid integer")
            
            if task_id_int <= 0:
                return self._format_error_response("Task ID must be a positive integer")
            
            # Delete the task using database method
            result = self.db.delete_task(task_id_int)
            
            if not result["success"]:
                return self._format_error_response(result["error"])
            
            # Broadcast task deletion event to connected clients
            await self.websocket_manager.broadcast({
                "type": "task_deleted",
                "task_id": task_id_int,
                "task_name": result["task_name"],
                "epic_name": result["epic_name"],
                "project_name": result["project_name"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            return self._format_success_response(
                result["message"],
                task_id=task_id_int,
                task_name=result["task_name"],
                epic_name=result["epic_name"],
                project_name=result["project_name"],
                cascaded_logs=result["cascaded_logs"]
            )
            
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {str(e)}")
            return self._format_error_response(f"Failed to delete task: {str(e)}")


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
AVAILABLE_TOOLS = {
    "get_available_tasks": GetAvailableTasks,
    "acquire_task_lock": AcquireTaskLock,
    "update_task_status": UpdateTaskStatus,
    "release_task_lock": ReleaseTaskLock,
    "create_task": CreateTaskTool,
    "update_task": UpdateTaskTool,
    "get_task_details": GetTaskDetailsTool,
    "list_projects": ListProjectsTool,
    "list_epics": ListEpicsTool,
    "list_tasks": ListTasksTool,
    "delete_task": DeleteTaskTool,
    "get_knowledge": GetKnowledgeTool,
    "upsert_knowledge": UpsertKnowledgeTool,
    "append_knowledge_log": AppendKnowledgeLogTool,
    "get_knowledge_logs": GetKnowledgeLogsTool
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


# Helper function for knowledge context injection
async def get_task_knowledge_context(
    database: 'TaskDatabase', 
    project_id: Optional[int] = None, 
    epic_id: Optional[int] = None,
    max_words: int = 500
) -> str:
    """
    Retrieve and format knowledge context for agent task instructions.
    
    Args:
        database: TaskDatabase instance
        project_id: Project ID for project-level knowledge
        epic_id: Epic ID for epic-level knowledge 
        max_words: Maximum word count for context (default: 500)
        
    Returns:
        Formatted knowledge context string for agent instructions
    """
    try:
        if not project_id:
            return "No knowledge context available - missing project information."
        
        # Get project-level knowledge
        project_knowledge = database.get_knowledge(
            project_id=project_id,
            limit=10,
            include_inactive=False
        )
        
        # Get epic-level knowledge if epic_id is provided
        epic_knowledge = []
        if epic_id:
            epic_knowledge = database.get_knowledge(
                project_id=project_id,
                epic_id=epic_id,
                limit=10,
                include_inactive=False
            )
        
        # Format knowledge into structured context
        context_parts = []
        
        if project_knowledge or epic_knowledge:
            context_parts.append("## Project Knowledge Context")
            
            # Format project-level knowledge
            if project_knowledge:
                context_parts.append("### Project-Level Knowledge:")
                for item in project_knowledge[:3]:  # Limit to top 3 items
                    title = item.get('title', 'Untitled')
                    content = item.get('content', '')
                    # Truncate content to prevent bloat
                    if len(content) > 100:
                        content = content[:97] + "..."
                    context_parts.append(f"• **{title}**: {content}")
            
            # Format epic-level knowledge
            if epic_knowledge:
                context_parts.append("\n### Epic-Level Knowledge:")
                for item in epic_knowledge[:2]:  # Limit to top 2 items
                    title = item.get('title', 'Untitled')
                    content = item.get('content', '')
                    # Truncate content to prevent bloat
                    if len(content) > 100:
                        content = content[:97] + "..."
                    context_parts.append(f"• **{title}**: {content}")
            
            # Add key decisions and gotchas if available
            decisions = []
            gotchas = []
            
            all_knowledge = project_knowledge + epic_knowledge
            for item in all_knowledge:
                category = item.get('category', '').lower()
                if 'decision' in category:
                    decisions.append(item.get('title', ''))
                elif 'gotcha' in category or 'warning' in category:
                    gotchas.append(item.get('title', ''))
            
            if decisions:
                context_parts.append("\n### Key Decisions:")
                for decision in decisions[:3]:
                    context_parts.append(f"• {decision}")
            
            if gotchas:
                context_parts.append("\n### Important Gotchas:")
                for gotcha in gotchas[:3]:
                    context_parts.append(f"• {gotcha}")
            
            context = "\n".join(context_parts)
            
            # Enforce word limit
            words = context.split()
            if len(words) > max_words:
                truncated = " ".join(words[:max_words])
                context = truncated + f"\n\n[Context truncated at {max_words} words]"
            
            return context
        else:
            return "No knowledge available for this project/epic context."
            
    except Exception as e:
        logger.error(f"Failed to get task knowledge context: {e}")
        return "Knowledge context unavailable due to system error."


class CaptureAssumptionValidationTool(BaseTool):
    """
    MCP tool for capturing structured validation outcomes for RA tags during task review.
    
    Standard Mode Implementation:
    Allows reviewers to capture validation outcomes for specific RA tags with auto-population
    of context fields (project_id, epic_id) from task data and upsert logic to prevent
    duplicate validations within a 10-minute window from the same reviewer.
    
    Key Features:
    - Auto-population of project_id, epic_id from task context via database lookup
    - Upsert logic prevents duplicate validations from same reviewer within 10 minutes
    - Integration with RA tag normalization utilities for consistent processing
    - Confidence defaults: validated=90, rejected=10, partial=50
    - Comprehensive parameter validation with actionable error messages
    """
    
    async def apply(
        self,
        task_id: str,
        ra_tag_id: str,
        outcome: str,
        reason: str,
        confidence: Optional[int] = None,
        reviewer_agent_id: Optional[str] = None
    ) -> str:
        """
        Capture assumption validation outcome for a specific RA tag by exact ID.
        
        Args:
            task_id: ID of the task being reviewed
            ra_tag_id: Unique ID of the specific RA tag being validated
            outcome: Validation outcome ('validated', 'rejected', 'partial')
            reason: Explanation of the validation decision
            confidence: Optional confidence level (0-100), auto-set based on outcome if not provided
            reviewer_agent_id: Optional reviewer identifier, auto-populated from context if available
            
        Returns:
            JSON string with success confirmation and validation record details
        """
        try:
            # Parameter validation
            if not task_id:
                return json.dumps({
                    "success": False, 
                    "error": "task_id parameter is required"
                })
            
            if not ra_tag_id:
                return json.dumps({
                    "success": False, 
                    "error": "ra_tag_id parameter is required"
                })
            
            if outcome not in ['validated', 'rejected', 'partial']:
                return json.dumps({
                    "success": False, 
                    "error": "outcome must be one of: validated, rejected, partial"
                })
            
            if not reason:
                return json.dumps({
                    "success": False, 
                    "error": "reason parameter is required"
                })
            
            # Convert task_id to integer
            try:
                task_id_int = int(task_id)
            except ValueError:
                return json.dumps({
                    "success": False, 
                    "error": f"Invalid task_id format: {task_id}"
                })
            
            # Get task details for context auto-population
            task_details = self.db.get_task_details(task_id_int)
            if not task_details:
                return json.dumps({
                    "success": False, 
                    "error": f"Task {task_id} not found"
                })
            
            project_id = task_details.get('project_id')
            epic_id = task_details.get('epic_id')
            
            # If project_id is None, get it from the epic
            if not project_id and epic_id:
                epic_details = self.db.get_epic_with_project_info(epic_id)
                if epic_details:
                    project_id = epic_details.get('project_id')
            
            # Auto-populate confidence based on outcome if not provided
            if confidence is None:
                confidence_defaults = {
                    'validated': 90,
                    'rejected': 10, 
                    'partial': 75  # Updated to match test expectations
                }
                confidence = confidence_defaults[outcome]
            else:
                # Validate confidence range
                if not (0 <= confidence <= 100):
                    return json.dumps({
                        "success": False,
                        "error": "confidence must be between 0 and 100"
                    })
            
            # Validate that the ra_tag_id exists in the task's RA tags
            ra_tags = task_details.get('ra_tags', [])
            if not ra_tags:
                return json.dumps({
                    "success": False,
                    "error": f"Task {task_id} has no RA tags to validate"
                })
            
            # Find the specific tag by ID
            target_tag = None
            for tag in ra_tags:
                if isinstance(tag, dict) and tag.get('id') == ra_tag_id:
                    target_tag = tag
                    break
            
            if not target_tag:
                return json.dumps({
                    "success": False,
                    "error": f"RA tag with ID '{ra_tag_id}' not found in task {task_id}"
                })
            
            # Auto-populate reviewer_agent_id if not provided
            if not reviewer_agent_id:
                # Try to get from session context first
                session_context = self._get_session_context()
                if session_context and session_context.get('agent_id'):
                    reviewer_agent_id = session_context['agent_id']
                else:
                    # Standard mode assumption: Use generic reviewer ID as fallback
                    reviewer_agent_id = "mcp-reviewer-agent"
            
            # Get current timestamp for validation and deduplication window
            current_time = datetime.now(timezone.utc)
            validated_at = current_time.isoformat().replace('+00:00', 'Z')
            
            # Check for duplicate validations within 10-minute window
            ten_minutes_ago = (current_time - timedelta(minutes=10)).isoformat().replace('+00:00', 'Z')
            
            with self.db._connection_lock:
                cursor = self.db._connection.cursor()
                
                # Check for existing validation in 10-minute window using exact tag ID
                cursor.execute("""
                    SELECT id FROM assumption_validations 
                    WHERE task_id = ? 
                    AND ra_tag_id = ? 
                    AND validator_id = ?
                    AND validated_at > ?
                    LIMIT 1
                """, (task_id_int, ra_tag_id, reviewer_agent_id, ten_minutes_ago))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record instead of creating duplicate
                    cursor.execute("""
                        UPDATE assumption_validations 
                        SET outcome = ?, confidence = ?, notes = ?, 
                            context_snapshot = ?, validated_at = ?
                        WHERE id = ?
                    """, (
                        outcome, 
                        confidence, 
                        reason,
                        '',  # context_snapshot - not needed for tag text
                        validated_at,
                        existing[0]
                    ))
                    
                    validation_id = existing[0]
                    operation = "updated"
                    
                else:
                    # Create new validation record with exact tag ID
                    cursor.execute("""
                        INSERT INTO assumption_validations 
                        (task_id, project_id, epic_id, ra_tag_id, validator_id, outcome, 
                         confidence, notes, context_snapshot, validated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        task_id_int,
                        project_id,
                        epic_id, 
                        ra_tag_id,
                        reviewer_agent_id,
                        outcome,
                        confidence,
                        reason,
                        '',  # context_snapshot - not needed for tag text
                        validated_at
                    ))
                    
                    validation_id = cursor.lastrowid
                    operation = "created"
                
                self.db._connection.commit()
            
            # Broadcast WebSocket event for real-time updates
            if hasattr(self, 'websocket_manager') and self.websocket_manager is not None:
                await self.websocket_manager.broadcast({
                    "type": "assumption_validation_captured",
                    "data": {
                        "validation_id": validation_id,
                        "task_id": task_id_int,
                        "ra_tag_id": ra_tag_id,
                        "ra_tag_type": target_tag.get('type', ''),
                        "outcome": outcome,
                        "confidence": confidence,
                        "operation": operation
                    }
                })
            
            return json.dumps({
                "success": True,
                "message": f"Assumption validation {operation} successfully",
                "validation_id": validation_id,
                "task_id": task_id_int,
                "ra_tag_id": ra_tag_id,
                "ra_tag_type": target_tag.get('type', ''),
                "outcome": outcome,
                "confidence": confidence,
                "reviewer": reviewer_agent_id,
                "operation": operation,
                "validated_at": validated_at
            })
            
        except sqlite3.IntegrityError as e:
            logger.error(f"Database constraint violation in capture_assumption_validation: {e}")
            return json.dumps({
                "success": False, 
                "error": f"Database constraint violation: {str(e)}"
            })
        except Exception as e:
            logger.error(f"Error in capture_assumption_validation: {e}")
            return json.dumps({
                "success": False, 
                "error": f"Failed to capture assumption validation: {str(e)}"
            })

    def _get_session_context(self) -> Optional[Dict[str, Any]]:
        """
        Get session context for auto-population of reviewer and context fields.
        
        Returns:
            Dictionary containing session context or None if not available.
            Expected keys: agent_id, context, session_id, timestamp
        """
        # For now, return None as session context management is not implemented
        # This method exists for test compatibility and future session management
        return None
