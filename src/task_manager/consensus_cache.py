"""
Multi-Model Consensus Caching Layer

Provides intelligent caching for consensus calculations with TTL,
LRU eviction, and thread-safe operations for performance optimization.
"""

import time
import threading
from typing import Optional, Dict, Tuple, Any
from dataclasses import dataclass
from collections import OrderedDict
import logging
from .models import ConsensusResult

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL and access tracking."""

    value: ConsensusResult
    created_at: float
    last_accessed: float
    ttl_seconds: int = 300  # 5 minutes default


class ConsensusCache:
    """
    Thread-safe LRU cache with TTL for consensus calculation results.

    Features:
    - 5-minute TTL for consensus results
    - LRU eviction when cache exceeds size limit
    - Thread-safe operations for concurrent access
    - Automatic invalidation on new validations
    - Performance metrics tracking
    """

    def __init__(self, max_size: int = 2000, default_ttl: int = 300):
        """
        Initialize consensus cache with performance optimizations.

        #COMPLETION_DRIVE_IMPL: Tuned cache parameters for multi-model performance requirements
        Increased cache size to 2000 entries to support higher concurrent usage with
        P95 < 500ms response time requirements.

        Args:
            max_size: Maximum number of cache entries (LRU eviction) - increased to 2000
            default_ttl: Default TTL in seconds (5 minutes = 300s)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()  # Reentrant lock for nested operations

        # Performance metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0

    def _generate_cache_key(self, task_id: int, ra_tag_id: str) -> str:
        """Generate cache key for consensus result."""
        return f"consensus:{task_id}:{ra_tag_id}"

    def get(self, task_id: int, ra_tag_id: str) -> Optional[ConsensusResult]:
        """
        Retrieve cached consensus result if available and not expired.

        Args:
            task_id: Task ID for the consensus
            ra_tag_id: RA tag ID for the consensus

        Returns:
            ConsensusResult if cached and valid, None otherwise
        """
        cache_key = self._generate_cache_key(task_id, ra_tag_id)

        with self._lock:
            entry = self._cache.get(cache_key)

            if entry is None:
                self._misses += 1
                logger.debug(f"Cache miss for key: {cache_key}")
                return None

            # Check TTL expiration
            current_time = time.time()
            if current_time - entry.created_at > entry.ttl_seconds:
                # Entry expired, remove it
                del self._cache[cache_key]
                self._misses += 1
                logger.debug(f"Cache entry expired for key: {cache_key}")
                return None

            # Update access time and move to end (LRU)
            entry.last_accessed = current_time
            self._cache.move_to_end(cache_key)

            self._hits += 1
            logger.debug(f"Cache hit for key: {cache_key}")
            return entry.value

    def set(self, task_id: int, ra_tag_id: str, consensus_result: ConsensusResult,
            ttl: Optional[int] = None) -> None:
        """
        Store consensus result in cache with TTL.

        Args:
            task_id: Task ID for the consensus
            ra_tag_id: RA tag ID for the consensus
            consensus_result: ConsensusResult to cache
            ttl: Custom TTL in seconds, uses default if None
        """
        cache_key = self._generate_cache_key(task_id, ra_tag_id)
        current_time = time.time()

        entry = CacheEntry(
            value=consensus_result,
            created_at=current_time,
            last_accessed=current_time,
            ttl_seconds=ttl or self.default_ttl
        )

        with self._lock:
            # Add/update entry
            self._cache[cache_key] = entry
            self._cache.move_to_end(cache_key)  # Mark as most recently used

            # Enforce size limit with LRU eviction
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
                logger.debug(f"Evicted oldest cache entry: {oldest_key}")

        logger.debug(f"Cached consensus result for key: {cache_key}, TTL: {entry.ttl_seconds}s")

    def invalidate(self, task_id: int, ra_tag_id: str) -> bool:
        """
        Invalidate specific cache entry.

        Args:
            task_id: Task ID for the consensus
            ra_tag_id: RA tag ID for the consensus

        Returns:
            True if entry was found and removed, False otherwise
        """
        cache_key = self._generate_cache_key(task_id, ra_tag_id)

        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                self._invalidations += 1
                logger.debug(f"Invalidated cache entry: {cache_key}")
                return True

        return False

    def invalidate_task(self, task_id: int) -> int:
        """
        Invalidate all cache entries for a specific task.

        Args:
            task_id: Task ID to invalidate

        Returns:
            Number of entries invalidated
        """
        prefix = f"consensus:{task_id}:"
        keys_to_remove = []

        with self._lock:
            for key in self._cache:
                if key.startswith(prefix):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._cache[key]
                self._invalidations += 1

        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for task {task_id}")
        return len(keys_to_remove)

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._invalidations += count

        logger.info(f"Cleared all {count} cache entries")
        return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of expired entries removed
        """
        current_time = time.time()
        expired_keys = []

        with self._lock:
            for key, entry in self._cache.items():
                if current_time - entry.created_at > entry.ttl_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests) if total_requests > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "evictions": self._evictions,
                "invalidations": self._invalidations,
                "total_requests": total_requests
            }

    def get_memory_usage(self) -> Dict[str, int]:
        """
        Estimate memory usage of cache.

        Returns:
            Dictionary with memory usage estimates in bytes
        """
        import sys

        with self._lock:
            # Rough estimation of memory usage
            entries_size = sum(
                sys.getsizeof(key) + sys.getsizeof(entry) + sys.getsizeof(entry.value)
                for key, entry in self._cache.items()
            )

            overhead_size = sys.getsizeof(self._cache) + sys.getsizeof(self._lock)
            total_size = entries_size + overhead_size

            return {
                "entries_bytes": entries_size,
                "overhead_bytes": overhead_size,
                "total_bytes": total_size,
                "entries_count": len(self._cache)
            }

    def warm_cache(self, task_ra_pairs: list[tuple[int, str]],
                   consensus_calculator, database) -> int:
        """
        Warm cache with pre-calculated consensus results for frequently accessed data.

        #COMPLETION_DRIVE_IMPL: Cache warming strategy for improved P95 response times
        Pre-populates cache with consensus calculations for active tasks to reduce
        cold start latency and improve API response time performance.

        Args:
            task_ra_pairs: List of (task_id, ra_tag_id) tuples to warm
            consensus_calculator: ConsensusCalculator instance
            database: TaskDatabase instance for querying validations

        Returns:
            Number of cache entries warmed
        """
        warmed_count = 0

        for task_id, ra_tag_id in task_ra_pairs:
            try:
                # Check if already cached
                if self.get(task_id, ra_tag_id) is not None:
                    continue

                # Query validations from database
                with database._connection_lock:
                    cursor = database._connection.cursor()
                    cursor.execute("""
                        SELECT outcome, confidence, validator_id
                        FROM assumption_validations
                        WHERE task_id = ? AND ra_tag_id = ?
                        ORDER BY validated_at ASC
                    """, (task_id, ra_tag_id))

                    validations_data = cursor.fetchall()

                if validations_data:
                    # Calculate consensus and cache it
                    from .consensus import ValidationInput
                    validations = [
                        ValidationInput(outcome=row[0], confidence=row[1], validator_id=row[2])
                        for row in validations_data
                    ]

                    consensus_result = consensus_calculator.calculate_consensus(validations)
                    self.set(task_id, ra_tag_id, consensus_result)
                    warmed_count += 1

            except Exception as e:
                logger.warning(f"Failed to warm cache for task {task_id}, tag {ra_tag_id}: {e}")
                continue

        logger.info(f"Cache warming completed: {warmed_count} entries pre-calculated")
        return warmed_count


# Global cache instance for the application
_consensus_cache: Optional[ConsensusCache] = None


def get_consensus_cache() -> ConsensusCache:
    """Get or create the global consensus cache instance.

    Respects environment variables for configuration:
    - CONSENSUS_CACHE_MAX_SIZE (int, default 2000)
    - CONSENSUS_CACHE_TTL_SECONDS (int, default 300)
    """
    import os
    global _consensus_cache

    if _consensus_cache is None:
        try:
            max_size = int(os.getenv("CONSENSUS_CACHE_MAX_SIZE", "2000"))
        except ValueError:
            max_size = 2000
        try:
            ttl = int(os.getenv("CONSENSUS_CACHE_TTL_SECONDS", "300"))
        except ValueError:
            ttl = 300

        _consensus_cache = ConsensusCache(max_size=max_size, default_ttl=ttl)
        logger.info(f"Initialized global consensus cache (max_size={max_size}, ttl={ttl}s)")

    return _consensus_cache


def reset_consensus_cache() -> None:
    """Reset the global consensus cache (primarily for testing)."""
    global _consensus_cache
    _consensus_cache = None
    logger.info("Reset global consensus cache")
