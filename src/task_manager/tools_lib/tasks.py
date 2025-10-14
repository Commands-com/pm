"""
Task-related MCP tools.

Provides tools for task management operations including retrieval, locking,
status updates, creation, updates, and deletion.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from .base import BaseTool
from ..database import TaskDatabase
from ..api import ConnectionManager
from ..ra_instructions import ra_instructions_manager

# Configure logging for task tool operations
logger = logging.getLogger(__name__)

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
            # Convert ra_score from string to int if provided (MCP compatibility)
            if ra_score is not None:
                try:
                    ra_score = int(ra_score)
                    if ra_score < 1 or ra_score > 10:
                        return self._format_error_response(
                            "ra_score must be between 1 and 10 if provided"
                        )
                except (ValueError, TypeError):
                    return self._format_error_response(
                        "ra_score must be a valid integer between 1 and 10"
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
            from ..api import generate_enriched_task_payload, extract_session_id
            
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
            # Convert ra_score from string to int if provided (MCP compatibility)
            if ra_score is not None:
                try:
                    ra_score = int(ra_score)
                    if ra_score < 1 or ra_score > 10:
                        return self._format_error_response("ra_score must be between 1 and 10")
                except (ValueError, TypeError):
                    return self._format_error_response(
                        "ra_score must be a valid integer between 1 and 10"
                    )
            
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
                from ..api import generate_enriched_task_payload, extract_session_id
                
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
                        from ..api import generate_logs_appended_payload
                        
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


