"""
Planning Mode API Router

Provides REST endpoints for planning mode file management, archive operations,
and WebSocket support for real-time file updates.
"""

import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse

from ..models import create_error_response

logger = logging.getLogger(__name__)

# Create API router for planning mode endpoints
router = APIRouter(
    prefix="/api/planning",
    tags=["planning"],
    responses={404: {"description": "Not found"}},
)


def get_connection_manager():
    """Dependency to get connection manager instance - will be overridden by main app."""
    from ..api import connection_manager
    return connection_manager


@router.get("/files")
async def list_planning_files():
    """
    List all PRD and Epic markdown files from the .pm directory.

    Returns:
        JSON response with PRDs and Epics file lists
    """
    try:
        pm_dir = Path(".pm")
        if not pm_dir.exists():
            return JSONResponse(
                status_code=404,
                content=create_error_response(".pm directory not found")
            )

        # Get PRD files
        prds_dir = pm_dir / "prds"
        prd_files = []
        if prds_dir.exists():
            for file_path in prds_dir.glob("*.md"):
                stat = file_path.stat()
                prd_files.append({
                    "name": file_path.stem,
                    "filename": file_path.name,
                    "path": str(file_path),
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "size": stat.st_size
                })

        # Get Epic files
        epics_dir = pm_dir / "epics"
        epic_files = []
        if epics_dir.exists():
            for file_path in epics_dir.glob("*.md"):
                stat = file_path.stat()
                epic_files.append({
                    "name": file_path.stem,
                    "filename": file_path.name,
                    "path": str(file_path),
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "size": stat.st_size
                })

        # Sort by name
        prd_files.sort(key=lambda x: x["name"])
        epic_files.sort(key=lambda x: x["name"])

        # Get task files
        tasks_dir = Path(".pm/tasks")
        task_files = []
        if tasks_dir.exists():
            for file_path in tasks_dir.glob("*.md"):
                stat = file_path.stat()
                task_files.append({
                    "name": file_path.stem,
                    "filename": file_path.name,
                    "path": str(file_path),
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "size": stat.st_size
                })

        # Sort by name
        task_files.sort(key=lambda x: x["name"])

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "prds": prd_files,
                "epics": epic_files,
                "tasks": task_files,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    except Exception as e:
        logger.error(f"Failed to list planning files: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response("Failed to list planning files")
        )


@router.get("/file/{file_type}/{filename}")
async def get_planning_file(file_type: str, filename: str):
    """
    Get the content of a specific PRD, Epic, or Task markdown file.

    Args:
        file_type: Either 'prds', 'epics', or 'tasks'
        filename: Name of the markdown file (with or without .md extension)

    Returns:
        JSON response with file content and metadata
    """
    try:
        # Validate file type
        if file_type not in ["prds", "epics", "tasks"]:
            return JSONResponse(
                status_code=400,
                content=create_error_response("File type must be 'prds', 'epics', or 'tasks'")
            )

        # Ensure filename has .md extension
        if not filename.endswith('.md'):
            filename += '.md'

        # Construct file path
        file_path = Path(".pm") / file_type / filename

        if not file_path.exists():
            return JSONResponse(
                status_code=404,
                content=create_error_response(f"File {filename} not found in {file_type}")
            )

        # Read file content
        content = file_path.read_text(encoding='utf-8')
        stat = file_path.stat()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "filename": filename,
                "type": file_type.rstrip('s'),  # 'prds' -> 'prd', 'epics' -> 'epic'
                "content": content,
                "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "size": stat.st_size,
                "path": str(file_path)
            }
        )

    except Exception as e:
        logger.error(f"Failed to read planning file {file_type}/{filename}: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response("Failed to read planning file")
        )


@router.get("/archive/files")
async def list_archived_planning_files():
    """
    List all archived PRD and Epic markdown files from the .pm/archive directory.

    Returns:
        JSON response with archived PRDs and Epics file lists
    """
    try:
        archive_dir = Path(".pm/archive")
        if not archive_dir.exists():
            # Return empty lists if archive directory doesn't exist yet
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "prds": [],
                    "epics": [],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

        # Get archived PRD files
        prds_dir = archive_dir / "prds"
        prd_files = []
        if prds_dir.exists():
            for file_path in prds_dir.glob("*.md"):
                stat = file_path.stat()
                prd_files.append({
                    "name": file_path.stem,
                    "filename": file_path.name,
                    "path": str(file_path),
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "size": stat.st_size
                })

        # Get archived Epic files
        epics_dir = archive_dir / "epics"
        epic_files = []
        if epics_dir.exists():
            for file_path in epics_dir.glob("*.md"):
                stat = file_path.stat()
                epic_files.append({
                    "name": file_path.stem,
                    "filename": file_path.name,
                    "path": str(file_path),
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "size": stat.st_size
                })

        # Get archived Task files
        tasks_dir = archive_dir / "tasks"
        task_files = []
        if tasks_dir.exists():
            for file_path in tasks_dir.glob("*.md"):
                stat = file_path.stat()
                task_files.append({
                    "name": file_path.stem,
                    "filename": file_path.name,
                    "path": str(file_path),
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "size": stat.st_size
                })

        # Sort by name
        prd_files.sort(key=lambda x: x["name"])
        epic_files.sort(key=lambda x: x["name"])
        task_files.sort(key=lambda x: x["name"])

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "prds": prd_files,
                "epics": epic_files,
                "tasks": task_files,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    except Exception as e:
        logger.error(f"Failed to list archived planning files: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response("Failed to list archived planning files")
        )


@router.post("/archive")
async def archive_planning_file(request_data: dict):
    """
    Archive a PRD, Epic, or Task file by moving it to the archive directory.

    When archiving a PRD, also archives related Epic and Task files.
    When archiving an Epic, also archives related Task files.

    Args:
        request_data: Dict with 'file_type' ('prd', 'epic', or 'task') and 'filename'

    Returns:
        JSON response with success status and list of archived files
    """
    try:
        file_type = request_data.get("file_type")
        filename = request_data.get("filename")

        if not file_type or not filename:
            return JSONResponse(
                status_code=400,
                content=create_error_response("file_type and filename are required")
            )

        # Validate file type
        if file_type not in ["prd", "epic", "task"]:
            return JSONResponse(
                status_code=400,
                content=create_error_response("file_type must be 'prd', 'epic', or 'task'")
            )

        # Ensure filename has .md extension
        if not filename.endswith('.md'):
            filename += '.md'

        archived_files = []

        def archive_file(ftype: str, fname: str) -> bool:
            """Helper function to archive a single file."""
            file_type_plural = ftype + 's'
            source_path = Path(".pm") / file_type_plural / fname
            dest_dir = Path(".pm/archive") / file_type_plural
            dest_path = dest_dir / fname

            if not source_path.exists():
                return False

            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path), str(dest_path))
            archived_files.append({"type": ftype, "filename": fname})
            logger.info(f"Archived {ftype} file: {fname}")
            return True

        # Archive the requested file
        if not archive_file(file_type, filename):
            return JSONResponse(
                status_code=404,
                content=create_error_response(f"File {filename} not found in {file_type}s")
            )

        # Get base name (remove .md extension and any numeric prefix)
        base_name = filename[:-3]  # Remove .md

        # If archiving a PRD, also archive related Epic and Tasks
        if file_type == "prd":
            # Archive the matching Epic file (same base name)
            epic_path = Path(".pm/epics") / filename
            if epic_path.exists():
                archive_file("epic", filename)

            # Archive all related Task files (pattern: NNN-base_name.md)
            tasks_dir = Path(".pm/tasks")
            if tasks_dir.exists():
                # Match tasks like 001-base_name.md, 002-base_name.md, etc.
                task_pattern = re.compile(rf'^\d+-{re.escape(base_name)}\.md$')
                for task_file in tasks_dir.glob("*.md"):
                    if task_pattern.match(task_file.name):
                        archive_file("task", task_file.name)

        # If archiving an Epic, also archive related Tasks
        elif file_type == "epic":
            tasks_dir = Path(".pm/tasks")
            if tasks_dir.exists():
                task_pattern = re.compile(rf'^\d+-{re.escape(base_name)}\.md$')
                for task_file in tasks_dir.glob("*.md"):
                    if task_pattern.match(task_file.name):
                        archive_file("task", task_file.name)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Archived {len(archived_files)} file(s)",
                "archived_files": archived_files
            }
        )

    except Exception as e:
        logger.error(f"Failed to archive planning file: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response("Failed to archive planning file")
        )


@router.post("/unarchive")
async def unarchive_planning_file(request_data: dict):
    """
    Unarchive a PRD, Epic, or Task file by moving it back to the active directory.

    When unarchiving a PRD, also unarchives related Epic and Task files.
    When unarchiving an Epic, also unarchives related Task files.

    Args:
        request_data: Dict with 'file_type' ('prd', 'epic', or 'task') and 'filename'

    Returns:
        JSON response with success status and list of unarchived files
    """
    try:
        file_type = request_data.get("file_type")
        filename = request_data.get("filename")

        if not file_type or not filename:
            return JSONResponse(
                status_code=400,
                content=create_error_response("file_type and filename are required")
            )

        # Validate file type
        if file_type not in ["prd", "epic", "task"]:
            return JSONResponse(
                status_code=400,
                content=create_error_response("file_type must be 'prd', 'epic', or 'task'")
            )

        # Ensure filename has .md extension
        if not filename.endswith('.md'):
            filename += '.md'

        unarchived_files = []
        conflicts = []

        def unarchive_file(ftype: str, fname: str) -> bool:
            """Helper function to unarchive a single file."""
            file_type_plural = ftype + 's'
            source_path = Path(".pm/archive") / file_type_plural / fname
            dest_dir = Path(".pm") / file_type_plural
            dest_path = dest_dir / fname

            if not source_path.exists():
                return False

            # Check if destination file already exists
            if dest_path.exists():
                conflicts.append({"type": ftype, "filename": fname})
                return False

            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path), str(dest_path))
            unarchived_files.append({"type": ftype, "filename": fname})
            logger.info(f"Unarchived {ftype} file: {fname}")
            return True

        # Unarchive the requested file
        if not unarchive_file(file_type, filename):
            # Check if it was a conflict or not found
            if conflicts:
                return JSONResponse(
                    status_code=409,
                    content=create_error_response(f"File {filename} already exists in {file_type}s")
                )
            return JSONResponse(
                status_code=404,
                content=create_error_response(f"File {filename} not found in archive/{file_type}s")
            )

        # Get base name (remove .md extension)
        base_name = filename[:-3]  # Remove .md

        # If unarchiving a PRD, also unarchive related Epic and Tasks
        if file_type == "prd":
            # Unarchive the matching Epic file (same base name)
            epic_path = Path(".pm/archive/epics") / filename
            if epic_path.exists():
                unarchive_file("epic", filename)

            # Unarchive all related Task files (pattern: NNN-base_name.md)
            tasks_archive_dir = Path(".pm/archive/tasks")
            if tasks_archive_dir.exists():
                task_pattern = re.compile(rf'^\d+-{re.escape(base_name)}\.md$')
                for task_file in tasks_archive_dir.glob("*.md"):
                    if task_pattern.match(task_file.name):
                        unarchive_file("task", task_file.name)

        # If unarchiving an Epic, also unarchive related Tasks
        elif file_type == "epic":
            tasks_archive_dir = Path(".pm/archive/tasks")
            if tasks_archive_dir.exists():
                task_pattern = re.compile(rf'^\d+-{re.escape(base_name)}\.md$')
                for task_file in tasks_archive_dir.glob("*.md"):
                    if task_pattern.match(task_file.name):
                        unarchive_file("task", task_file.name)

        response_content = {
            "success": True,
            "message": f"Unarchived {len(unarchived_files)} file(s)",
            "unarchived_files": unarchived_files
        }

        if conflicts:
            response_content["conflicts"] = conflicts
            response_content["message"] += f" ({len(conflicts)} file(s) skipped due to conflicts)"

        return JSONResponse(
            status_code=200,
            content=response_content
        )

    except Exception as e:
        logger.error(f"Failed to unarchive planning file: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response("Failed to unarchive planning file")
        )
