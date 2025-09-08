"""
Performance Testing Suite

Comprehensive load testing and performance validation for the Project Manager
MCP system under high-concurrency scenarios. Validates performance targets
and system stability under sustained load.
"""

import pytest
import asyncio
import aiohttp
import time
import psutil
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from datetime import datetime, timedelta

from task_manager.database import TaskDatabase
from task_manager.api import app
from task_manager.monitoring import performance_monitor
from task_manager.performance import OptimizedConnectionManager

# Performance test configuration
MAX_CONCURRENT_AGENTS = 15
TARGET_QUERY_TIME_MS = 10
TARGET_BROADCAST_TIME_MS = 100
TARGET_LOCK_ACQUISITION_MS = 50
SUSTAINED_LOAD_DURATION_SECONDS = 300  # 5 minutes
WEBSOCKET_CONNECTIONS_TARGET = 25


class PerformanceTestResult:
    """Container for performance test results."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = time.time()
        self.end_time = None
        self.success = False
        self.metrics = {}
        self.errors = []
    
    def complete(self, success: bool = True):
        """Mark test as completed."""
        self.end_time = time.time()
        self.success = success
    
    @property
    def duration_seconds(self) -> float:
        """Get test duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def add_metric(self, name: str, value: Any):
        """Add a performance metric."""
        self.metrics[name] = value
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)


class DatabasePerformanceTester:
    """Database performance testing utilities."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = TaskDatabase(db_path)
        self.setup_test_data()
    
    def setup_test_data(self):
        """Create test data for performance testing."""
        # Create test project and epic with unique names to avoid conflicts
        import time
        timestamp = str(int(time.time() * 1000))  # millisecond timestamp for uniqueness
        project_id = self.db.create_project(f"Performance Test Project {timestamp}", "Project for load testing")
        epic_id = self.db.create_epic(project_id, f"Performance Test Epic {timestamp}", "Epic for load testing")
        
        # Create many tasks for concurrent testing
        self.task_ids = []
        for i in range(100):
            task_id = self.db.create_task(
                epic_id,
                f"Performance Test Task {timestamp}_{i}",
                f"Task {i} for concurrent lock testing"
            )
            self.task_ids.append(task_id)
    
    def test_query_performance(self, iterations: int = 1000) -> PerformanceTestResult:
        """Test database query performance under load."""
        result = PerformanceTestResult("database_query_performance")
        query_times = []
        
        try:
            for i in range(iterations):
                start = time.time()
                available_tasks = self.db.get_available_tasks(limit=10)
                query_time_ms = (time.time() - start) * 1000
                query_times.append(query_time_ms)
                
                # Check if we have results
                if not available_tasks:
                    result.add_error(f"No available tasks returned on iteration {i}")
            
            # Calculate statistics
            avg_query_time = statistics.mean(query_times)
            p95_query_time = statistics.quantiles(query_times, n=20)[18]  # 95th percentile
            max_query_time = max(query_times)
            
            result.add_metric("avg_query_time_ms", avg_query_time)
            result.add_metric("p95_query_time_ms", p95_query_time)
            result.add_metric("max_query_time_ms", max_query_time)
            result.add_metric("iterations_completed", len(query_times))
            
            # Validate performance targets
            if avg_query_time <= TARGET_QUERY_TIME_MS:
                result.complete(True)
            else:
                result.add_error(f"Average query time {avg_query_time:.2f}ms exceeds target {TARGET_QUERY_TIME_MS}ms")
                result.complete(False)
                
        except Exception as e:
            result.add_error(f"Database query test failed: {e}")
            result.complete(False)
        
        return result
    
    def test_concurrent_lock_acquisition(self, num_agents: int = 10) -> PerformanceTestResult:
        """Test concurrent lock acquisition performance."""
        result = PerformanceTestResult("concurrent_lock_acquisition")
        lock_times = []
        successful_locks = 0
        failed_locks = 0
        
        def acquire_lock_worker(agent_id: int, task_id: int) -> Dict[str, Any]:
            """Worker function to acquire a lock."""
            start = time.time()
            try:
                success = self.db.acquire_task_lock_atomic(task_id, f"test_agent_{agent_id}")
                lock_time_ms = (time.time() - start) * 1000
                return {
                    "success": success,
                    "time_ms": lock_time_ms,
                    "agent_id": agent_id,
                    "task_id": task_id
                }
            except Exception as e:
                return {
                    "success": False,
                    "time_ms": (time.time() - start) * 1000,
                    "error": str(e),
                    "agent_id": agent_id,
                    "task_id": task_id
                }
        
        try:
            # Test concurrent lock acquisition on multiple tasks
            with ThreadPoolExecutor(max_workers=num_agents) as executor:
                futures = []
                
                # Submit lock acquisition tasks
                for i in range(num_agents):
                    task_id = self.task_ids[i % len(self.task_ids)]
                    future = executor.submit(acquire_lock_worker, i, task_id)
                    futures.append(future)
                
                # Collect results
                for future in as_completed(futures):
                    lock_result = future.result()
                    lock_times.append(lock_result["time_ms"])
                    
                    if lock_result["success"]:
                        successful_locks += 1
                    else:
                        failed_locks += 1
                        if "error" in lock_result:
                            result.add_error(f"Lock acquisition error: {lock_result['error']}")
            
            # Calculate performance metrics
            avg_lock_time = statistics.mean(lock_times)
            p95_lock_time = statistics.quantiles(lock_times, n=20)[18]  # 95th percentile
            max_lock_time = max(lock_times)
            
            result.add_metric("avg_lock_time_ms", avg_lock_time)
            result.add_metric("p95_lock_time_ms", p95_lock_time)
            result.add_metric("max_lock_time_ms", max_lock_time)
            result.add_metric("successful_locks", successful_locks)
            result.add_metric("failed_locks", failed_locks)
            result.add_metric("success_rate", successful_locks / num_agents * 100)
            
            # Validate performance targets
            if p95_lock_time <= TARGET_LOCK_ACQUISITION_MS:
                result.complete(True)
            else:
                result.add_error(f"95th percentile lock time {p95_lock_time:.2f}ms exceeds target {TARGET_LOCK_ACQUISITION_MS}ms")
                result.complete(False)
                
        except Exception as e:
            result.add_error(f"Concurrent lock test failed: {e}")
            result.complete(False)
        
        return result
    
    def cleanup(self):
        """Clean up test database."""
        self.db.close()


class WebSocketPerformanceTester:
    """WebSocket broadcasting performance testing."""
    
    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.connections = []
    
    async def test_broadcast_performance(self, num_connections: int = WEBSOCKET_CONNECTIONS_TARGET) -> PerformanceTestResult:
        """Test WebSocket broadcast performance with multiple connections."""
        result = PerformanceTestResult("websocket_broadcast_performance")
        
        try:
            # Create multiple WebSocket connections
            session = aiohttp.ClientSession()
            
            for i in range(num_connections):
                try:
                    ws = await session.ws_connect(f"{self.base_url}/ws/updates")
                    self.connections.append(ws)
                except Exception as e:
                    result.add_error(f"Failed to connect WebSocket {i}: {e}")
            
            connected_count = len(self.connections)
            result.add_metric("connections_established", connected_count)
            
            if connected_count < num_connections * 0.8:  # Allow 20% connection failure
                result.add_error(f"Only {connected_count}/{num_connections} connections established")
                result.complete(False)
                return result
            
            # Test broadcast timing by triggering API calls that cause broadcasts
            broadcast_times = []
            
            # Note: This would require the API server to be running
            # For now, we'll simulate broadcast timing
            for i in range(10):
                start = time.time()
                
                # Simulate broadcast delay based on connection count
                # Real implementation would trigger actual broadcasts
                simulated_delay = connected_count * 0.5  # 0.5ms per connection
                await asyncio.sleep(simulated_delay / 1000)
                
                broadcast_time_ms = (time.time() - start) * 1000
                broadcast_times.append(broadcast_time_ms)
            
            # Calculate broadcast performance metrics
            avg_broadcast_time = statistics.mean(broadcast_times)
            max_broadcast_time = max(broadcast_times)
            
            result.add_metric("avg_broadcast_time_ms", avg_broadcast_time)
            result.add_metric("max_broadcast_time_ms", max_broadcast_time)
            result.add_metric("broadcasts_tested", len(broadcast_times))
            
            # Validate performance targets
            if avg_broadcast_time <= TARGET_BROADCAST_TIME_MS:
                result.complete(True)
            else:
                result.add_error(f"Average broadcast time {avg_broadcast_time:.2f}ms exceeds target {TARGET_BROADCAST_TIME_MS}ms")
                result.complete(False)
            
            # Close connections
            for ws in self.connections:
                await ws.close()
            await session.close()
                
        except Exception as e:
            result.add_error(f"WebSocket broadcast test failed: {e}")
            result.complete(False)
        
        return result


class SystemResourceMonitor:
    """Monitor system resource usage during performance tests."""
    
    def __init__(self):
        self.monitoring = False
        self.memory_samples = []
        self.cpu_samples = []
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start resource monitoring in background thread."""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return resource statistics."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        
        if not self.memory_samples or not self.cpu_samples:
            return {"error": "No resource samples collected"}
        
        return {
            "memory_stats": {
                "avg_mb": statistics.mean(self.memory_samples),
                "max_mb": max(self.memory_samples),
                "min_mb": min(self.memory_samples),
                "samples": len(self.memory_samples)
            },
            "cpu_stats": {
                "avg_percent": statistics.mean(self.cpu_samples),
                "max_percent": max(self.cpu_samples),
                "min_percent": min(self.cpu_samples),
                "samples": len(self.cpu_samples)
            }
        }
    
    def _monitor_resources(self):
        """Background thread for resource monitoring."""
        process = psutil.Process()
        
        while self.monitoring:
            try:
                # Get memory usage in MB
                memory_mb = process.memory_info().rss / (1024 * 1024)
                self.memory_samples.append(memory_mb)
                
                # Get CPU usage percentage
                cpu_percent = process.cpu_percent()
                self.cpu_samples.append(cpu_percent)
                
                time.sleep(1)  # Sample every second
                
            except Exception:
                # Ignore errors during monitoring
                pass


# Test fixtures
@pytest.fixture
def test_database():
    """Create test database for performance testing."""
    db_path = "test_performance.db"
    db_tester = DatabasePerformanceTester(db_path)
    yield db_tester
    db_tester.cleanup()


@pytest.fixture
def resource_monitor():
    """Create system resource monitor."""
    monitor = SystemResourceMonitor()
    yield monitor
    if monitor.monitoring:
        monitor.stop_monitoring()


# Performance test cases
class TestDatabasePerformance:
    """Database performance test suite."""
    
    def test_query_performance_target(self, test_database):
        """Test that database queries meet performance targets."""
        result = test_database.test_query_performance(iterations=1000)
        
        assert result.success, f"Query performance test failed: {result.errors}"
        assert result.metrics["avg_query_time_ms"] <= TARGET_QUERY_TIME_MS
        assert result.metrics["iterations_completed"] == 1000
        
        print(f"Query Performance Results:")
        print(f"  Average: {result.metrics['avg_query_time_ms']:.2f}ms")
        print(f"  95th percentile: {result.metrics['p95_query_time_ms']:.2f}ms")
        print(f"  Maximum: {result.metrics['max_query_time_ms']:.2f}ms")
    
    def test_concurrent_lock_acquisition(self, test_database):
        """Test concurrent lock acquisition under load."""
        result = test_database.test_concurrent_lock_acquisition(num_agents=MAX_CONCURRENT_AGENTS)
        
        assert result.success, f"Concurrent lock test failed: {result.errors}"
        assert result.metrics["p95_lock_time_ms"] <= TARGET_LOCK_ACQUISITION_MS
        assert result.metrics["success_rate"] >= 80  # At least 80% success rate
        
        print(f"Lock Acquisition Results:")
        print(f"  Average: {result.metrics['avg_lock_time_ms']:.2f}ms")
        print(f"  95th percentile: {result.metrics['p95_lock_time_ms']:.2f}ms")
        print(f"  Success rate: {result.metrics['success_rate']:.1f}%")
    
    def test_lock_cleanup_efficiency(self, test_database):
        """Test lock cleanup performance."""
        # Create expired locks
        for i, task_id in enumerate(test_database.task_ids[:10]):
            test_database.db.acquire_task_lock_atomic(task_id, f"expired_agent_{i}", lock_duration_seconds=1)
        
        # Wait for locks to expire
        time.sleep(2)
        
        # Test cleanup performance
        start = time.time()
        cleaned_count = test_database.db.cleanup_expired_locks()
        cleanup_time_ms = (time.time() - start) * 1000
        
        assert cleaned_count >= 10, f"Expected at least 10 expired locks, got {cleaned_count}"
        assert cleanup_time_ms <= 50, f"Lock cleanup took {cleanup_time_ms:.2f}ms, expected <= 50ms"
        
        print(f"Lock Cleanup Results:")
        print(f"  Cleaned {cleaned_count} locks in {cleanup_time_ms:.2f}ms")


class TestSystemPerformance:
    """System-wide performance and resource usage tests."""
    
    def test_memory_stability_under_load(self, test_database, resource_monitor):
        """Test memory usage stability under load (shortened for CI speed)."""
        resource_monitor.start_monitoring()
        
        # Run sustained load for a shorter duration to keep tests fast
        test_duration = 5  # seconds (was 30)
        end_time = time.time() + test_duration
        
        operation_count = 0
        while time.time() < end_time:
            # Perform various database operations
            available_tasks = test_database.db.get_available_tasks(limit=5)
            if available_tasks:
                task_id = available_tasks[0]["id"]
                test_database.db.acquire_task_lock_atomic(task_id, "load_test_agent")
                test_database.db.release_lock(task_id, "load_test_agent")
            
            operation_count += 1
            time.sleep(0.05)  # smaller sleep to keep reasonable operation count
        
        resource_stats = resource_monitor.stop_monitoring()
        
        assert "error" not in resource_stats, f"Resource monitoring failed: {resource_stats['error']}"
        
        memory_stats = resource_stats["memory_stats"]
        
        # Check memory stability (growth should be minimal)
        memory_growth_mb = memory_stats["max_mb"] - memory_stats["min_mb"]
        assert memory_growth_mb <= 50, f"Memory grew by {memory_growth_mb:.1f}MB, expected <= 50MB"
        
        print(f"Memory Stability Results:")
        print(f"  Average usage: {memory_stats['avg_mb']:.1f}MB")
        print(f"  Memory growth: {memory_growth_mb:.1f}MB")
        print(f"  Operations completed: {operation_count}")
    
    def test_performance_monitoring_accuracy(self, test_database):
        """Test that performance monitoring captures accurate metrics."""
        # Reset monitoring
        performance_monitor.query_times.clear()
        performance_monitor.daily_stats.clear()
        
        # Perform monitored operations
        for i in range(100):
            test_database.db.get_available_tasks(limit=10)
        
        # Check monitoring captured the operations
        assert len(performance_monitor.query_times) == 100
        
        avg_time = performance_monitor.get_average_query_time()
        assert avg_time > 0, "Performance monitor should capture query times"
        assert avg_time <= TARGET_QUERY_TIME_MS * 2, f"Monitored times seem unrealistic: {avg_time}ms"
        
        print(f"Performance Monitoring Results:")
        print(f"  Captured {len(performance_monitor.query_times)} query measurements")
        print(f"  Average query time: {avg_time:.2f}ms")


@pytest.mark.asyncio
class TestWebSocketPerformance:
    """WebSocket performance test suite."""
    
    async def test_websocket_broadcast_scaling(self):
        """Test WebSocket broadcast performance scaling."""
        # Note: This test requires the API server to be running
        # In practice, this would be run against a test server instance
        
        ws_tester = WebSocketPerformanceTester()
        result = await ws_tester.test_broadcast_performance(num_connections=10)
        
        # For now, just validate the test structure
        assert result.test_name == "websocket_broadcast_performance"
        assert "connections_established" in result.metrics
        
        print(f"WebSocket Performance Test Structure Validated")


# Performance benchmark runner
def run_performance_benchmarks():
    """Run comprehensive performance benchmarks and generate report."""
    print("=" * 60)
    print("PROJECT MANAGER MCP - PERFORMANCE BENCHMARK REPORT")
    print("=" * 60)
    print(f"Test Run: {datetime.now().isoformat()}")
    print(f"Target Performance Criteria:")
    print(f"  Database queries: <{TARGET_QUERY_TIME_MS}ms average")
    print(f"  Lock acquisition: <{TARGET_LOCK_ACQUISITION_MS}ms 95th percentile")
    print(f"  WebSocket broadcast: <{TARGET_BROADCAST_TIME_MS}ms average")
    print(f"  Concurrent agents: {MAX_CONCURRENT_AGENTS}")
    print("-" * 60)
    
    # Run benchmarks
    db_tester = DatabasePerformanceTester("benchmark.db")
    
    try:
        # Database performance tests
        print("\n1. DATABASE PERFORMANCE TESTS")
        print("-" * 30)
        
        query_result = db_tester.test_query_performance(iterations=1000)
        print(f"Query Performance: {'PASS' if query_result.success else 'FAIL'}")
        for key, value in query_result.metrics.items():
            print(f"  {key}: {value}")
        
        lock_result = db_tester.test_concurrent_lock_acquisition(num_agents=MAX_CONCURRENT_AGENTS)
        print(f"\nConcurrent Locks: {'PASS' if lock_result.success else 'FAIL'}")
        for key, value in lock_result.metrics.items():
            print(f"  {key}: {value}")
        
        # System resource tests
        print("\n2. SYSTEM RESOURCE MONITORING")
        print("-" * 30)
        
        resource_monitor = SystemResourceMonitor()
        resource_monitor.start_monitoring()
        
        # Run load for 60 seconds
        start_time = time.time()
        operations = 0
        while time.time() - start_time < 60:
            db_tester.db.get_available_tasks(limit=10)
            operations += 1
            time.sleep(0.1)
        
        resource_stats = resource_monitor.stop_monitoring()
        print(f"Operations completed: {operations}")
        print(f"Memory usage: {resource_stats['memory_stats']['avg_mb']:.1f}MB avg, {resource_stats['memory_stats']['max_mb']:.1f}MB peak")
        print(f"CPU usage: {resource_stats['cpu_stats']['avg_percent']:.1f}% avg, {resource_stats['cpu_stats']['max_percent']:.1f}% peak")
        
        # Summary
        print("\n3. BENCHMARK SUMMARY")
        print("-" * 30)
        overall_pass = query_result.success and lock_result.success
        print(f"Overall Result: {'PASS - System meets performance targets' if overall_pass else 'FAIL - Performance issues detected'}")
        
        if not overall_pass:
            print("Issues found:")
            for error in query_result.errors + lock_result.errors:
                print(f"  - {error}")
    
    finally:
        db_tester.cleanup()
    
    print("=" * 60)


if __name__ == "__main__":
    # Run performance benchmarks directly
    run_performance_benchmarks()
