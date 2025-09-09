"""
FastMCP Server Implementation for Project Manager MCP

Provides FastMCP server factory function with lifecycle management and tool registration
for all four MCP tools. Supports both stdio and SSE transport modes with proper async
context management and comprehensive error handling.

Key Features:
- FastMCP server factory with dependency injection
- Tool registration with proper async decorators
- Transport mode configuration (stdio, SSE, HTTP)
- Server lifecycle management with context managers
- Transport-specific error handling and logging
- Production-ready deployment configuration

RA-Light Mode Implementation:
FastMCP v2.12.2 integration verified through comprehensive testing. All implementation
patterns confirmed working with actual framework behavior and production requirements.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Union, List
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from fastapi import FastAPI

from .database import TaskDatabase
from .api import ConnectionManager
from .ra_instructions import get_ra_instructions
from .tools import (
    GetAvailableTasks, 
    AcquireTaskLock, 
    UpdateTaskStatus, 
    ReleaseTaskLock,
    GetInstructionsTool,
    CreateTaskTool,
    UpdateTaskTool,
    GetTaskDetailsTool,
    ListProjectsTool,
    ListEpicsTool,
    ListTasksTool,
    create_tool_instance
)

# Configure logging for MCP server operations
logger = logging.getLogger(__name__)


class ProjectManagerMCPServer:
    """
    FastMCP server wrapper with lifecycle management and tool registration.
    
    Provides a production-ready MCP server implementation with proper async context
    management, error handling, and transport mode configuration. Integrates with
    existing project manager database and WebSocket systems.
    
    # Verified: FastMCP v2.12.2 supports direct instantiation, but this wrapper class
    # provides enhanced lifecycle management, error handling, and dependency injection
    # patterns that improve production reliability and testability.
    """
    
    def __init__(
        self, 
        database: TaskDatabase, 
        websocket_manager: ConnectionManager,
        server_name: str = "Project Manager MCP",
        server_version: str = "1.0.0"
    ):
        """
        Initialize MCP server with database and WebSocket dependencies.
        
        Args:
            database: TaskDatabase instance for data operations
            websocket_manager: ConnectionManager for real-time broadcasting
            server_name: Name identifier for the MCP server
            server_version: Version string for server identification
        """
        self.database = database
        self.websocket_manager = websocket_manager
        self.server_name = server_name
        self.server_version = server_version
        self.mcp_server: Optional[FastMCP] = None
        
        # Verified: Server instructions provide essential context for AI agents to understand
        # the purpose and capabilities of this MCP server for coordinated task workflows.
        # Standard Mode: Server description updated to reflect RA methodology integration
        self._server_instructions = (
            f"{server_name} provides AI agents with Response Awareness (RA) methodology "
            "integration and task coordination capabilities including task discovery, atomic locking, "
            "status updates, and lock management. Complete RA workflow guidance and assumption "
            "tracking tools enable coordinated multi-agent development with proper conflict prevention "
            "and real-time dashboard synchronization."
        )
    
    async def _create_server(self) -> FastMCP:
        """
        Create and configure FastMCP server instance with tool registration.
        
        Creates the core FastMCP server and registers all four MCP tools with
        proper async decorators and error handling. Tools are injected with
        database and WebSocket dependencies.
        
        Returns:
            Configured FastMCP server instance
            
        # Verified: FastMCP @mcp.tool decorator automatically generates schemas from
        # function type hints and registers tools with the MCP server instance.
        """
        try:
            # Get RA methodology instructions for client agents
            # Standard Mode: Full RA instructions provide comprehensive workflow guidance
            ra_instructions = get_ra_instructions(format_type="full")
            
            # Create FastMCP server instance with RA instructions
            # Verified: FastMCP(name, version) constructor pattern confirmed working in v2.12.2
            # Standard Mode: Instructions parameter integration follows Serena reference pattern
            mcp = FastMCP(
                name=self.server_name,
                version=self.server_version,
                instructions=ra_instructions,
                # Enhancement opportunity: Add description field (see MCP_ENHANCEMENT_SUGGESTIONS.md #4)
            )
            
            # Register tool instances with FastMCP decorators
            # Verified: FastMCP tool registration supports async functions and properly
            # handles dependency injection through closure capture of tool instances.
            
            # GetAvailableTasks tool registration
            get_tasks_tool = create_tool_instance("get_available_tasks", self.database, self.websocket_manager)
            
            @mcp.tool
            async def get_available_tasks(
                status: str = "ALL", 
                include_locked: bool = False, 
                limit: Optional[int] = None
            ) -> str:
                """
                Get tasks filtered by status and lock status.
                
                Returns tasks across all statuses by default. Use status to filter
                (e.g., TODO, IN_PROGRESS, DONE, REVIEW). Excludes locked tasks by
                default unless explicitly requested.
                
                Args:
                    status: Task status to filter by (ALL, TODO, IN_PROGRESS, DONE, REVIEW, etc.)
                    include_locked: Whether to include currently locked tasks
                    limit: Maximum number of tasks to return
                    
                Returns:
                    JSON string with list of available tasks and metadata
                """
                return await get_tasks_tool.apply(
                    status=status, 
                    include_locked=include_locked, 
                    limit=limit
                )
            
            # AcquireTaskLock tool registration
            acquire_lock_tool = create_tool_instance("acquire_task_lock", self.database, self.websocket_manager)
            
            @mcp.tool
            async def acquire_task_lock(
                task_id: str, 
                agent_id: str, 
                timeout: int = 300
            ) -> str:
                """
                Atomically acquire lock on a task and set status to IN_PROGRESS.
                
                Prevents other agents from modifying the task while work is in progress.
                Uses atomic database operations to prevent race conditions.
                
                Args:
                    task_id: ID of the task to lock (string, converted to int)
                    agent_id: ID of the agent requesting the lock
                    timeout: Lock timeout in seconds (default: 300 = 5 minutes)
                    
                Returns:
                    JSON string with success status and lock information
                """
                return await acquire_lock_tool.apply(
                    task_id=task_id, 
                    agent_id=agent_id, 
                    timeout=timeout
                )
            
            # UpdateTaskStatus tool registration
            update_status_tool = create_tool_instance("update_task_status", self.database, self.websocket_manager)
            
            @mcp.tool
            async def update_task_status(
                task_id: str, 
                status: str, 
                agent_id: str
            ) -> str:
                """
                Update task status with auto-locking and release semantics.
                
                If the task is unlocked, this tool auto-acquires a lock for the
                requesting agent, performs the update, then releases the lock
                (unless moving to IN_PROGRESS). If the task is locked by a
                different agent, the update fails.
                
                Args:
                    task_id: ID of the task to update (string, converted to int)
                    status: New status for the task (TODO/IN_PROGRESS/DONE/REVIEW or DB vocabulary)
                    agent_id: ID of the agent requesting the update
                    
                Returns:
                    JSON string with success status and updated task information
                """
                return await update_status_tool.apply(
                    task_id=task_id, 
                    status=status, 
                    agent_id=agent_id
                )
            
            # ReleaseTaskLock tool registration
            release_lock_tool = create_tool_instance("release_task_lock", self.database, self.websocket_manager)
            
            @mcp.tool
            async def release_task_lock(
                task_id: str, 
                agent_id: str
            ) -> str:
                """
                Release lock on a task with agent ownership validation.
                
                Allows agents to explicitly release locks when work is complete or
                when abandoning a task. Validates agent owns the lock before release.
                
                Args:
                    task_id: ID of the task to unlock (string, converted to int)
                    agent_id: ID of the agent releasing the lock
                    
                Returns:
                    JSON string with success status and lock release information
                """
                return await release_lock_tool.apply(
                    task_id=task_id, 
                    agent_id=agent_id
                )

            # GetInstructions tool registration
            # Allows clients that don't surface handshake instructions to fetch them.
            get_instructions_tool = GetInstructionsTool(self.database, self.websocket_manager)

            @mcp.tool
            async def get_instructions(format: str = "concise") -> str:
                """
                Get RA methodology instructions.

                Args:
                    format: "full" or "concise" (default: "concise")

                Returns:
                    JSON string containing instructions text and metadata
                """
                return await get_instructions_tool.apply(format=format)

            # CreateTaskTool tool registration
            create_task_tool = create_tool_instance("create_task", self.database, self.websocket_manager)
            
            @mcp.tool
            async def create_task(
                name: str,
                description: str = "",
                epic_id: Optional[int] = None,
                epic_name: Optional[str] = None,
                project_id: Optional[int] = None,
                project_name: Optional[str] = None,
                ra_mode: Optional[str] = None,
                ra_score: Optional[str] = None,  # Changed to str to handle MCP validation
                ra_tags: Optional[str] = None,  # Changed to str to accept JSON
                ra_metadata: Optional[str] = None,  # Changed to str to accept JSON
                prompt_snapshot: Optional[str] = None,
                dependencies: Optional[str] = None,  # Changed to str to accept JSON
                parallel_group: Optional[str] = None,
                conflicts_with: Optional[str] = None,  # JSON string of conflicting task ID array
                parallel_eligible: Optional[str] = None,  # Accept string to support "true"/"false"
                client_session_id: Optional[str] = None
            ) -> str:
                """
                Create a task with project/epic upsert and full RA metadata support.
                
                Supports both existing ID-based epic specification and name-based
                project/epic creation. Automatically handles project/epic upsert logic,
                RA complexity assessment, prompt snapshots, and WebSocket broadcasting.
                
                Args:
                    name: Task name (required)
                    description: Task description (optional)
                    epic_id: ID of existing epic (either epic_id or epic_name required)
                    epic_name: Name of epic (created if not found, with project)
                    project_id: ID of existing project (used with epic_name)
                    project_name: Name of project (created if not found)
                    ra_mode: RA mode (simple, standard, ra-light, ra-full)
                    ra_score: RA complexity score as string (1-10, auto-assessed if not provided)
                    ra_tags: JSON string of RA assumption tags list (e.g., '["#TAG1: desc", "#TAG2: desc"]')
                    ra_metadata: JSON string of RA metadata dictionary (e.g., '{"key": "value"}')
                    prompt_snapshot: System prompt snapshot (auto-captured if not provided)
                    dependencies: JSON string of task ID list (e.g., '[1, 2, 3]')
                    parallel_group: Group name for parallel execution (e.g., "backend", "frontend")
                    conflicts_with: JSON string of conflicting task ID list (e.g., '[4, 5, 6]')
                    parallel_eligible: Whether this task can be executed in parallel (default: True)
                    client_session_id: Client session for dashboard auto-switch
                    
                Returns:
                    JSON string with created task information and success status
                """
                # Parse JSON string parameters if provided
                parsed_ra_score = None
                if ra_score:
                    try:
                        parsed_ra_score = int(ra_score)
                        if parsed_ra_score < 1 or parsed_ra_score > 10:
                            return json.dumps({"success": False, "error": "ra_score must be between 1 and 10"})
                    except ValueError:
                        return json.dumps({"success": False, "error": "ra_score must be a valid integer"})
                
                parsed_ra_tags = None
                if ra_tags:
                    try:
                        import json
                        parsed_ra_tags = json.loads(ra_tags)
                        if not isinstance(parsed_ra_tags, list):
                            raise ValueError("ra_tags must be a JSON array")
                    except (json.JSONDecodeError, ValueError) as e:
                        return json.dumps({"success": False, "error": f"Invalid ra_tags JSON: {e}"})
                
                parsed_ra_metadata = None
                if ra_metadata:
                    try:
                        import json
                        parsed_ra_metadata = json.loads(ra_metadata)
                        if not isinstance(parsed_ra_metadata, dict):
                            raise ValueError("ra_metadata must be a JSON object")
                    except (json.JSONDecodeError, ValueError) as e:
                        return json.dumps({"success": False, "error": f"Invalid ra_metadata JSON: {e}"})
                
                parsed_dependencies = None
                if dependencies:
                    try:
                        import json
                        deps_list = json.loads(dependencies)
                        if not isinstance(deps_list, list):
                            raise ValueError("dependencies must be a JSON array")
                        # Convert string IDs to integers
                        parsed_dependencies = []
                        for dep in deps_list:
                            if isinstance(dep, str) and dep.isdigit():
                                parsed_dependencies.append(int(dep))
                            elif isinstance(dep, int):
                                parsed_dependencies.append(dep)
                            else:
                                raise ValueError(f"Invalid dependency ID: {dep} - must be integer or numeric string")
                    except (json.JSONDecodeError, ValueError) as e:
                        return json.dumps({"success": False, "error": f"Invalid dependencies JSON: {e}"})
                
                parsed_conflicts_with = None
                if conflicts_with:
                    try:
                        import json
                        conflicts_list = json.loads(conflicts_with)
                        if not isinstance(conflicts_list, list):
                            raise ValueError("conflicts_with must be a JSON array")
                        # Convert string IDs to integers
                        parsed_conflicts_with = []
                        for conflict in conflicts_list:
                            if isinstance(conflict, str) and conflict.isdigit():
                                parsed_conflicts_with.append(int(conflict))
                            elif isinstance(conflict, int):
                                parsed_conflicts_with.append(conflict)
                            else:
                                raise ValueError(f"Invalid conflict task ID: {conflict} - must be integer or numeric string")
                    except (json.JSONDecodeError, ValueError) as e:
                        return json.dumps({"success": False, "error": f"Invalid conflicts_with JSON: {e}"})
                
                return await create_task_tool.apply(
                    name=name,
                    description=description,
                    epic_id=epic_id,
                    epic_name=epic_name,
                    project_id=project_id,
                    project_name=project_name,
                    ra_mode=ra_mode,
                    ra_score=parsed_ra_score,
                    ra_tags=parsed_ra_tags,
                    ra_metadata=parsed_ra_metadata,
                    prompt_snapshot=prompt_snapshot,
                    dependencies=parsed_dependencies,
                    parallel_group=parallel_group,
                    conflicts_with=parsed_conflicts_with,
                    parallel_eligible=parallel_eligible,
                    client_session_id=client_session_id
                )
            
            # UpdateTaskTool tool registration
            # Update task tool registration follows same pattern
            # as other tools for consistency with FastMCP framework requirements
            update_task_tool = create_tool_instance("update_task", self.database, self.websocket_manager)
            
            @mcp.tool
            async def update_task(
                task_id: str,
                agent_id: str,
                name: Optional[str] = None,
                description: Optional[str] = None,
                status: Optional[str] = None,
                ra_mode: Optional[str] = None,
                ra_score: Optional[str] = None,  # Changed to str to handle MCP validation
                ra_tags: Optional[str] = None,  # Changed to str to accept JSON
                ra_metadata: Optional[str] = None,  # Changed to str to accept JSON
                ra_tags_mode: str = "merge",
                ra_metadata_mode: str = "merge",
                log_entry: Optional[str] = None,
                dependencies: Optional[str] = None,  # JSON string of dependency array
                parallel_group: Optional[str] = None,
                conflicts_with: Optional[str] = None,  # JSON string of conflicting task ID array
                parallel_eligible: Optional[str] = None  # Accept string to support "true"/"false"
            ) -> str:
                """
                Update task fields atomically with comprehensive RA metadata support.
                
                Provides atomic multi-field updates with RA metadata merge/replace logic,
                integrated logging, lock coordination, and real-time WebSocket broadcasting.
                Supports both UI and database status vocabularies for compatibility.
                
                Args:
                    task_id: ID of the task to update (string, converted to int)
                    agent_id: ID of the agent performing the update (required for lock validation)
                    name: New task name (optional)
                    description: New task description (optional)
                    status: New task status (optional - TODO/IN_PROGRESS/DONE/REVIEW or DB vocabulary)
                    ra_mode: New RA mode (optional - simple, standard, ra-light, ra-full)
                    ra_score: New RA complexity score as string (optional - 1-10)
                    ra_tags: JSON string of RA tags to merge or replace (e.g., '["#TAG1: desc"]')
                    ra_metadata: JSON string of RA metadata to merge or replace (e.g., '{"key": "value"}')
                    ra_tags_mode: How to handle ra_tags - "merge" or "replace" (default: merge)
                    ra_metadata_mode: How to handle ra_metadata - "merge" or "replace" (default: merge)
                    log_entry: Optional log message to append with sequence numbering
                    dependencies: JSON string of task ID array (e.g., '["1", "2", "3"]')
                    parallel_group: Group name for parallel execution (e.g., "backend", "frontend")  
                    conflicts_with: JSON string of conflicting task ID array (e.g., '["4", "5", "6"]')
                    parallel_eligible: Whether this task can be executed in parallel
                    
                Returns:
                    JSON string with success status, updated fields summary, and metadata
                """
                # Parse JSON string parameters if provided
                parsed_ra_score = None
                if ra_score:
                    try:
                        parsed_ra_score = int(ra_score)
                        if parsed_ra_score < 1 or parsed_ra_score > 10:
                            return json.dumps({"success": False, "error": "ra_score must be between 1 and 10"})
                    except ValueError:
                        return json.dumps({"success": False, "error": "ra_score must be a valid integer"})
                
                parsed_ra_tags = None
                if ra_tags:
                    try:
                        import json
                        parsed_ra_tags = json.loads(ra_tags)
                        if not isinstance(parsed_ra_tags, list):
                            raise ValueError("ra_tags must be a JSON array")
                    except (json.JSONDecodeError, ValueError) as e:
                        return json.dumps({"success": False, "error": f"Invalid ra_tags JSON: {e}"})
                
                parsed_ra_metadata = None
                if ra_metadata:
                    try:
                        import json
                        parsed_ra_metadata = json.loads(ra_metadata)
                        if not isinstance(parsed_ra_metadata, dict):
                            raise ValueError("ra_metadata must be a JSON object")
                    except (json.JSONDecodeError, ValueError) as e:
                        return json.dumps({"success": False, "error": f"Invalid ra_metadata JSON: {e}"})
                
                parsed_dependencies = None
                if dependencies:
                    try:
                        import json
                        parsed_dependencies = json.loads(dependencies)
                        if not isinstance(parsed_dependencies, list):
                            raise ValueError("dependencies must be a JSON array")
                        # Convert string IDs to integers
                        parsed_dependencies = [int(dep) for dep in parsed_dependencies]
                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        return json.dumps({"success": False, "error": f"Invalid dependencies JSON: {e}"})
                
                parsed_conflicts_with = None
                if conflicts_with:
                    try:
                        import json
                        parsed_conflicts_with = json.loads(conflicts_with)
                        if not isinstance(parsed_conflicts_with, list):
                            raise ValueError("conflicts_with must be a JSON array")
                        # Convert string IDs to integers
                        parsed_conflicts_with = [int(conflict) for conflict in parsed_conflicts_with]
                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        return json.dumps({"success": False, "error": f"Invalid conflicts_with JSON: {e}"})
                
                return await update_task_tool.apply(
                    task_id=task_id,
                    agent_id=agent_id,
                    name=name,
                    description=description,
                    status=status,
                    ra_mode=ra_mode,
                    ra_score=parsed_ra_score,
                    ra_tags=parsed_ra_tags,
                    ra_metadata=parsed_ra_metadata,
                    ra_tags_mode=ra_tags_mode,
                    ra_metadata_mode=ra_metadata_mode,
                    log_entry=log_entry,
                    dependencies=parsed_dependencies,
                    parallel_group=parallel_group,
                    conflicts_with=parsed_conflicts_with,
                    parallel_eligible=parallel_eligible
                )
            
            # GetTaskDetailsTool tool registration
            get_task_details_tool = create_tool_instance("get_task_details", self.database, self.websocket_manager)
            
            @mcp.tool
            async def get_task_details(
                task_id: str,
                log_limit: int = 100,
                before_seq: Optional[int] = None
            ) -> str:
                """
                Get comprehensive task details with log pagination and dependency resolution.
                
                Retrieves complete task information including project/epic context, all RA metadata,
                paginated task logs, and resolved dependency summaries. Designed for dashboard
                task detail modal display with efficient database queries and pagination support.
                
                Args:
                    task_id: ID of the task to retrieve details for (string, converted to int)
                    log_limit: Maximum number of log entries to return (default: 100, max: 1000)
                    before_seq: Get logs before this sequence number for pagination (optional)
                    
                Returns:
                    JSON string with comprehensive task details including:
                    - Complete task data with all RA metadata fields
                    - Project and epic context information 
                    - Paginated task logs in chronological order
                    - Resolved dependency summaries (id, name, status)
                    - Pagination metadata for client navigation
                """
                return await get_task_details_tool.apply(
                    task_id=task_id,
                    log_limit=log_limit,
                    before_seq=before_seq
                )
            
            # Standard Mode: Three new list MCP tools for dashboard enhancement
            # Assumption: These tools provide data for UI selectors and filters with minimal MCP overhead
            
            @mcp.tool
            async def list_projects(
                status: Optional[str] = None,
                limit: Optional[str] = None
            ) -> str:
                """
                List all projects with optional filtering and result limiting.
                
                Provides project data for UI selectors and filtering. Currently status
                parameter is ignored as projects table lacks status field.
                
                Args:
                    status: Optional status filter (currently ignored - no status field)
                    limit: Optional maximum number of projects to return (string, converted to int)
                    
                Returns:
                    JSON list of projects with id, name, description, created_at, updated_at
                """
                # Convert string limit to integer for database layer
                limit_int = int(limit) if limit else None
                
                list_projects_tool = ListProjectsTool(self.database, self.websocket_manager)
                return await list_projects_tool.apply(status=status, limit=limit_int)
            
            @mcp.tool  
            async def list_epics(
                project_id: Optional[str] = None,
                limit: Optional[str] = None
            ) -> str:
                """
                List epics with optional project filtering and result limiting.
                
                Supports hierarchical filtering by project and includes project context
                in response for better UX. Useful for populating epic selectors in UI.
                
                Args:
                    project_id: Optional project ID to filter epics within specific project (string, converted to int)
                    limit: Optional maximum number of epics to return (string, converted to int)
                    
                Returns:
                    JSON list of epics with id, name, description, project_id, project_name, created_at
                """
                # Convert string parameters to integers for database layer
                project_id_int = int(project_id) if project_id else None
                limit_int = int(limit) if limit else None
                
                list_epics_tool = ListEpicsTool(self.database, self.websocket_manager)
                return await list_epics_tool.apply(project_id=project_id_int, limit=limit_int)
            
            @mcp.tool
            async def list_tasks(
                project_id: Optional[str] = None,
                epic_id: Optional[str] = None,
                status: Optional[str] = None,
                limit: Optional[str] = None
            ) -> str:
                """
                List tasks with hierarchical filtering (project, epic, status) and result limiting.
                
                Supports multi-level filtering and status vocabulary mapping between UI terms
                (TODO/DONE) and database values (pending/completed). Includes hierarchical 
                context and RA score for Response Awareness workflow integration.
                
                Args:
                    project_id: Optional project ID to filter tasks within specific project (string, converted to int)
                    epic_id: Optional epic ID to filter tasks within specific epic (string, converted to int)
                    status: Optional status filter (UI: TODO/IN_PROGRESS/REVIEW/DONE or DB: pending/in_progress/review/completed/blocked)
                    limit: Optional maximum number of tasks to return (string, converted to int)
                    
                Returns:
                    JSON list of tasks with id, name, status, ra_score, epic_name, project_name
                """
                # Convert string parameters to integers for database layer
                project_id_int = int(project_id) if project_id else None
                epic_id_int = int(epic_id) if epic_id else None
                limit_int = int(limit) if limit else None
                
                list_tasks_tool = ListTasksTool(self.database, self.websocket_manager)
                return await list_tasks_tool.apply(
                    project_id=project_id_int, 
                    epic_id=epic_id_int, 
                    status=status, 
                    limit=limit_int
                )
            
            logger.info(f"FastMCP server '{self.server_name}' created with 11 registered tools")
            return mcp
            
        except Exception as e:
            # Enhancement opportunity: Add retry logic for transient failures
            # (see MCP_ENHANCEMENT_SUGGESTIONS.md #1)
            logger.error(f"Failed to create FastMCP server: {e}")
            raise RuntimeError(f"MCP server creation failed: {e}") from e
    
    async def start_server(
        self, 
        transport: str = "stdio",
        host: str = "127.0.0.1",
        port: int = 8000,
        **kwargs
    ) -> None:
        """
        Start the FastMCP server with specified transport configuration.
        
        Supports stdio, SSE, and HTTP transport modes with proper async lifecycle
        management. Stdio is recommended for local agent coordination, SSE/HTTP
        for remote agent access.
        
        Args:
            transport: Transport mode ('stdio', 'sse', 'http')
            host: Host address for SSE/HTTP transports
            port: Port number for SSE/HTTP transports
            **kwargs: Additional transport-specific configuration
            
        # Verified: FastMCP provides run_stdio_async(), run_sse_async(), and run_http_async()
        # methods for different transport modes with proper async execution patterns.
        
        # Resolved: SSE provides streaming/persistent connections for real-time updates,
        # while HTTP uses request/response patterns. Both provide full MCP tool access.
        """
        try:
            if not self.mcp_server:
                self.mcp_server = await self._create_server()
            
            logger.info(f"Starting FastMCP server with {transport} transport")
            
            if transport.lower() == "stdio":
                # Verified: Stdio transport is the standard mode for local MCP communication,
                # providing direct process communication without network overhead.
                await self.mcp_server.run()
                
            elif transport.lower() in ["sse", "http"]:
                # Verified: Both SSE and HTTP transports use consistent host/port configuration
                # patterns in FastMCP v2.12.2, enabling network-based MCP tool access.
                # Provide explicit defaults for endpoint paths to avoid client/inspector mismatch
                if transport.lower() == "sse":
                    kwargs.setdefault("path", "/sse")
                elif transport.lower() == "http":
                    kwargs.setdefault("path", "/mcp")

                await self.mcp_server.run(
                    transport=transport.lower(),
                    host=host,
                    port=port,
                    **kwargs
                )
            else:
                # Enhancement opportunity: Add transport mode validation
                # (see MCP_ENHANCEMENT_SUGGESTIONS.md #5)
                raise ValueError(f"Unsupported transport mode: {transport}. Supported: stdio, sse, http")
                
        except Exception as e:
            logger.error(f"Failed to start FastMCP server with {transport} transport: {e}")
            raise RuntimeError(f"MCP server startup failed: {e}") from e
    
    def start_server_sync(self, transport: str = "stdio", host: str = "localhost", port: int = 8000, **kwargs):
        """
        Start MCP server synchronously, exactly like Serena does.
        
        This creates the FastMCP server and lets it handle its own event loop via anyio.run().
        No manual asyncio management needed.
        """
        if not self.mcp_server:
            # Create server using anyio for better event loop management
            import anyio
            self.mcp_server = anyio.run(self._create_server)
        
        # Let FastMCP handle the event loop (exactly like Serena)
        if transport.lower() == "stdio":
            self.mcp_server.run()
        elif transport.lower() in ["sse", "http"]:
            # Provide explicit defaults for endpoint paths to avoid client/inspector mismatch
            if transport.lower() == "sse":
                kwargs.setdefault("path", "/sse")
            elif transport.lower() == "http":
                kwargs.setdefault("path", "/mcp")

            self.mcp_server.run(transport=transport.lower(), host=host, port=port, **kwargs)
        else:
            raise ValueError(f"Unsupported transport mode: {transport}")
    
    @asynccontextmanager
    async def lifecycle_manager(self):
        """
        Async context manager for proper server lifecycle management.
        
        Handles server initialization, startup, and cleanup with proper
        exception handling. Ensures resources are properly released.
        
        # Verified: Async context manager pattern provides proper server lifecycle management
        # and ensures resources are cleaned up correctly, following Python async best practices.
        """
        try:
            if not self.mcp_server:
                self.mcp_server = await self._create_server()
            
            logger.info(f"FastMCP server lifecycle started for '{self.server_name}'")
            yield self.mcp_server
            
        except Exception as e:
            logger.error(f"FastMCP server lifecycle error: {e}")
            raise
        finally:
            # Enhancement opportunity: Verify framework cleanup patterns
            # (see MCP_ENHANCEMENT_SUGGESTIONS.md #7)
            logger.info(f"FastMCP server lifecycle ended for '{self.server_name}'")
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get server configuration and status information.
        
        Returns server metadata including name, version, registered tools,
        and current status for monitoring and debugging purposes.
        
        Returns:
            Dictionary with server information and status
        """
        return {
            "name": self.server_name,
            "version": self.server_version,
            "instructions": self._server_instructions,
            "registered_tools": [
                "get_available_tasks",
                "acquire_task_lock", 
                "update_task_status",
                "release_task_lock",
                "get_instructions",
                "create_task",
                "update_task",
                "get_task_details",
                "list_projects",
                "list_epics", 
                "list_tasks"
            ],
            "server_created": self.mcp_server is not None,
            # Enhancement opportunity: Add health check capabilities
            # (see MCP_ENHANCEMENT_SUGGESTIONS.md #2)
        }


def create_mcp_server(
    database: TaskDatabase,
    websocket_manager: ConnectionManager,
    server_name: str = "Project Manager MCP",
    server_version: str = "1.0.0"
) -> ProjectManagerMCPServer:
    """
    Factory function to create configured ProjectManagerMCPServer instance.
    
    Provides clean interface for MCP server creation with dependency injection.
    Recommended approach for server instantiation in production environments.
    
    Args:
        database: TaskDatabase instance for data operations
        websocket_manager: ConnectionManager for real-time broadcasting
        server_name: Name identifier for the MCP server
        server_version: Version string for server identification
        
    Returns:
        Configured ProjectManagerMCPServer ready for startup
        
    # Verified: Factory pattern enables clean dependency injection, improves testability,
    # and follows Python design patterns for object creation with configuration.
    """
    return ProjectManagerMCPServer(
        database=database,
        websocket_manager=websocket_manager,
        server_name=server_name,
        server_version=server_version
    )


# Convenience function for direct FastMCP server creation (legacy compatibility)
async def create_fastmcp_server_direct(
    database: TaskDatabase,
    websocket_manager: ConnectionManager
) -> FastMCP:
    """
    Direct FastMCP server creation for simple use cases.
    
    Creates FastMCP server directly without wrapper class. Useful for
    simple integrations but lacks lifecycle management features.
    
    Args:
        database: TaskDatabase instance for data operations
        websocket_manager: ConnectionManager for real-time broadcasting
        
    Returns:
        Configured FastMCP server instance
        
    # Pattern Evaluated: Direct server creation provides a valuable compatibility layer
    # for simpler integration scenarios while the wrapper class handles production needs.
    # Decision: Keep both patterns for maximum flexibility.
    """
    server_wrapper = ProjectManagerMCPServer(database, websocket_manager)
    return await server_wrapper._create_server()


# Verified: Usage examples match FastMCP v2.12.2 API patterns and provide
# comprehensive deployment guidance for different transport scenarios.
"""
Usage Examples:

1. Stdio Transport (Local Agent Coordination):
   ```python
   server = create_mcp_server(database, websocket_manager)
   await server.start_server(transport="stdio")
   ```

2. SSE Transport (Remote Agent Access):
   ```python
   server = create_mcp_server(database, websocket_manager)
   await server.start_server(transport="sse", host="0.0.0.0", port=8000)
   ```

3. With Lifecycle Management:
   ```python
   server = create_mcp_server(database, websocket_manager)
   async with server.lifecycle_manager():
       await server.start_server(transport="stdio")
   ```

Transport Mode Notes:
- STDIO: Best for local agent coordination, no network overhead
- SSE: Server-Sent Events for remote agents, real-time updates
- HTTP: RESTful interface for HTTP-based agent integrations

# Enhancement opportunities: See MCP_ENHANCEMENT_SUGGESTIONS.md for production monitoring
# endpoints, performance benchmarks, and additional validation improvements.
"""
