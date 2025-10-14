"""
Health Check Router

Provides health check endpoint for monitoring and load balancers.
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..database import TaskDatabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    database_connected: bool
    active_websocket_connections: int
    timestamp: str


def get_database() -> TaskDatabase:
    """FastAPI dependency to provide database instance."""
    from ..api import db_instance
    from fastapi import HTTPException

    if db_instance is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return db_instance


def get_connection_manager():
    """FastAPI dependency to provide connection manager instance."""
    from ..api import connection_manager
    return connection_manager


@router.get("/healthz", response_model=HealthResponse)
async def health_check(
    db: TaskDatabase = Depends(get_database),
    conn_mgr = Depends(get_connection_manager)
):
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
        active_websocket_connections=conn_mgr.get_connection_count(),
        timestamp=datetime.now(timezone.utc).isoformat() + 'Z'
    )
