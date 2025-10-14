"""
Projects Router

Provides project-related endpoints including listing and deletion.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..database import TaskDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["projects"])


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


@router.get("/projects")
async def list_projects_endpoint(
    status: Optional[str] = None,
    limit: Optional[int] = None,
    db: TaskDatabase = Depends(get_database)
):
    """
    List all projects with optional filtering and result limiting.

    Standard Mode Implementation:
    - Mirrors list_projects MCP tool functionality for REST API access
    - Enables frontend UI to populate project selectors and filters
    - Consistent response format with MCP tool output

    Args:
        status: Optional status filter (currently ignored - projects have no status field)
        limit: Optional maximum number of projects to return

    Returns:
        JSON list of projects with id, name, description, created_at, updated_at
    """
    try:
        # Validate limit parameter
        if limit is not None and limit <= 0:
            raise HTTPException(status_code=400, detail="Limit must be a positive integer")

        # Get filtered projects from database using same method as MCP tool
        projects = db.list_projects_filtered(status=status, limit=limit)

        logger.info(f"REST API: Retrieved {len(projects)} projects")
        return projects

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve projects")


@router.get("/projects/{project_id}/epics")
async def list_epics_for_project_endpoint(
    project_id: int,
    limit: Optional[int] = None,
    db: TaskDatabase = Depends(get_database)
):
    """
    List epics within a specific project with optional result limiting.

    Standard Mode Implementation:
    - Provides hierarchical filtering for epics within specific projects
    - Mirrors list_epics MCP tool with project_id filtering
    - Useful for frontend UI epic selectors when project is selected

    Args:
        project_id: Project ID to filter epics within specific project
        limit: Optional maximum number of epics to return

    Returns:
        JSON list of epics with id, name, description, project_id, project_name, created_at
    """
    try:
        # Validate parameters
        if project_id <= 0:
            raise HTTPException(status_code=400, detail="Project ID must be a positive integer")

        if limit is not None and limit <= 0:
            raise HTTPException(status_code=400, detail="Limit must be a positive integer")

        # Get filtered epics using same method as MCP tool
        epics = db.list_epics_filtered(project_id=project_id, limit=limit)

        logger.info(f"REST API: Retrieved {len(epics)} epics for project {project_id}")
        return epics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list epics for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve epics")


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    db: TaskDatabase = Depends(get_database),
    conn_mgr = Depends(get_connection_manager)
):
    """
    Delete a project and all associated epics and tasks.

    Args:
        project_id: ID of the project to delete

    Returns:
        JSON response with success status and cascade deletion information
    """
    try:
        result = db.delete_project(project_id)

        if result["success"]:
            # Log the deletion for debugging
            remaining_tasks = db.get_all_tasks()
            remaining_epics = db.get_all_epics()
            remaining_projects = db.get_all_projects()
            logger.info(f"After project deletion: {len(remaining_projects)} projects, {len(remaining_epics)} epics, {len(remaining_tasks)} tasks remaining")
            # Broadcast deletion event to all WebSocket clients
            await conn_mgr.broadcast({
                "type": "project_deleted",
                "project_id": project_id,
                "project_name": result["project_name"],
                "cascaded_epics": result["cascaded_epics"],
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
        logger.error(f"Failed to delete project {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete project: {str(e)}"
        )
