"""
Simple benchmark to test board state query performance.

Tests the optimized get_all_tasks(), get_all_epics(), and get_all_projects()
methods vs any previous approach.
"""

import time
from task_manager.database import TaskDatabase

def benchmark_board_state(db_path="test_benchmark.db"):
    """Benchmark board state retrieval."""
    # Clean up any existing database file
    import os
    if os.path.exists(db_path):
        os.remove(db_path)

    db = TaskDatabase(db_path)

    # Create test data
    print("Creating test data...")
    project_id = db.create_project("Benchmark Project", "Performance test")

    # Create 5 epics
    epic_ids = []
    for i in range(5):
        epic_id = db.create_epic(f"Epic {i+1}", f"Epic {i+1} description", project_id)
        epic_ids.append(epic_id)

    # Create 50 tasks (10 per epic)
    for epic_id in epic_ids:
        for j in range(10):
            db.create_task(
                name=f"Task {j+1} for Epic {epic_id}",
                description="Test task",
                epic_id=epic_id
            )

    print(f"Created {len(epic_ids)} epics and 50 tasks")

    # Benchmark the optimized queries
    print("\nBenchmarking optimized board state queries...")
    iterations = 100

    start = time.perf_counter()
    for _ in range(iterations):
        tasks = db.get_all_tasks()
        epics = db.get_all_epics()
        projects = db.get_all_projects()
    end = time.perf_counter()

    avg_time_ms = ((end - start) / iterations) * 1000

    print(f"\nResults:")
    print(f"  Iterations: {iterations}")
    print(f"  Total time: {(end - start):.4f}s")
    print(f"  Average time per board state fetch: {avg_time_ms:.4f}ms")
    print(f"  Tasks fetched: {len(tasks)}")
    print(f"  Epics fetched: {len(epics)}")
    print(f"  Projects fetched: {len(projects)}")

    # Verify data integrity
    assert len(tasks) == 50, f"Expected 50 tasks, got {len(tasks)}"
    assert len(epics) == 5, f"Expected 5 epics, got {len(epics)}"
    assert len(projects) == 1, f"Expected 1 project, got {len(projects)}"

    # Check that tasks have proper epic/project context
    task_with_context = tasks[0]
    assert "epic_name" in task_with_context, "Task missing epic_name"
    assert "project_name" in task_with_context, "Task missing project_name"

    print(f"\nData integrity verified")
    print(f"  Sample task has epic_name: {task_with_context.get('epic_name')}")
    print(f"  Sample task has project_name: {task_with_context.get('project_name')}")

    # Cleanup
    db.close()
    import os
    os.remove(db_path)

    print(f"\nBenchmark complete!")
    return avg_time_ms

if __name__ == "__main__":
    avg_time = benchmark_board_state()

    # Performance threshold check
    threshold_ms = 50  # Should be under 50ms for good performance
    if avg_time < threshold_ms:
        print(f"\n✓ Performance is good! ({avg_time:.2f}ms < {threshold_ms}ms threshold)")
    else:
        print(f"\n⚠ Performance could be improved ({avg_time:.2f}ms >= {threshold_ms}ms threshold)")
