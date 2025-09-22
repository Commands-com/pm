"""
Performance Optimization Utilities

Database query optimization, WebSocket broadcasting enhancements, and 
connection management utilities for high-performance operation under
concurrent agent workloads.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Set, Callable
from contextlib import asynccontextmanager
from functools import wraps

from .monitoring import performance_monitor

logger = logging.getLogger(__name__)


def timed_query(operation_name: str):
    """
    Decorator to measure and record database query execution times.
    
    Automatically tracks query performance for monitoring and optimization.
    
    Args:
        operation_name: Human-readable description of the database operation
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_query_time(operation_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_query_time(f"{operation_name}_ERROR", duration_ms)
                raise
        return wrapper
    return decorator


def timed_async_query(operation_name: str):
    """
    Async decorator to measure and record database query execution times.
    
    Args:
        operation_name: Human-readable description of the database operation
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_query_time(operation_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_query_time(f"{operation_name}_ERROR", duration_ms)
                raise
        return wrapper
    return decorator


class OptimizedConnectionManager:
    """
    Enhanced WebSocket connection manager with performance optimizations.
    
    Provides efficient broadcasting, connection health monitoring, and
    automatic cleanup of failed connections.
    """
    
    def __init__(self, max_connections: int = 100):
        self.active_connections: Set = set()
        # Dedicated planning-mode connections (do not receive general updates)
        self.planning_connections: Set = set()
        self.connection_health: Dict = {}
        self.max_connections = max_connections
        self._connection_lock = asyncio.Lock()
        self._broadcast_stats = {
            'total_broadcasts': 0,
            'failed_connections': 0,
            'avg_broadcast_time_ms': 0.0
        }
    
    async def connect(self, websocket) -> bool:
        """
        Accept WebSocket connection with capacity management.
        
        Args:
            websocket: WebSocket connection to accept
            
        Returns:
            bool: True if connection accepted, False if at capacity
        """
        async with self._connection_lock:
            if len(self.active_connections) >= self.max_connections:
                logger.warning(f"WebSocket connection rejected: at capacity ({self.max_connections})")
                return False
            
            await websocket.accept()
            self.active_connections.add(websocket)
            self.connection_health[websocket] = {
                'connected_at': time.time(),
                'last_successful_send': time.time(),
                'failed_sends': 0
            }
            
            logger.info(f"WebSocket connected. Total: {len(self.active_connections)}/{self.max_connections}")
            return True
    
    async def disconnect(self, websocket):
        """Remove WebSocket connection and cleanup health tracking."""
        async with self._connection_lock:
            self.active_connections.discard(websocket)
            # Ensure planning-only sockets are also cleaned up
            self.planning_connections.discard(websocket)
            self.connection_health.pop(websocket, None)
            
            logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def optimized_broadcast(self, event_data: Dict[str, Any]) -> Dict[str, int]:
        """
        High-performance parallel WebSocket broadcasting with health monitoring.
        
        Features:
        - Parallel message sending using asyncio.gather()
        - Automatic cleanup of failed connections
        - Performance monitoring and statistics
        - Connection health tracking
        
        Args:
            event_data: Event data to broadcast (JSON serializable)
            
        Returns:
            Dict with broadcast statistics
        """
        if not self.active_connections:
            return {'sent': 0, 'failed': 0, 'duration_ms': 0.0}
        
        start_time = time.time()
        
        # Create broadcast tasks for all connections
        broadcast_tasks = []
        connections_to_broadcast = list(self.active_connections)
        
        for websocket in connections_to_broadcast:
            task = self._safe_send_with_health_tracking(websocket, event_data)
            broadcast_tasks.append(task)
        
        # Execute all broadcasts in parallel
        results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)
        
        # Process results and update statistics
        successful_sends = sum(1 for result in results if result is True)
        failed_sends = len(results) - successful_sends
        duration_ms = (time.time() - start_time) * 1000
        
        # Update broadcast statistics
        self._broadcast_stats['total_broadcasts'] += 1
        self._broadcast_stats['failed_connections'] += failed_sends
        
        # Update rolling average of broadcast times
        current_avg = self._broadcast_stats['avg_broadcast_time_ms']
        total_broadcasts = self._broadcast_stats['total_broadcasts']
        self._broadcast_stats['avg_broadcast_time_ms'] = (
            (current_avg * (total_broadcasts - 1) + duration_ms) / total_broadcasts
        )
        
        # Record performance metrics
        performance_monitor.record_broadcast_time(len(connections_to_broadcast), duration_ms)
        
        logger.info(
            f"Broadcast completed: {successful_sends}/{len(connections_to_broadcast)} "
            f"successful in {duration_ms:.1f}ms"
        )
        
        return {
            'sent': successful_sends,
            'failed': failed_sends,
            'duration_ms': duration_ms
        }

    async def broadcast(self, event_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Compatibility wrapper to match simple ConnectionManager API.
        
        Tools expect a `broadcast` coroutine; delegate to optimized version.
        """
        return await self.optimized_broadcast(event_data)

    # --- Planning-mode specific API (parity with ConnectionManager) ---
    async def connect_planning(self, websocket) -> bool:
        """
        Accept a planning-mode WebSocket connection without registering it
        for general updates. Maintains separate planning connection set.
        """
        async with self._connection_lock:
            # Use same capacity guard across all connections
            total_connections = len(self.active_connections) + len(self.planning_connections)
            if total_connections >= self.max_connections:
                logger.warning(
                    f"Planning WebSocket connection rejected: at capacity ({self.max_connections})"
                )
                return False

            await websocket.accept()
            self.planning_connections.add(websocket)
            # Track health for planning sockets as well
            self.connection_health[websocket] = {
                'connected_at': time.time(),
                'last_successful_send': time.time(),
                'failed_sends': 0
            }
            logger.info(
                f"Planning WebSocket connected. Planning: {len(self.planning_connections)} "
                f"(Total: {len(self.active_connections)+len(self.planning_connections)}/{self.max_connections})"
            )
            return True

    async def disconnect_planning(self, websocket):
        """Remove planning-mode WebSocket from tracking sets."""
        await self.disconnect(websocket)

    async def broadcast_planning(self, event_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Broadcast event to planning-mode clients only using the same
        optimized parallel send and health tracking.
        """
        if not self.planning_connections:
            return {'sent': 0, 'failed': 0, 'duration_ms': 0.0}

        start_time = time.time()

        # Create broadcast tasks for planning connections
        broadcast_tasks = []
        connections_to_broadcast = list(self.planning_connections)

        for websocket in connections_to_broadcast:
            task = self._safe_send_with_health_tracking(websocket, event_data)
            broadcast_tasks.append(task)

        results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)

        successful_sends = sum(1 for result in results if result is True)
        failed_sends = len(results) - successful_sends
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Planning broadcast completed: {successful_sends}/{len(connections_to_broadcast)} "
            f"successful in {duration_ms:.1f}ms"
        )

        return {
            'sent': successful_sends,
            'failed': failed_sends,
            'duration_ms': duration_ms
        }
    
    async def _safe_send_with_health_tracking(self, websocket, event_data: Dict[str, Any]) -> bool:
        """
        Safely send message with connection health tracking.
        
        Args:
            websocket: WebSocket connection
            event_data: Data to send
            
        Returns:
            bool: True if successful, False if failed
        """
        try:
            import json
            message = json.dumps(event_data)
            await websocket.send_text(message)
            
            # Update health tracking on success
            if websocket in self.connection_health:
                self.connection_health[websocket]['last_successful_send'] = time.time()
                self.connection_health[websocket]['failed_sends'] = 0
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")
            
            # Update health tracking on failure
            if websocket in self.connection_health:
                self.connection_health[websocket]['failed_sends'] += 1
            
            # Remove unhealthy connection immediately to match expected semantics in tests
            await self.disconnect(websocket)
            return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics."""
        healthy_connections = sum(
            1 for health in self.connection_health.values()
            if health['failed_sends'] == 0
        )
        
        avg_connection_age = 0.0
        if self.connection_health:
            current_time = time.time()
            total_age = sum(
                current_time - health['connected_at']
                for health in self.connection_health.values()
            )
            avg_connection_age = total_age / len(self.connection_health)
        
        return {
            'active_connections': len(self.active_connections),
            'healthy_connections': healthy_connections,
            'max_connections': self.max_connections,
            'avg_connection_age_seconds': avg_connection_age,
            'total_broadcasts': self._broadcast_stats['total_broadcasts'],
            'failed_connections': self._broadcast_stats['failed_connections'],
            'avg_broadcast_time_ms': self._broadcast_stats['avg_broadcast_time_ms']
        }
    
    def get_connection_count(self) -> int:
        """Get current active connection count."""
        return len(self.active_connections)


class DatabaseOptimizer:
    """
    Database query optimization utilities and performance helpers.
    
    Provides optimized query patterns and performance monitoring for
    high-concurrency scenarios.
    """
    
    @staticmethod
    @timed_query("get_available_tasks_optimized")
    def get_available_tasks_optimized(database, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Optimized query for available tasks using performance indexes.
        
        Uses optimized WHERE clause ordering and LIMIT for better performance.
        
        Args:
            database: TaskDatabase instance
            limit: Maximum tasks to return
            
        Returns:
            List of available task dictionaries
        """
        current_time_str = database._get_current_time_str() if hasattr(database, '_get_current_time_str') else ""
        
        with database._connection_lock:
            cursor = database._connection.cursor()
            
            # Optimized query using covering indexes
            # Status filter first (most selective), then lock conditions
            query = """
                SELECT id, story_id, epic_id, name, description, status, created_at
                FROM tasks 
                WHERE status = 'pending'
                  AND (lock_holder IS NULL OR lock_expires_at < ?)
                ORDER BY created_at ASC
            """
            
            if limit:
                query += " LIMIT ?"
                cursor.execute(query, (current_time_str, limit))
            else:
                cursor.execute(query, (current_time_str,))
            
            rows = cursor.fetchall()
            
            # Log performance info for optimization
            logger.debug(f"Available tasks query returned {len(rows)} results")
            
            return [{
                "id": row[0],
                "story_id": row[1], 
                "epic_id": row[2],
                "name": row[3],
                "description": row[4],
                "status": row[5],
                "created_at": row[6]
            } for row in rows]
    
    @staticmethod
    @timed_query("batch_lock_cleanup") 
    def batch_lock_cleanup_optimized(database) -> int:
        """
        Optimized batch cleanup of expired locks.
        
        Uses efficient UPDATE with indexed WHERE clause for better performance
        under high concurrency.
        
        Args:
            database: TaskDatabase instance
            
        Returns:
            Number of locks cleaned up
        """
        current_time_str = database._get_current_time_str() if hasattr(database, '_get_current_time_str') else ""
        
        with database._connection_lock:
            cursor = database._connection.cursor()
            
            # Optimized cleanup using lock expiration index
            cursor.execute("""
                UPDATE tasks 
                SET lock_holder = NULL, 
                    lock_expires_at = NULL,
                    updated_at = ?
                WHERE lock_expires_at IS NOT NULL 
                  AND lock_expires_at < ?
            """, (current_time_str, current_time_str))
            
            cleanup_count = cursor.rowcount
            
            if cleanup_count > 0:
                logger.info(f"Batch cleaned up {cleanup_count} expired locks")
                performance_monitor.increment_daily_stat('locks_cleaned', cleanup_count)
            
            return cleanup_count
    
    @staticmethod
    @timed_query("get_lock_statistics")
    def get_lock_statistics(database) -> Dict[str, Any]:
        """
        Get comprehensive lock usage statistics for monitoring.
        
        Args:
            database: TaskDatabase instance
            
        Returns:
            Dictionary with lock statistics
        """
        current_time_str = database._get_current_time_str() if hasattr(database, '_get_current_time_str') else ""
        
        with database._connection_lock:
            cursor = database._connection.cursor()
            
            # Count active locks
            cursor.execute("""
                SELECT COUNT(*) FROM tasks 
                WHERE lock_holder IS NOT NULL 
                  AND lock_expires_at > ?
            """, (current_time_str,))
            active_locks = cursor.fetchone()[0]
            
            # Count expired locks
            cursor.execute("""
                SELECT COUNT(*) FROM tasks 
                WHERE lock_holder IS NOT NULL 
                  AND lock_expires_at <= ?
            """, (current_time_str,))
            expired_locks = cursor.fetchone()[0]
            
            # Count available tasks
            cursor.execute("""
                SELECT COUNT(*) FROM tasks 
                WHERE status = 'pending'
                  AND (lock_holder IS NULL OR lock_expires_at < ?)
            """, (current_time_str,))
            available_tasks = cursor.fetchone()[0]
            
            return {
                'active_locks': active_locks,
                'expired_locks': expired_locks,
                'available_tasks': available_tasks,
                'lock_utilization_percent': (
                    active_locks / max(active_locks + available_tasks, 1) * 100
                )
            }


@asynccontextmanager
async def performance_context(operation_name: str):
    """
    Async context manager for measuring operation performance.
    
    Usage:
        async with performance_context("complex_operation"):
            await do_complex_work()
    
    Args:
        operation_name: Name for performance tracking
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        performance_monitor.record_query_time(operation_name, duration_ms)


def create_optimized_connection_manager(max_connections: int = 50) -> OptimizedConnectionManager:
    """
    Factory function for creating optimized WebSocket connection manager.
    
    Args:
        max_connections: Maximum concurrent WebSocket connections
        
    Returns:
        OptimizedConnectionManager instance
    """
    return OptimizedConnectionManager(max_connections=max_connections)
