"""
Project and epic management MCP tools.

Provides tools for listing projects, epics, and tasks with hierarchical
filtering and relationship context.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from .base import BaseTool

# Configure logging for project tool operations
logger = logging.getLogger(__name__)

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


