"""
Unit tests for consensus caching layer.

Tests the ConsensusCache class with TTL, LRU eviction,
thread safety, and integration with consensus calculator.
"""

import pytest
import time
import threading
from unittest.mock import Mock
from src.task_manager.consensus_cache import ConsensusCache, CacheEntry, get_consensus_cache, reset_consensus_cache
from src.task_manager.consensus import ConsensusCalculator, ValidationInput
from src.task_manager.models import ConsensusResult, AgreementLevel


class TestConsensusCache:
    """Test suite for ConsensusCache class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = ConsensusCache(max_size=5, default_ttl=1)  # Small cache, short TTL for testing
        self.sample_result = ConsensusResult(
            consensus=0.8,
            overall_score=80,
            outcome="validated",
            agreement_level=AgreementLevel.STRONG,
            model_disagreement=False,
            total_validations=3,
            model_breakdown={"validated": 3, "rejected": 0, "partial": 0},
            weighted_confidence=0.85
        )

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        task_id = 123
        ra_tag_id = "tag_abc"

        # Cache miss initially
        result = self.cache.get(task_id, ra_tag_id)
        assert result is None

        # Set value
        self.cache.set(task_id, ra_tag_id, self.sample_result)

        # Cache hit
        result = self.cache.get(task_id, ra_tag_id)
        assert result is not None
        assert result.consensus == 0.8
        assert result.outcome == "validated"

    def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        task_id = 123
        ra_tag_id = "tag_abc"

        # Set with short TTL
        self.cache.set(task_id, ra_tag_id, self.sample_result, ttl=0.1)

        # Should be available immediately
        result = self.cache.get(task_id, ra_tag_id)
        assert result is not None

        # Wait for expiration
        time.sleep(0.2)

        # Should be expired now
        result = self.cache.get(task_id, ra_tag_id)
        assert result is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache exceeds max size."""
        # Fill cache to max size
        for i in range(5):
            self.cache.set(i, f"tag_{i}", self.sample_result)

        # All should be available
        for i in range(5):
            result = self.cache.get(i, f"tag_{i}")
            assert result is not None

        # Add one more item, should evict oldest (0)
        self.cache.set(5, "tag_5", self.sample_result)

        # Item 0 should be evicted
        result = self.cache.get(0, "tag_0")
        assert result is None

        # Items 1-5 should still be available
        for i in range(1, 6):
            result = self.cache.get(i, f"tag_{i}")
            assert result is not None

    def test_lru_access_pattern(self):
        """Test that accessing items affects LRU order."""
        # Fill cache
        for i in range(5):
            self.cache.set(i, f"tag_{i}", self.sample_result)

        # Access item 0 to make it most recently used
        self.cache.get(0, "tag_0")

        # Add new item, should evict item 1 (oldest non-accessed)
        self.cache.set(5, "tag_5", self.sample_result)

        # Item 0 should still be available (was accessed)
        result = self.cache.get(0, "tag_0")
        assert result is not None

        # Item 1 should be evicted
        result = self.cache.get(1, "tag_1")
        assert result is None

    def test_cache_invalidation(self):
        """Test manual cache invalidation."""
        task_id = 123
        ra_tag_id = "tag_abc"

        # Set and verify
        self.cache.set(task_id, ra_tag_id, self.sample_result)
        result = self.cache.get(task_id, ra_tag_id)
        assert result is not None

        # Invalidate
        was_invalidated = self.cache.invalidate(task_id, ra_tag_id)
        assert was_invalidated is True

        # Should be gone now
        result = self.cache.get(task_id, ra_tag_id)
        assert result is None

        # Invalidating non-existent entry
        was_invalidated = self.cache.invalidate(task_id, ra_tag_id)
        assert was_invalidated is False

    def test_task_invalidation(self):
        """Test invalidating all entries for a task."""
        task_id = 123

        # Set multiple entries for same task
        for i in range(3):
            self.cache.set(task_id, f"tag_{i}", self.sample_result)

        # Set entry for different task
        self.cache.set(456, "tag_other", self.sample_result)

        # Invalidate all for task 123
        count = self.cache.invalidate_task(task_id)
        assert count == 3

        # Task 123 entries should be gone
        for i in range(3):
            result = self.cache.get(task_id, f"tag_{i}")
            assert result is None

        # Other task should still be there
        result = self.cache.get(456, "tag_other")
        assert result is not None

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        # Add some entries
        for i in range(3):
            self.cache.set(i, f"tag_{i}", self.sample_result)

        # Clear all
        count = self.cache.clear()
        assert count == 3

        # All should be gone
        for i in range(3):
            result = self.cache.get(i, f"tag_{i}")
            assert result is None

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        # Add entries with different TTLs
        self.cache.set(1, "tag_1", self.sample_result, ttl=0.1)  # Short TTL
        self.cache.set(2, "tag_2", self.sample_result, ttl=10)   # Long TTL

        # Wait for first to expire
        time.sleep(0.2)

        # Cleanup expired
        count = self.cache.cleanup_expired()
        assert count == 1

        # First should be gone, second should remain
        assert self.cache.get(1, "tag_1") is None
        assert self.cache.get(2, "tag_2") is not None

    def test_cache_stats(self):
        """Test cache statistics tracking."""
        initial_stats = self.cache.get_stats()
        assert initial_stats["hits"] == 0
        assert initial_stats["misses"] == 0
        assert initial_stats["size"] == 0

        # Generate some cache activity
        self.cache.set(1, "tag_1", self.sample_result)
        self.cache.get(1, "tag_1")  # Hit
        self.cache.get(2, "tag_2")  # Miss

        stats = self.cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["total_requests"] == 2

    def test_memory_usage_estimation(self):
        """Test memory usage estimation."""
        initial_usage = self.cache.get_memory_usage()
        assert initial_usage["entries_count"] == 0

        # Add some entries
        for i in range(3):
            self.cache.set(i, f"tag_{i}", self.sample_result)

        usage = self.cache.get_memory_usage()
        assert usage["entries_count"] == 3
        assert usage["total_bytes"] > initial_usage["total_bytes"]
        assert usage["entries_bytes"] > 0
        assert usage["overhead_bytes"] > 0

    def test_thread_safety(self):
        """Test thread-safe operations."""
        num_threads = 10
        operations_per_thread = 20
        results = []
        errors = []

        def cache_operations(thread_id):
            try:
                for i in range(operations_per_thread):
                    key = f"thread_{thread_id}_item_{i}"
                    # Set
                    self.cache.set(thread_id, key, self.sample_result)
                    # Get
                    result = self.cache.get(thread_id, key)
                    results.append(result is not None)
                    # Invalidate some
                    if i % 3 == 0:
                        self.cache.invalidate(thread_id, key)
            except Exception as e:
                errors.append(e)

        # Start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=cache_operations, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check for errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Should have some successful operations
        assert len(results) > 0
        assert any(results)  # At least some gets should have succeeded

    def test_performance_benchmark(self):
        """Test cache performance under load."""
        import time

        num_operations = 1000

        # Measure set operations
        start_time = time.time()
        for i in range(num_operations):
            self.cache.set(i % 100, f"tag_{i}", self.sample_result)  # Reuse some keys
        set_time = time.time() - start_time

        # Measure get operations
        start_time = time.time()
        hits = 0
        for i in range(num_operations):
            result = self.cache.get(i % 100, f"tag_{i}")
            if result is not None:
                hits += 1
        get_time = time.time() - start_time

        # Performance assertions
        assert set_time < 0.1, f"Set operations took too long: {set_time:.3f}s"
        assert get_time < 0.1, f"Get operations took too long: {get_time:.3f}s"
        assert hits > 0, "Should have some cache hits"

        print(f"Performance: {num_operations} sets in {set_time:.3f}s, {num_operations} gets in {get_time:.3f}s, {hits} hits")


class TestConsensusCalculatorCaching:
    """Test cache integration with ConsensusCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_consensus_cache()  # Reset global cache
        self.calculator = ConsensusCalculator(use_cache=True)
        self.validations = [
            ValidationInput("claude-3-opus", "validated", 90),
            ValidationInput("gpt-4", "validated", 85),
            ValidationInput("gemini-pro", "rejected", 70)
        ]

    def test_caching_integration(self):
        """Test that calculator uses cache correctly."""
        task_id = 123
        ra_tag_id = "tag_abc"

        # First calculation should cache result
        result1 = self.calculator.calculate_consensus_cached(task_id, ra_tag_id, self.validations)

        # Second calculation should use cache
        result2 = self.calculator.calculate_consensus_cached(task_id, ra_tag_id, self.validations)

        # Results should be identical
        assert result1.consensus == result2.consensus
        assert result1.outcome == result2.outcome

        # Cache should show hits
        stats = self.calculator.get_cache_stats()
        assert stats is not None
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_cache_invalidation_integration(self):
        """Test cache invalidation through calculator."""
        task_id = 123
        ra_tag_id = "tag_abc"

        # Cache a result
        result1 = self.calculator.calculate_consensus_cached(task_id, ra_tag_id, self.validations)

        # Invalidate cache
        was_invalidated = self.calculator.invalidate_cache(task_id, ra_tag_id)
        assert was_invalidated is True

        # Next calculation should be a cache miss
        result2 = self.calculator.calculate_consensus_cached(task_id, ra_tag_id, self.validations)

        # Results should still be identical (same inputs)
        assert result1.consensus == result2.consensus

        # Cache should show additional miss
        stats = self.calculator.get_cache_stats()
        assert stats["misses"] == 2

    def test_cache_bypass(self):
        """Test calculator without caching."""
        calculator_no_cache = ConsensusCalculator(use_cache=False)

        # Should not use cache
        result = calculator_no_cache.calculate_consensus_cached(123, "tag_abc", self.validations)
        assert result is not None

        # Cache stats should be None
        stats = calculator_no_cache.get_cache_stats()
        assert stats is None

    def test_task_cache_invalidation(self):
        """Test invalidating all cache entries for a task."""
        task_id = 123

        # Cache multiple results for same task
        for i in range(3):
            ra_tag_id = f"tag_{i}"
            self.calculator.calculate_consensus_cached(task_id, ra_tag_id, self.validations)

        # Invalidate entire task
        count = self.calculator.invalidate_task_cache(task_id)
        assert count == 3

        # All should be cache misses now
        initial_misses = self.calculator.get_cache_stats()["misses"]
        for i in range(3):
            ra_tag_id = f"tag_{i}"
            self.calculator.calculate_consensus_cached(task_id, ra_tag_id, self.validations)

        # Should have 3 additional misses
        final_misses = self.calculator.get_cache_stats()["misses"]
        assert final_misses == initial_misses + 3


class TestGlobalCacheInstance:
    """Test global cache instance management."""

    def test_global_cache_singleton(self):
        """Test that global cache returns same instance."""
        cache1 = get_consensus_cache()
        cache2 = get_consensus_cache()
        assert cache1 is cache2

    def test_global_cache_reset(self):
        """Test resetting global cache instance."""
        cache1 = get_consensus_cache()
        reset_consensus_cache()
        cache2 = get_consensus_cache()
        assert cache1 is not cache2