"""
Knowledge Management API Router

Provides REST endpoints for knowledge item CRUD operations, logging,
and hierarchical knowledge retrieval by project/epic scope.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..database import TaskDatabase
from ..models import (
    KnowledgeRequest, KnowledgeResponse, LogRequest, LogResponse,
    KnowledgeDetailResponse, create_error_response
)

logger = logging.getLogger(__name__)

# Create API router for knowledge management endpoints
router = APIRouter(
    prefix="/api/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
)


def get_database():
    """Dependency to get database instance - will be overridden by main app."""
    from ..api import db_instance
    if db_instance is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database not available")
    return db_instance


def get_connection_manager():
    """Dependency to get connection manager instance - will be overridden by main app."""
    from ..api import connection_manager
    return connection_manager


@router.get("/{knowledge_id}/logs")
async def get_knowledge_logs(
    knowledge_id: int,
    limit: Optional[int] = 50,
    action_type: Optional[str] = None,
    db: TaskDatabase = Depends(get_database)
):
    """
    Get log entries for a knowledge item.

    Args:
        knowledge_id: ID of knowledge item to get logs for
        limit: Maximum number of log entries to return (default: 50)
        action_type: Filter by specific action type (optional)

    Returns:
        JSON response with log entries
    """
    try:
        # Validate knowledge_id
        if knowledge_id <= 0:
            return JSONResponse(
                status_code=400,
                content=create_error_response("Knowledge ID must be a positive integer")
            )

        # Fetch logs from database
        logs = db.get_knowledge_logs(knowledge_id, limit, action_type)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "knowledge_id": knowledge_id,
                "logs": logs,
                "count": len(logs),
                "filters": {
                    "limit": limit,
                    "action_type": action_type
                }
            }
        )

    except Exception as e:
        logger.error(f"Failed to get logs for knowledge {knowledge_id}: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response("Failed to retrieve knowledge logs")
        )


@router.post("/{knowledge_id}/logs", response_model=LogResponse)
async def append_knowledge_log(
    knowledge_id: int,
    log_entry: LogRequest,
    db: TaskDatabase = Depends(get_database)
):
    """
    Append log entry to knowledge item history.

    Args:
        knowledge_id: ID of knowledge item to log to
        log_entry: LogRequest with log entry data

    Returns:
        LogResponse with log operation result
    """
    try:
        # Validate knowledge_id
        if knowledge_id <= 0:
            return JSONResponse(
                status_code=400,
                content=create_error_response("Knowledge ID must be a positive integer")
            )

        # Import and use the AppendKnowledgeLogTool
        from ..tools_lib import AppendKnowledgeLogTool

        connection_manager = get_connection_manager()
        log_tool = AppendKnowledgeLogTool(db, connection_manager)

        # Convert metadata to JSON string if provided
        metadata_json = None
        if log_entry.metadata is not None:
            metadata_json = json.dumps(log_entry.metadata)

        # Call the MCP tool to append log entry
        result = await log_tool.apply(
            knowledge_id=str(knowledge_id),
            action_type=log_entry.action_type,
            change_reason=log_entry.change_reason,
            created_by=log_entry.created_by,
            metadata=metadata_json
        )

        # Parse the JSON result from the MCP tool
        try:
            parsed_result = json.loads(result)

            if parsed_result.get("success", False):
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": parsed_result.get("message", "Log entry added"),
                        "log_id": parsed_result.get("log_id"),
                        "knowledge_id": parsed_result.get("knowledge_id"),
                        "knowledge_title": parsed_result.get("knowledge_title"),
                        "created_at": parsed_result.get("created_at")
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content=create_error_response(
                        parsed_result.get("error", "Failed to add log entry")
                    )
                )
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from AppendKnowledgeLogTool: {result}")
            return JSONResponse(
                status_code=500,
                content=create_error_response("Invalid response from knowledge service")
            )

    except Exception as e:
        logger.error(f"Failed to append log to knowledge {knowledge_id}: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response("Failed to add log entry")
        )


@router.get("/project/{project_id}", response_model=KnowledgeDetailResponse)
async def get_knowledge_for_project(
    project_id: int,
    logs_limit: Optional[int] = 10,
    db: TaskDatabase = Depends(get_database)
):
    """
    Get knowledge items for project scope with optional logs.

    Args:
        project_id: Project ID to filter knowledge items
        logs_limit: Maximum number of log entries to return (default: 10)

    Returns:
        KnowledgeDetailResponse with knowledge items and logs
    """
    try:
        # Validate project_id
        if project_id <= 0:
            return JSONResponse(
                status_code=400,
                content=create_error_response("Project ID must be a positive integer")
            )

        # Import and use the GetKnowledgeTool
        from ..tools_lib import GetKnowledgeTool

        connection_manager = get_connection_manager()
        knowledge_tool = GetKnowledgeTool(db, connection_manager)

        # Call the MCP tool to get knowledge items
        result = await knowledge_tool.apply(
            project_id=str(project_id),
            limit=str(logs_limit) if logs_limit else None
        )

        # Parse the JSON result from the MCP tool
        try:
            parsed_result = json.loads(result)

            if parsed_result.get("success", False):
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": parsed_result.get("message", "Knowledge items retrieved"),
                        "knowledge_items": parsed_result.get("knowledge_items", []),
                        "total_count": parsed_result.get("total_count", 0),
                        "filters_applied": parsed_result.get("filters_applied", {}),
                        "logs": []  # Logs would need separate endpoint call
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content=create_error_response(
                        parsed_result.get("error", "Failed to retrieve knowledge items")
                    )
                )
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from GetKnowledgeTool: {result}")
            return JSONResponse(
                status_code=500,
                content=create_error_response("Invalid response from knowledge service")
            )

    except Exception as e:
        logger.error(f"Failed to get knowledge for project {project_id}: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response("Failed to retrieve knowledge items")
        )


@router.get("/project/{project_id}/epic/{epic_id}", response_model=KnowledgeDetailResponse)
async def get_knowledge_for_epic(
    project_id: int,
    epic_id: int,
    logs_limit: Optional[int] = 10,
    db: TaskDatabase = Depends(get_database)
):
    """
    Get knowledge items for epic scope with optional logs.

    Args:
        project_id: Project ID for context validation
        epic_id: Epic ID to filter knowledge items
        logs_limit: Maximum number of log entries to return (default: 10)

    Returns:
        KnowledgeDetailResponse with knowledge items and logs
    """
    try:
        # Validate IDs
        if project_id <= 0 or epic_id <= 0:
            return JSONResponse(
                status_code=400,
                content=create_error_response("Project ID and Epic ID must be positive integers")
            )

        # Import and use the GetKnowledgeTool
        from ..tools_lib import GetKnowledgeTool

        connection_manager = get_connection_manager()
        knowledge_tool = GetKnowledgeTool(db, connection_manager)

        # Call the MCP tool to get knowledge items
        result = await knowledge_tool.apply(
            project_id=str(project_id),
            epic_id=str(epic_id),
            limit=str(logs_limit) if logs_limit else None
        )

        # Parse the JSON result from the MCP tool
        try:
            parsed_result = json.loads(result)

            if parsed_result.get("success", False):
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": parsed_result.get("message", "Knowledge items retrieved"),
                        "knowledge_items": parsed_result.get("knowledge_items", []),
                        "total_count": parsed_result.get("total_count", 0),
                        "filters_applied": parsed_result.get("filters_applied", {}),
                        "logs": []  # Logs would need separate endpoint call
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content=create_error_response(
                        parsed_result.get("error", "Failed to retrieve knowledge items")
                    )
                )
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from GetKnowledgeTool: {result}")
            return JSONResponse(
                status_code=500,
                content=create_error_response("Invalid response from knowledge service")
            )

    except Exception as e:
        logger.error(f"Failed to get knowledge for epic {epic_id}: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response("Failed to retrieve knowledge items")
        )


@router.put("", response_model=KnowledgeResponse)
async def upsert_knowledge(
    knowledge: KnowledgeRequest,
    db: TaskDatabase = Depends(get_database)
):
    """
    Create or update knowledge items with validation.

    Args:
        knowledge: KnowledgeRequest with knowledge item data

    Returns:
        KnowledgeResponse with operation result
    """
    try:
        # Import and use the UpsertKnowledgeTool
        from ..tools_lib import UpsertKnowledgeTool

        connection_manager = get_connection_manager()
        upsert_tool = UpsertKnowledgeTool(db, connection_manager)

        # Convert tags and metadata to JSON strings if provided
        tags_json = None
        if knowledge.tags is not None:
            tags_json = json.dumps(knowledge.tags)

        metadata_json = None
        if knowledge.metadata is not None:
            metadata_json = json.dumps(knowledge.metadata)

        # Call the MCP tool to upsert knowledge item
        result = await upsert_tool.apply(
            knowledge_id=str(knowledge.knowledge_id) if knowledge.knowledge_id else None,
            title=knowledge.title,
            content=knowledge.content,
            category=knowledge.category,
            tags=tags_json,
            parent_id=str(knowledge.parent_id) if knowledge.parent_id else None,
            project_id=str(knowledge.project_id) if knowledge.project_id else None,
            epic_id=str(knowledge.epic_id) if knowledge.epic_id else None,
            task_id=str(knowledge.task_id) if knowledge.task_id else None,
            priority=str(knowledge.priority) if knowledge.priority is not None else None,
            is_active=str(knowledge.is_active) if knowledge.is_active is not None else None,
            created_by=knowledge.created_by,
            metadata=metadata_json
        )

        # Parse the JSON result from the MCP tool
        try:
            parsed_result = json.loads(result)

            if parsed_result.get("success", False):
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": parsed_result.get("message", "Knowledge item processed"),
                        "knowledge_id": parsed_result.get("knowledge_id"),
                        "operation": parsed_result.get("operation"),
                        "knowledge_item": parsed_result.get("knowledge_item")
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content=create_error_response(
                        parsed_result.get("error", "Failed to process knowledge item")
                    )
                )
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from UpsertKnowledgeTool: {result}")
            return JSONResponse(
                status_code=500,
                content=create_error_response("Invalid response from knowledge service")
            )

    except Exception as e:
        logger.error(f"Failed to upsert knowledge item: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response("Failed to process knowledge item")
        )


@router.delete("/{knowledge_id}")
async def delete_knowledge_item(
    knowledge_id: int,
    db: TaskDatabase = Depends(get_database)
):
    """
    Delete a knowledge item by ID.

    Args:
        knowledge_id: ID of knowledge item to delete

    Returns:
        JSON response with success status
    """
    try:
        # Validate knowledge_id
        if knowledge_id <= 0:
            return JSONResponse(
                status_code=400,
                content=create_error_response("Knowledge ID must be a positive integer")
            )

        # Delete from database
        result = db.delete_knowledge_item(knowledge_id)

        if result:
            # Broadcast deletion event via WebSocket
            connection_manager = get_connection_manager()
            await connection_manager.broadcast({
                "event_type": "knowledge_deleted",
                "knowledge_id": knowledge_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Knowledge item {knowledge_id} deleted successfully"
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content=create_error_response(f"Knowledge item {knowledge_id} not found")
            )

    except Exception as e:
        logger.error(f"Failed to delete knowledge item {knowledge_id}: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response("Failed to delete knowledge item")
        )
