"""
Tasks Router

Provides all task-related endpoints including status updates, locking,
details retrieval, filtering, and deletion.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from ..database import TaskDatabase
from ..monitoring import performance_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tasks"])


class TaskStatusUpdate(BaseModel):
    """Request model for task status updates with validation."""
    status: str
    agent_id: str

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate task status values."""
        # Accept both API/DB and UI vocabulary
        valid_statuses = [
            'pending', 'in_progress', 'completed', 'blocked', 'backlog',
            'TODO', 'IN_PROGRESS', 'DONE', 'REVIEW', 'BACKLOG'
        ]
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v

    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        """Validate agent ID format."""
        if not v or not v.strip():
            raise ValueError('Agent ID cannot be empty')
        return v.strip()


class TaskStatusResponse(BaseModel):
    """Response model for task status update operations."""
    success: bool
    status: Optional[str] = None
    error: Optional[str] = None


class TaskDetailsRequest(BaseModel):
    """Request model for task details with optional pagination."""
    task_id: str
    log_limit: Optional[int] = 100
    before_seq: Optional[int] = None

    @field_validator('log_limit')
    @classmethod
    def validate_log_limit(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 1000):
            raise ValueError('log_limit must be between 1 and 1000')
        return v

    @field_validator('before_seq')
    @classmethod
    def validate_before_seq(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError('before_seq must be positive')
        return v


def get_database() -> TaskDatabase:
    """FastAPI dependency to provide database instance."""
    from ..api import db_instance

    if db_instance is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return db_instance


def get_connection_manager():
    """FastAPI dependency to provide connection manager instance."""
    from ..api import connection_manager
    return connection_manager


@router.post("/task/{task_id}/status", response_model=TaskStatusResponse)
async def update_task_status(
    task_id: int,
    update: TaskStatusUpdate,
    db: TaskDatabase = Depends(get_database),
    conn_mgr = Depends(get_connection_manager)
):
    """
    Update task status with atomic lock validation.

    Validates that the requesting agent holds the lock on the task before
    allowing status updates. Broadcasts status change events via WebSocket
    to all connected clients.

    Args:
        task_id: ID of task to update
        update: TaskStatusUpdate with new status and agent_id

    Returns:
        TaskStatusResponse: Success status and new task status

    Raises:
        HTTPException: 400 for validation errors, 403 for lock violations, 500 for database errors
    """
    try:
        # Map UI vocabulary to database vocabulary
        status_mapping = {
            'TODO': 'pending',
            'IN_PROGRESS': 'in_progress',
            'DONE': 'completed',
            'REVIEW': 'review',
            'BACKLOG': 'backlog'
        }
        db_status = status_mapping.get(update.status, update.status)

        # Proactively clear any expired locks (best-effort); do not auto-acquire here
        try:
            expired_ids = db.cleanup_expired_locks_with_ids()
            for eid in expired_ids:
                await conn_mgr.optimized_broadcast({
                    "type": "task.unlocked",
                    "task_id": eid,
                    "agent_id": None,
                    "reason": "lock_expired"
                })
        except Exception:
            pass

        # Auto-acquire a short-lived lock if task is not locked to allow single-call updates
        auto_locked = False
        current_lock = db.get_task_lock_status(task_id)
        if "error" in current_lock:
            raise HTTPException(status_code=404, detail="Task not found")

        if current_lock["is_locked"] and current_lock["lock_holder"] != update.agent_id:
            raise HTTPException(status_code=403, detail="Task is locked by another agent")

        if not current_lock["is_locked"]:
            if db.acquire_task_lock_atomic(task_id, update.agent_id, 60):
                auto_locked = True
            else:
                raise HTTPException(status_code=409, detail="Failed to acquire lock for update")

        # Validate task exists and update status with lock validation
        result = db.update_task_status(task_id, db_status, update.agent_id)

        if result["success"]:
            # Broadcast status change event to all WebSocket clients using optimized broadcasting
            await conn_mgr.optimized_broadcast({
                "type": "task.status_changed",
                "task_id": task_id,
                # Broadcast UI vocabulary understood by the dashboard
                "status": update.status if update.status in status_mapping else update.status,
                "agent_id": update.agent_id
            })

            # Release the auto-acquired lock immediately (UI should not hold locks)
            if auto_locked:
                try:
                    if db.release_lock(task_id, update.agent_id):
                        await conn_mgr.optimized_broadcast({
                            "type": "task.unlocked",
                            "task_id": task_id,
                            "agent_id": update.agent_id,
                            "reason": "auto_release_after_update"
                        })
                except Exception:
                    # Non-fatal: avoid blocking HTTP response on release/broadcast failures
                    pass

            logger.info(f"Task {task_id} status updated to {update.status} by {update.agent_id}")

            return TaskStatusResponse(
                success=True,
                status=result["status"]
            )
        else:
            # Handle validation errors
            error_msg = result.get("error", "Unknown error")

            if "not found" in error_msg.lower():
                raise HTTPException(status_code=404, detail=error_msg)
            elif "must be locked" in error_msg.lower():
                # Fallback: expose as 409 conflict to hint at lock state
                raise HTTPException(status_code=409, detail=error_msg)
            else:
                raise HTTPException(status_code=400, detail=error_msg)

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Failed to update task {task_id} status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update task status")


@router.post("/task/{task_id}/lock")
async def acquire_task_lock(
    task_id: int,
    request: Dict[str, Any],
    db: TaskDatabase = Depends(get_database),
    conn_mgr = Depends(get_connection_manager)
):
    """
    Acquire lock on a task for exclusive access.

    Allows agents to acquire locks on tasks before making updates.
    Broadcasts lock acquisition events to WebSocket clients.
    """
    try:
        agent_id = request.get("agent_id")
        duration = request.get("duration_seconds", 300)  # 5 minute default

        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id required")

        # Clear any expired locks system-wide and broadcast unlocks
        try:
            expired_ids = db.cleanup_expired_locks_with_ids()
            for eid in expired_ids:
                await conn_mgr.optimized_broadcast({
                    "type": "task.unlocked",
                    "task_id": eid,
                    "agent_id": None,
                    "reason": "lock_expired"
                })
        except Exception:
            pass

        # Attempt to acquire lock
        success = db.acquire_task_lock_atomic(task_id, agent_id, duration)

        if success:
            # Broadcast lock acquisition event using optimized broadcasting
            await conn_mgr.optimized_broadcast({
                "type": "task.locked",
                "task_id": task_id,
                "agent_id": agent_id
            })

            # Record lock acquisition for monitoring
            performance_monitor.increment_daily_stat('locks_acquired')

            logger.info(f"Task {task_id} locked by {agent_id}")
            return {"success": True, "agent_id": agent_id}
        else:
            # Lock acquisition failed (already locked)
            lock_status = db.get_task_lock_status(task_id)
            raise HTTPException(
                status_code=409,
                detail=f"Task already locked by {lock_status.get('lock_holder')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acquire lock on task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to acquire task lock")


@router.delete("/task/{task_id}/lock")
async def release_task_lock(
    task_id: int,
    request: Dict[str, str],
    db: TaskDatabase = Depends(get_database),
    conn_mgr = Depends(get_connection_manager)
):
    """
    Release lock on a task.

    Allows agents to release locks when finished with tasks.
    Broadcasts lock release events to WebSocket clients.
    """
    try:
        agent_id = request.get("agent_id")

        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id required")

        # Attempt to release lock
        success = db.release_lock(task_id, agent_id)

        if success:
            # Broadcast lock release event using optimized broadcasting
            await conn_mgr.optimized_broadcast({
                "type": "task.unlocked",
                "task_id": task_id,
                "agent_id": agent_id
            })

            logger.info(f"Task {task_id} unlocked by {agent_id}")
            return {"success": True}
        else:
            raise HTTPException(
                status_code=403,
                detail="Agent does not hold lock on this task"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to release lock on task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to release task lock")


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    db: TaskDatabase = Depends(get_database),
    conn_mgr = Depends(get_connection_manager)
):
    """
    Delete a task and all associated logs via CASCADE DELETE.

    Args:
        task_id: ID of the task to delete

    Returns:
        JSON response with deletion confirmation and statistics
    """
    try:
        from datetime import datetime, timezone

        result = db.delete_task(task_id)

        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=result["error"]
            )

        # Broadcast task deletion event to connected clients
        await conn_mgr.broadcast({
            "type": "task_deleted",
            "task_id": task_id,
            "task_name": result["task_name"],
            "epic_name": result["epic_name"],
            "project_name": result["project_name"],
            "timestamp": datetime.now(timezone.utc).isoformat() + 'Z'
        })

        return JSONResponse(
            status_code=200,
            content=result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete task: {str(e)}"
        )


@router.post("/task/details")
async def get_task_details_endpoint(
    request: TaskDetailsRequest,
    db: TaskDatabase = Depends(get_database)
):
    """
    Get comprehensive task details with RA metadata, logs, and dependencies.

    RA-Light Mode Implementation: Provides complete task detail modal data by calling
    the get_task_details MCP tool internally and returning the comprehensive results.
    This endpoint bridges the gap between frontend REST API expectations and MCP tool
    functionality, ensuring consistent data format and comprehensive RA information.

    Args:
        request: TaskDetailsRequest with task_id, optional log_limit and before_seq

    Returns:
        JSON response containing MCP tool result or error information

    Response Structure:
        - success case: {"result": "<JSON string with comprehensive task details>"}
        - error case: {"error": {"message": "error description", "details": "..."}}
    """
    try:
        # Import the MCP tool here to avoid circular imports
        from ..tools_lib import GetTaskDetailsTool

        # Create tool instance with database dependency
        task_details_tool = GetTaskDetailsTool(db, None)  # No websocket manager needed for readonly

        # Call the MCP tool with provided parameters
        result = await task_details_tool.apply(
            task_id=request.task_id,
            log_limit=request.log_limit or 100,
            before_seq=request.before_seq
        )

        # MCP tool returns JSON string, but we need to check if it contains error info
        try:
            # Try to parse the result to check for internal MCP tool errors
            parsed_result = json.loads(result)
            if isinstance(parsed_result, dict) and 'error' in parsed_result:
                # MCP tool returned an error response
                return JSONResponse(
                    status_code=400,
                    content={"error": parsed_result['error']}
                )
        except json.JSONDecodeError:
            # If result is not valid JSON, treat as error
            return JSONResponse(
                status_code=500,
                content={"error": {"message": "Invalid response from task details service"}}
            )

        # Return successful result in FastAPI-compatible format
        logger.info(f"REST API: Retrieved comprehensive details for task {request.task_id}")
        return JSONResponse(content={"result": result})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task details for {request.task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Failed to retrieve task details",
                    "details": str(e)
                }
            }
        )


@router.get("/tasks/filtered")
async def list_tasks_filtered_endpoint(
    project_id: Optional[int] = None,
    epic_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    db: TaskDatabase = Depends(get_database)
):
    """
    List tasks with hierarchical filtering (project, epic, status) and result limiting.

    Standard Mode Implementation:
    - Mirrors list_tasks MCP tool functionality exactly for REST API access
    - Supports all filtering options: project_id, epic_id, status
    - Status vocabulary mapping consistent with MCP tool (UI terms to DB values)
    - Includes hierarchical context (project_name, epic_name) in response

    Args:
        project_id: Optional project ID to filter tasks within specific project
        epic_id: Optional epic ID to filter tasks within specific epic
        status: Optional status filter (UI: TODO/IN_PROGRESS/REVIEW/DONE or DB: pending/in_progress/review/completed/blocked)
        limit: Optional maximum number of tasks to return

    Returns:
        JSON list of tasks with id, name, status, ra_score, epic_name, project_name
    """
    try:
        # Validate parameters (same validation as MCP tool)
        if project_id is not None and project_id <= 0:
            raise HTTPException(status_code=400, detail="Project ID must be a positive integer")

        if epic_id is not None and epic_id <= 0:
            raise HTTPException(status_code=400, detail="Epic ID must be a positive integer")

        if limit is not None and limit <= 0:
            raise HTTPException(status_code=400, detail="Limit must be a positive integer")

        # Validate and map status vocabulary (same as MCP tool)
        db_status = status
        if status is not None:
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
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status '{status}'. Valid options: {', '.join(valid_ui_statuses + valid_db_statuses)}"
                )

        # Get filtered tasks using same method as MCP tool
        tasks = db.list_tasks_filtered(
            project_id=project_id,
            epic_id=epic_id,
            status=db_status,
            limit=limit
        )

        # Log filtering details for debugging (same as MCP tool)
        filter_details = []
        if project_id: filter_details.append(f"project_id={project_id}")
        if epic_id: filter_details.append(f"epic_id={epic_id}")
        if status: filter_details.append(f"status={status}")
        filter_str = f" with filters: {', '.join(filter_details)}" if filter_details else ""

        logger.info(f"REST API: Retrieved {len(tasks)} tasks{filter_str}")
        return tasks

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tasks")
