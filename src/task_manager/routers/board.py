"""
Board State and Metrics Router

Provides endpoints for complete board state (OPTIMIZED!) and performance metrics.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..database import TaskDatabase
from ..monitoring import performance_monitor
from ..performance import DatabaseOptimizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["board"])


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


@router.get("/board/state", response_model=BoardStateResponse)
async def get_board_state(db: TaskDatabase = Depends(get_database)):
    """
    Get complete board state with all projects, epics, and tasks.

    **OPTIMIZED VERSION** - Uses single JOIN query instead of N+1 pattern!

    Returns hierarchical project data for dashboard display including
    task lock status and all project entities in one efficient query.

    Returns:
        BoardStateResponse: Complete board state with tasks, epics, projects

    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        # Use the new optimized method that does a single JOIN query
        board_data = db.get_board_state_optimized()

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

        # Map task statuses to UI vocabulary
        for t in board_data['tasks']:
            if 'status' in t:
                t['status'] = to_ui_status(t['status'])

        logger.info(f"Board state (OPTIMIZED): {len(board_data['projects'])} projects, "
                   f"{len(board_data['epics'])} epics, {len(board_data['tasks'])} tasks")

        return BoardStateResponse(
            tasks=board_data['tasks'],
            epics=board_data['epics'],
            projects=board_data['projects']
        )

    except Exception as e:
        logger.error(f"Failed to get board state: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve board state")


@router.get("/metrics", response_model=MetricsResponse)
async def get_performance_metrics(
    db: TaskDatabase = Depends(get_database),
    conn_mgr = Depends(get_connection_manager)
):
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
        system_metrics = performance_monitor.get_system_metrics(conn_mgr, db)

        # Get connection statistics from optimized connection manager
        connection_stats = conn_mgr.get_connection_stats()

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
