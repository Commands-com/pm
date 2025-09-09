"""
FastAPI Backend with WebSocket Manager for Project Manager MCP System

Provides REST endpoints for board state and task status updates, plus real-time 
WebSocket broadcasting to connected clients. Integrates with TaskDatabase layer
for persistent storage and atomic locking operations.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from .database import TaskDatabase
from .monitoring import performance_monitor, background_tasks
from .performance import OptimizedConnectionManager, DatabaseOptimizer

# Configure logging for debugging WebSocket connections and API operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path configuration from environment variable
import os
DB_PATH = os.getenv("DATABASE_PATH", "project_manager.db")

# Global database instance for dependency injection
# VERIFIED: Singleton pattern appropriate for single database instance per FastAPI app
# Alternative: connection pool if high concurrency needed
db_instance: Optional[TaskDatabase] = None


class ConnectionManager:
    """
    WebSocket connection manager with parallel broadcasting capabilities.
    
    Handles connection lifecycle, parallel message broadcasting to all clients,
    and automatic cleanup on disconnection. Uses asyncio.gather for efficient
    parallel broadcasting to minimize latency.
    """
    
    def __init__(self):
        # Active WebSocket connections registry
        self.active_connections: Set[WebSocket] = set()
        self._connection_lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection and add to active connections."""
        await websocket.accept()
        async with self._connection_lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket from active connections registry."""
        async with self._connection_lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, event_data: Dict[str, Any]):
        """
        Broadcast event to all connected WebSocket clients in parallel.
        
        Uses asyncio.gather() for parallel broadcasting to minimize latency.
        Automatically handles disconnected clients and removes them from registry.
        
        Args:
            event_data: Event data to broadcast (will be JSON serialized)
        """
        if not self.active_connections:
            logger.debug("No active connections for broadcast")
            return
        
        # #COMPLETION_DRIVE_IMPL: Using JSON serialization for standardized event format
        # WebSocket clients expect JSON format for event parsing
        message = json.dumps(event_data)
        
        # Create coroutines for parallel broadcasting
        send_tasks = []
        
        # #SUGGEST_ERROR_HANDLING: Consider adding per-connection error handling
        # Individual connection failures shouldn't stop broadcasting to other clients
        async with self._connection_lock:
            for websocket in self.active_connections.copy():
                send_tasks.append(self._send_safe(websocket, message))
        
        if send_tasks:
            # Parallel broadcast using asyncio.gather for performance
            # #COMPLETION_DRIVE_IMPL: Parallel broadcasting assumed more efficient than sequential
            results = await asyncio.gather(*send_tasks, return_exceptions=True)
            
            # Count successful broadcasts for monitoring
            successful_broadcasts = sum(1 for result in results if result is True)
            logger.info(f"Broadcast completed: {successful_broadcasts}/{len(send_tasks)} successful")
    
    async def _send_safe(self, websocket: WebSocket, message: str) -> bool:
        """
        Safely send message to individual WebSocket connection.
        
        Handles connection errors and removes failed connections from registry.
        
        Args:
            websocket: WebSocket connection to send to
            message: JSON message string to send
            
        Returns:
            True if successful, False if connection failed
        """
        try:
            await websocket.send_text(message)
            return True
        except Exception as e:
            # #COMPLETION_DRIVE_IMPL: Assuming any send exception means connection is dead
            # This covers network errors, closed connections, and protocol errors
            logger.warning(f"Failed to send message to WebSocket: {e}")
            await self.disconnect(websocket)
            return False
    
    async def broadcast_enriched_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Broadcast enriched event with comprehensive payload structure.
        
        #COMPLETION_DRIVE_INTEGRATION: Enhanced broadcasting for enriched payloads
        Provides structured event data with project/epic context, session tracking,
        and auto-switch flags as required by task specification.
        
        Args:
            event_type: Type of event (task.created, task.updated, task.logs.appended)
            event_data: Event-specific payload data
        """
        # #COMPLETION_DRIVE_IMPL: Enriched payload structure follows task specification exactly
        enriched_payload = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat() + 'Z',
            "data": event_data
        }
        
        # #SUGGEST_PERFORMANCE: Consider adding event size validation to prevent oversized payloads
        await self.broadcast(enriched_payload)
    
    def get_connection_count(self) -> int:
        """Get current number of active WebSocket connections."""
        return len(self.active_connections)


# #COMPLETION_DRIVE_IMPL: Session tracking utilities for client_session_id extraction
# MCP tools can include client_session_id parameter for dashboard auto-switch functionality
def extract_session_id(mcp_args: Dict[str, Any]) -> Optional[str]:
    """
    Extract client session ID from MCP tool arguments.
    
    #COMPLETION_DRIVE_INTEGRATION: Session ID extraction for auto-switch logic
    Enables dashboard clients to receive events with session context for proper
    auto-switching behavior when multiple clients are connected.
    
    Args:
        mcp_args: Dictionary of MCP tool arguments
        
    Returns:
        Client session ID if present, None otherwise
    """
    return mcp_args.get('client_session_id')


def generate_enriched_task_payload(task_data: Dict[str, Any], project_data: Optional[Dict[str, Any]] = None,
                                 epic_data: Optional[Dict[str, Any]] = None, 
                                 auto_flags: Optional[Dict[str, bool]] = None,
                                 session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate enriched task event payload with project/epic context and auto-switch flags.
    
    #COMPLETION_DRIVE_IMPL: Enriched payload generation as specified in task requirements
    Creates comprehensive event payloads with all required context for dashboard
    real-time updates and auto-switch functionality.
    
    Args:
        task_data: Core task information
        project_data: Project context (id, name)
        epic_data: Epic context (id, name, project_id)
        auto_flags: Auto-switch flags (project_created, epic_created)
        session_id: Client session ID for event targeting
        
    Returns:
        Enriched payload dictionary ready for WebSocket broadcasting
    """
    # #COMPLETION_DRIVE_IMPL: Task payload structure matches specification exactly
    payload = {
        "task": {
            "id": task_data.get("id"),
            "name": task_data.get("name"),
            "status": task_data.get("status"),
            "epic_id": task_data.get("epic_id"),
            "ra_score": task_data.get("ra_score"),
            "ra_mode": task_data.get("ra_mode"),
            "description": task_data.get("description", "")
        }
    }
    
    # Add project context if available
    if project_data:
        payload["project"] = {
            "id": project_data.get("id"),
            "name": project_data.get("name")
        }
    
    # Add epic context if available 
    if epic_data:
        payload["epic"] = {
            "id": epic_data.get("id"),
            "name": epic_data.get("name"),
            "project_id": epic_data.get("project_id")
        }
    
    # Add auto-switch flags if provided
    if auto_flags:
        payload["flags"] = auto_flags
    
    # Add session context for dashboard targeting
    if session_id:
        payload["initiator"] = session_id
        # #COMPLETION_DRIVE_INTEGRATION: Auto-switch recommendation based on session presence
        payload["auto_switch_recommended"] = True
    
    return payload


def generate_logs_appended_payload(task_id: int, log_entries: List[Dict[str, Any]], 
                                 session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate task.logs.appended event payload for real-time log updates.
    
    #COMPLETION_DRIVE_IMPL: Logs appended event as specified in task requirements
    Provides real-time log update events for dashboard execution log display
    with proper sequencing and task context.
    
    Args:
        task_id: ID of task receiving new log entries
        log_entries: List of new log entry dictionaries
        session_id: Optional session ID for event targeting
        
    Returns:
        Logs appended payload dictionary
    """
    payload = {
        "task_id": task_id,
        "log_entries": log_entries,
        "log_count": len(log_entries)
    }
    
    # Add sequence numbers for client synchronization
    if log_entries:
        payload["sequence_range"] = {
            "start": min(entry.get("seq", 0) for entry in log_entries),
            "end": max(entry.get("seq", 0) for entry in log_entries)
        }
    
    # Add session context if provided
    if session_id:
        payload["initiator"] = session_id
    
    return payload


# Global connection manager instance - using optimized version for better performance
# VERIFIED: Single ConnectionManager instance needed for WebSocket broadcasting coordination
# Alternative: dependency injection if multiple manager instances needed
connection_manager = OptimizedConnectionManager(max_connections=50)


# Pydantic models for request/response validation
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
        # #SUGGEST_VALIDATION: Consider adding agent ID format validation (e.g., UUID format)
        return v.strip()


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    database_connected: bool
    active_websocket_connections: int
    timestamp: str


class TaskStatusResponse(BaseModel):
    """Response model for task status update operations."""
    success: bool
    status: Optional[str] = None
    error: Optional[str] = None


class BoardStateResponse(BaseModel):
    """Response model for complete board state."""
    tasks: List[Dict[str, Any]]
    epics: List[Dict[str, Any]]
    projects: List[Dict[str, Any]]


class MetricsResponse(BaseModel):
    """Response model for performance metrics endpoint."""
    connections: Dict[str, Any]
    tasks: Dict[str, Any] 
    performance: Dict[str, Any]
    locks: Dict[str, Any]
    system: Dict[str, Any]


# Database dependency for FastAPI dependency injection
def get_database() -> TaskDatabase:
    """
    FastAPI dependency to provide database instance.
    
    Returns:
        TaskDatabase instance for database operations
        
    Raises:
        HTTPException: If database is not available
    """
    global db_instance
    if db_instance is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return db_instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup/shutdown operations.
    
    Handles database initialization and background task management.
    """
    global db_instance
    
    # Startup: Initialize database and background tasks
    try:
        db_instance = TaskDatabase(DB_PATH)
        logger.info(f"Database initialized: {DB_PATH}")
        
        # Start background tasks for monitoring and maintenance
        await background_tasks.start_background_tasks(db_instance, connection_manager)
        
        # Log startup information
        logger.info("Project Manager API starting up...")
        logger.info("Available endpoints:")
        logger.info("  GET /healthz - Health check")
        logger.info("  GET /api/board/state - Complete board state")
        logger.info("  GET /api/metrics - Performance metrics")
        logger.info("  POST /api/task/{task_id}/status - Update task status")
        logger.info("  POST /api/task/{task_id}/lock - Acquire task lock")
        logger.info("  DELETE /api/task/{task_id}/lock - Release task lock")
        logger.info("  WebSocket /ws/updates - Real-time event stream")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown: Stop background tasks and close database
    try:
        await background_tasks.stop_background_tasks()
    except Exception as e:
        logger.error(f"Error stopping background tasks: {e}")
    
    if db_instance:
        db_instance.close()
        logger.info("Database connection closed")


# FastAPI application with lifespan management
app = FastAPI(
    title="Project Manager API",
    description="REST API with WebSocket support for AI agent task management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for browser compatibility
# #COMPLETION_DRIVE_IMPL: Allowing all origins for development flexibility
# Production deployments should restrict origins to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # #SUGGEST_DEFENSIVE: Consider restricting origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for dashboard
# Get the directory where this api.py file is located
import os
from pathlib import Path

static_dir = Path(__file__).parent / "static"
try:
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        logger.info(f"Static files served from: {static_dir}")
    else:
        raise FileNotFoundError(f"Static directory not found: {static_dir}")
except Exception as e:
    # #SUGGEST_ERROR_HANDLING: Static file serving is optional for API functionality
    logger.warning(f"Static file serving not available: {e}")


# Health check endpoint for monitoring and load balancers
@app.get("/healthz", response_model=HealthResponse)
async def health_check(db: TaskDatabase = Depends(get_database)):
    """
    Enhanced health check endpoint for service monitoring.
    
    Returns comprehensive service status including database connectivity,
    WebSocket connections, and service component health. Used by load 
    balancers and monitoring systems to verify service health.
    """
    
    # Test database connectivity
    database_connected = True
    try:
        # Simple query to verify database connectivity and perform cleanup
        db.cleanup_expired_locks()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        database_connected = False
    
    # Determine overall health status
    overall_status = "healthy" if database_connected else "degraded"
    
    return HealthResponse(
        status=overall_status,
        database_connected=database_connected,
        active_websocket_connections=connection_manager.get_connection_count(),
        timestamp=datetime.now(timezone.utc).isoformat() + 'Z'
    )


# Dashboard route - serve the main interface
@app.get("/")
async def dashboard():
    """
    Serve the main dashboard interface.
    
    Returns the HTML dashboard for project management when accessed via browser.
    """
    from fastapi.responses import FileResponse
    
    dashboard_file = Path(__file__).parent / "static" / "index.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    else:
        return {"message": "Dashboard not available", "detail": "Static files not found"}


# WebSocket endpoint for real-time updates
@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    """Accept WebSocket connections and register with connection manager."""
    try:
        accepted = await connection_manager.connect(websocket)
        if not accepted:
            await websocket.close(code=1013)
            return
        # Keep the connection open; receive loop to handle client pings/messages
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                await connection_manager.disconnect(websocket)
                break
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await connection_manager.disconnect(websocket)
        except Exception:
            pass


# Board state endpoint - returns complete hierarchical project data
@app.get("/api/board/state", response_model=BoardStateResponse)
async def get_board_state(db: TaskDatabase = Depends(get_database)):
    """
    Get complete board state with all projects, epics, and tasks.
    
    Returns hierarchical project data for dashboard display including
    task lock status and all project entities.
    
    Returns:
        BoardStateResponse: Complete board state with tasks, epics, projects
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        # Fetch all data from database using new methods
        tasks = db.get_all_tasks()
        
        # Map database/internal statuses to UI vocabulary expected by the dashboard
        def to_ui_status(s: str) -> str:
            mapping = {
                'pending': 'TODO',
                'in_progress': 'IN_PROGRESS',
                'completed': 'DONE',
                'review': 'REVIEW',
                'blocked': 'BLOCKED',
                'backlog': 'BACKLOG',
                'TODO': 'TODO',
                'IN_PROGRESS': 'IN_PROGRESS',
                'DONE': 'DONE',
                'REVIEW': 'REVIEW',
                'BLOCKED': 'BLOCKED',
                'BACKLOG': 'BACKLOG'
            }
            return mapping.get(s, s)
        
        for t in tasks:
            if 'status' in t:
                t['status'] = to_ui_status(t['status'])
                
        epics = db.get_all_epics()
        projects = db.get_all_projects()
        
        logger.info(f"Board state: {len(projects)} projects, {len(epics)} epics, {len(tasks)} tasks")
        
        return BoardStateResponse(
            tasks=tasks,
            epics=epics,
            projects=projects
        )
        
    except Exception as e:
        logger.error(f"Failed to get board state: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve board state")


# Performance metrics endpoint for monitoring
@app.get("/api/metrics", response_model=MetricsResponse)
async def get_performance_metrics(db: TaskDatabase = Depends(get_database)):
    """
    Get comprehensive system performance metrics.
    
    Returns current system performance data including connection stats,
    task statistics, query performance, lock statistics, and system resource usage.
    
    Returns:
        MetricsResponse: Complete performance metrics
        
    Raises:
        HTTPException: 500 if metrics collection fails
    """
    try:
        # Collect system metrics using monitoring module
        system_metrics = performance_monitor.get_system_metrics(connection_manager, db)
        
        # Get connection statistics from optimized connection manager
        connection_stats = connection_manager.get_connection_stats()
        
        # Get lock statistics from database optimizer
        lock_stats = DatabaseOptimizer.get_lock_statistics(db)
        
        return MetricsResponse(
            connections={
                "active": system_metrics.active_connections,
                "healthy": connection_stats.get('healthy_connections', 0),
                "max_capacity": connection_stats.get('max_connections', 50),
                "total_broadcasts": connection_stats.get('total_broadcasts', 0),
                "avg_connection_age_seconds": connection_stats.get('avg_connection_age_seconds', 0.0)
            },
            tasks={
                "total": system_metrics.total_tasks,
                "locked": system_metrics.locked_tasks,
                "completed_today": system_metrics.completed_tasks_today,
                "available": lock_stats.get('available_tasks', 0)
            },
            performance={
                "avg_query_time_ms": system_metrics.avg_query_time_ms,
                "avg_broadcast_time_ms": system_metrics.avg_broadcast_time_ms,
                "avg_broadcast_per_connection_ms": connection_stats.get('avg_broadcast_time_ms', 0.0)
            },
            locks={
                "active": lock_stats.get('active_locks', 0),
                "expired": lock_stats.get('expired_locks', 0),
                "acquired_today": system_metrics.locks_acquired_today,
                "cleaned_today": system_metrics.expired_locks_cleaned,
                "conflicts": system_metrics.lock_conflicts,
                "utilization_percent": lock_stats.get('lock_utilization_percent', 0.0)
            },
            system={
                "memory_usage_mb": system_metrics.memory_usage_mb,
                "cpu_usage_percent": system_metrics.cpu_usage_percent,
                "last_lock_cleanup": system_metrics.last_lock_cleanup,
                "uptime_seconds": (datetime.now(timezone.utc) - performance_monitor.start_time).total_seconds()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")


# Task status update endpoint with lock validation
@app.post("/api/task/{task_id}/status", response_model=TaskStatusResponse)
async def update_task_status(
    task_id: int,
    update: TaskStatusUpdate,
    db: TaskDatabase = Depends(get_database)
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
                await connection_manager.optimized_broadcast({
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
            # #COMPLETION_DRIVE_INTEGRATION: Broadcasting after successful update for real-time UI updates
            await connection_manager.optimized_broadcast({
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
                        await connection_manager.optimized_broadcast({
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


# WebSocket endpoint for real-time updates
@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    """
    WebSocket endpoint for real-time event streaming.
    
    Accepts WebSocket connections and maintains them for broadcasting
    task status changes, lock acquisitions, and other real-time events.
    
    Connection lifecycle:
    1. Accept connection and add to active connections
    2. Keep connection alive with ping/pong handling
    3. Remove from active connections on disconnect
    
    Args:
        websocket: WebSocket connection from client
    """
    await connection_manager.connect(websocket)
    
    try:
        # Keep connection alive and handle client messages
        # #COMPLETION_DRIVE_IMPL: Client-to-server messaging not specified in requirements
        # but maintaining connection requires message loop
        while True:
            try:
                # Wait for client messages (ping/pong or other commands)
                data = await websocket.receive_text()
                
                # #SUGGEST_ERROR_HANDLING: Consider adding client command processing
                # Clients might send ping messages or other commands
                logger.debug(f"WebSocket received: {data}")
                
                # Echo back for connection health (optional)
                # await websocket.send_text(json.dumps({"type": "pong"}))
                
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    finally:
        await connection_manager.disconnect(websocket)


# Additional endpoints for lock management (bonus functionality)
@app.post("/api/task/{task_id}/lock")
async def acquire_task_lock(
    task_id: int,
    request: Dict[str, Any],  # {"agent_id": str, "duration_seconds": int}
    db: TaskDatabase = Depends(get_database)
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
                await connection_manager.optimized_broadcast({
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
            await connection_manager.optimized_broadcast({
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


@app.delete("/api/task/{task_id}/lock")
async def release_task_lock(
    task_id: int,
    request: Dict[str, str],  # {"agent_id": str}
    db: TaskDatabase = Depends(get_database)
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
            await connection_manager.optimized_broadcast({
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


# Standard Mode: New list endpoints mirroring MCP tools for frontend UI consumption
# Assumption: REST endpoints should return same data format as MCP tools for consistency

@app.get("/api/projects")
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


@app.get("/api/projects/{project_id}/epics") 
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


@app.get("/api/epics")
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


@app.get("/api/tasks/filtered")
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


# #COMPLETION_DRIVE_INTEGRATION: Task details endpoint to integrate with MCP get_task_details tool
# Assumption: Frontend modal needs comprehensive task details with RA metadata and logs
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


@app.post("/api/task/details")
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
        from .tools import GetTaskDetailsTool
        
        # Create tool instance with database dependency
        # #COMPLETION_DRIVE_INTEGRATION: Use existing MCP tool infrastructure
        task_details_tool = GetTaskDetailsTool(db, None)  # No websocket manager needed for readonly
        
        # Call the MCP tool with provided parameters
        # #SUGGEST_ERROR_HANDLING: MCP tool handles all validation and error cases internally
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


# Delete endpoints for project and epic management
@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: int,
    db: TaskDatabase = Depends(get_database)
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
            await connection_manager.broadcast({
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


@app.delete("/api/epics/{epic_id}")
async def delete_epic(
    epic_id: int,
    db: TaskDatabase = Depends(get_database)
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
            await connection_manager.broadcast({
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


@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: int,
    db: TaskDatabase = Depends(get_database)
):
    """
    Delete a task and all associated logs via CASCADE DELETE.
    
    Args:
        task_id: ID of the task to delete
        
    Returns:
        JSON response with deletion confirmation and statistics
    """
    try:
        result = db.delete_task(task_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=result["error"]
            )
        
        # Broadcast task deletion event to connected clients
        await connection_manager.broadcast({
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


@app.post("/api/cleanup/orphaned-tasks")
async def cleanup_orphaned_tasks(
    db: TaskDatabase = Depends(get_database)
):
    """
    Clean up orphaned tasks that have no associated epic or project.
    
    This is needed to fix tasks that were left behind when CASCADE DELETE
    wasn't working properly (before foreign keys were enabled).
    
    Returns:
        JSON response with cleanup statistics
    """
    try:
        result = db.cleanup_orphaned_tasks()
        
        if result["success"] and result["orphaned_tasks_removed"] > 0:
            # Broadcast cleanup event to refresh UI
            await connection_manager.broadcast({
                "type": "orphaned_tasks_cleaned",
                "tasks_removed": result["orphaned_tasks_removed"],
                "message": result["message"],
                "timestamp": datetime.now(timezone.utc).isoformat() + 'Z'
            })
            
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned tasks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup orphaned tasks: {str(e)}"
        )


# Error handlers for better API responses
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )




if __name__ == "__main__":
    # Development server startup
    import uvicorn
    
    # #COMPLETION_DRIVE_IMPL: Development configuration for local testing
    # Production deployment should use proper ASGI server configuration
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
