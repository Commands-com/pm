"""
Epics Router

Provides epic-related endpoints including listing and deletion.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..database import TaskDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["epics"])


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


@router.get("/epics")
async def list_all_epics_endpoint(
    project_id: Optional[int] = None,
    limit: Optional[int] = None,
    db: TaskDatabase = Depends(get_database)
):
    """
    List all epics with optional project filtering and result limiting.

    Standard Mode Implementation:
    - Mirrors list_epics MCP tool functionality exactly for REST API access
    - Supports optional project filtering like MCP tool
    - Consistent with MCP tool response format

    Args:
        project_id: Optional project ID to filter epics within specific project
        limit: Optional maximum number of epics to return

    Returns:
        JSON list of epics with id, name, description, project_id, project_name, created_at
    """
    try:
        # Validate parameters
        if project_id is not None and project_id <= 0:
            raise HTTPException(status_code=400, detail="Project ID must be a positive integer")

        if limit is not None and limit <= 0:
            raise HTTPException(status_code=400, detail="Limit must be a positive integer")

        # Get filtered epics using same method as MCP tool
        epics = db.list_epics_filtered(project_id=project_id, limit=limit)

        filter_str = f" for project {project_id}" if project_id else ""
        logger.info(f"REST API: Retrieved {len(epics)} epics{filter_str}")
        return epics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list epics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve epics")


@router.delete("/epics/{epic_id}")
async def delete_epic(
    epic_id: int,
    db: TaskDatabase = Depends(get_database),
    conn_mgr = Depends(get_connection_manager)
):
    """
    Delete an epic and all associated tasks.

    Args:
        epic_id: ID of the epic to delete

    Returns:
        JSON response with success status and cascade deletion information
    """
    try:
        result = db.delete_epic(epic_id)

        if result["success"]:
            # Log the deletion for debugging
            remaining_tasks = db.get_all_tasks()
            remaining_epics = db.get_all_epics()
            logger.info(f"After epic deletion: {len(remaining_epics)} epics, {len(remaining_tasks)} tasks remaining")
            # Broadcast deletion event to all WebSocket clients
            await conn_mgr.broadcast({
                "type": "epic_deleted",
                "epic_id": epic_id,
                "epic_name": result["epic_name"],
                "project_name": result["project_name"],
                "cascaded_tasks": result["cascaded_tasks"],
                "message": result["message"],
                "timestamp": datetime.now(timezone.utc).isoformat() + 'Z'
            })

            return JSONResponse(
                status_code=200,
                content=result
            )
        else:
            return JSONResponse(
                status_code=404,
                content=result
            )

    except Exception as e:
        logger.error(f"Failed to delete epic {epic_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete epic: {str(e)}"
        )
