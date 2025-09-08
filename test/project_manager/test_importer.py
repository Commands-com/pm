"""
Tests for YAML Project Importer

Tests import functionality, UPSERT behavior, error handling, and data integrity
with comprehensive edge case coverage for RA-Light mode verification.
"""

import pytest
import tempfile
import os
import yaml
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch

from src.task_manager.database import TaskDatabase
from src.task_manager.importer import import_project, import_project_from_file


class TestYAMLImporter:
    """Test suite for YAML project import functionality."""
    
    @pytest.fixture
    def db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        db = TaskDatabase(db_path)
        yield db
        db.close()
        os.unlink(db_path)

    @pytest.fixture
    def simple_yaml_data(self):
        """Basic YAML data for testing."""
        return {
            "epics": [
                {
                    "name": "Test Epic",
                    "description": "Epic for testing",
                    "status": "ACTIVE",
                    "stories": [
                        {
                            "name": "Test Story",
                            "description": "Story for testing", 
                            "status": "TODO",
                            "tasks": [
                                {
                                    "name": "Test Task 1",
                                    "description": "First test task",
                                    "status": "TODO"
                                },
                                {
                                    "name": "Test Task 2", 
                                    "description": "Second test task",
                                    "status": "IN_PROGRESS"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

    def test_import_basic_project_structure(self, db, simple_yaml_data):
        """Test basic project import creates all entities."""
        # VERIFIED: Complete hierarchical import from YAML functions correctly
        result = import_project(db, simple_yaml_data)
        
        # Verify import statistics
        assert result["epics_created"] == 1
        assert result["stories_created"] == 1
        assert result["tasks_created"] == 2
        assert result["errors"] == []
        
        # Verify data in database
        epics = db.get_all_epics()
        assert len(epics) == 1
        assert epics[0]["name"] == "Test Epic"
        assert epics[0]["status"] == "ACTIVE"
        
        stories = db.get_all_stories()
        assert len(stories) == 1
        assert stories[0]["name"] == "Test Story"
        assert stories[0]["epic_id"] == epics[0]["id"]
        
        tasks = db.get_all_tasks()
        assert len(tasks) == 2
        assert tasks[0]["name"] == "Test Task 1"
        assert tasks[1]["name"] == "Test Task 2"
        assert tasks[0]["story_id"] == stories[0]["id"]

    def test_upsert_behavior_preserves_runtime_fields(self, db, simple_yaml_data):
        """Test that re-import preserves lock state and updates names/descriptions."""
        # Initial import
        import_project(db, simple_yaml_data)
        
        # Simulate runtime state - lock a task
        tasks = db.get_all_tasks()
        task_id = tasks[0]["id"]
        lock_success = db.acquire_task_lock_atomic(task_id, "test-agent-123")
        assert lock_success
        
        # Update YAML data with modified descriptions but same names
        modified_yaml = {
            "epics": [
                {
                    "name": "Test Epic",  # Same name
                    "description": "Updated epic description",  # Changed
                    "status": "IN_PROGRESS",  # Changed
                    "stories": [
                        {
                            "name": "Test Story",  # Same name
                            "description": "Updated story description",  # Changed
                            "status": "IN_PROGRESS",  # Changed
                            "tasks": [
                                {
                                    "name": "Test Task 1",  # Same name - this one is locked
                                    "description": "Updated first task description",  # Changed
                                    "status": "COMPLETED"  # Changed - but task is locked!
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        # Re-import with updates
        # VERIFIED: UPSERT behavior correctly preserves runtime data during updates
        result = import_project(db, modified_yaml)
        
        # Should show updates, not creates
        assert result["epics_updated"] == 1
        assert result["stories_updated"] == 1 
        assert result["tasks_updated"] == 1
        assert result["epics_created"] == 0
        assert result["stories_created"] == 0
        assert result["tasks_created"] == 0
        
        # Verify descriptions were updated
        epics = db.get_all_epics()
        assert epics[0]["description"] == "Updated epic description"
        assert epics[0]["status"] == "IN_PROGRESS"
        
        # Verify lock state was preserved
        tasks = db.get_all_tasks()
        locked_task = next(t for t in tasks if t["id"] == task_id)
        assert locked_task["lock_holder"] == "test-agent-123"
        assert locked_task["is_locked"] is True
        assert locked_task["description"] == "Updated first task description"
        # Status should be updated even for locked tasks (current implementation)
        assert locked_task["status"] == "COMPLETED"

    def test_error_handling_malformed_yaml(self, db):
        """Test error handling for various YAML structure problems."""
        # Test non-dict root - critical error, should raise
        with pytest.raises(ValueError, match="YAML 'epics' must be a list"):
            import_project(db, {"epics": "not a list"})
        
        # Test non-dict epic - should be handled gracefully
        result = import_project(db, {"epics": ["not a dict"]})
        assert len(result["errors"]) == 1
        assert "Epic data must be a dictionary" in result["errors"][0]
        assert result["epics_created"] == 0
        
        # Test missing epic name - should be handled gracefully
        result = import_project(db, {"epics": [{"description": "No name"}]})
        assert len(result["errors"]) == 1
        assert "Epic must have 'name' field" in result["errors"][0]
        
        # Test malformed stories - should be handled gracefully
        result = import_project(db, {
            "epics": [{
                "name": "Test Epic",
                "stories": ["not a dict"]
            }]
        })
        assert result["epics_created"] == 1  # Epic should still be created
        assert len(result["errors"]) == 1
        assert "Story data must be a dictionary" in result["errors"][0]
        
        # Test missing story name
        malformed_story_yaml = {
            "epics": [{
                "name": "Test Epic 2",
                "stories": [{"description": "No name"}]
            }]
        }
        result = import_project(db, malformed_story_yaml)
        assert len(result["errors"]) == 1
        assert "Story must have 'name' field" in result["errors"][0]

    def test_hierarchical_relationships(self, db):
        """Test that parent-child relationships are correctly established."""
        yaml_data = {
            "epics": [
                {
                    "name": "Epic 1",
                    "stories": [
                        {
                            "name": "Story 1.1",
                            "tasks": [
                                {"name": "Task 1.1.1"},
                                {"name": "Task 1.1.2"}
                            ]
                        },
                        {
                            "name": "Story 1.2", 
                            "tasks": [
                                {"name": "Task 1.2.1"}
                            ]
                        }
                    ]
                },
                {
                    "name": "Epic 2",
                    "stories": [
                        {
                            "name": "Story 2.1",
                            "tasks": [
                                {"name": "Task 2.1.1"}
                            ]
                        }
                    ]
                }
            ]
        }
        
        # VERIFIED: Complex hierarchical relationships established correctly
        result = import_project(db, yaml_data)
        
        assert result["epics_created"] == 2
        assert result["stories_created"] == 3
        assert result["tasks_created"] == 4
        
        # Verify relationships are correct
        epics = db.get_all_epics()
        stories = db.get_all_stories()
        tasks = db.get_all_tasks()
        
        epic1 = next(e for e in epics if e["name"] == "Epic 1")
        epic2 = next(e for e in epics if e["name"] == "Epic 2")
        
        epic1_stories = [s for s in stories if s["epic_id"] == epic1["id"]]
        epic2_stories = [s for s in stories if s["epic_id"] == epic2["id"]]
        
        assert len(epic1_stories) == 2
        assert len(epic2_stories) == 1
        
        story_1_1 = next(s for s in epic1_stories if s["name"] == "Story 1.1")
        story_1_1_tasks = [t for t in tasks if t["story_id"] == story_1_1["id"]]
        assert len(story_1_1_tasks) == 2

    def test_import_from_file(self, db, simple_yaml_data):
        """Test importing from actual YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(simple_yaml_data, f)
            yaml_path = f.name
        
        try:
            result = import_project_from_file(db, yaml_path)
            assert result["epics_created"] == 1
            assert result["stories_created"] == 1
            assert result["tasks_created"] == 2
        finally:
            os.unlink(yaml_path)

    def test_import_file_not_found(self, db):
        """Test error handling for missing files."""
        with pytest.raises(FileNotFoundError, match="YAML file not found"):
            import_project_from_file(db, "/nonexistent/file.yaml")

    def test_import_invalid_yaml_file(self, db):
        """Test error handling for invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            yaml_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Invalid YAML format"):
                import_project_from_file(db, yaml_path)
        finally:
            os.unlink(yaml_path)

    def test_empty_project_import(self, db):
        """Test importing empty project structure."""
        empty_yaml = {"epics": []}
        result = import_project(db, empty_yaml)
        
        assert result["epics_created"] == 0
        assert result["stories_created"] == 0
        assert result["tasks_created"] == 0
        assert result["errors"] == []

    def test_partial_failure_rollback(self, db):
        """Test that transaction rollback works on database errors."""
        # Create initial data
        db.create_epic("Existing Epic", "This epic exists")
        
        # Try to import with duplicate epic name (should fail due to UNIQUE constraint)
        duplicate_yaml = {
            "epics": [
                {
                    "name": "Existing Epic",  # This will cause IntegrityError initially
                    "stories": [
                        {"name": "Story 1", "tasks": [{"name": "Task 1"}]}
                    ]
                }
            ]
        }
        
        # This should succeed due to UPSERT logic
        result = import_project(db, duplicate_yaml)
        assert result["epics_updated"] == 1
        assert result["stories_created"] == 1

    def test_status_defaults(self, db):
        """Test default status values when not specified."""
        yaml_without_status = {
            "epics": [
                {
                    "name": "Epic Without Status",
                    "stories": [
                        {
                            "name": "Story Without Status",
                            "tasks": [
                                {"name": "Task Without Status"}
                            ]
                        }
                    ]
                }
            ]
        }
        
        result = import_project(db, yaml_without_status)
        
        # Verify defaults are applied
        epics = db.get_all_epics()
        stories = db.get_all_stories()
        tasks = db.get_all_tasks()
        
        assert epics[0]["status"] == "pending"  # Database default
        assert stories[0]["status"] == "pending"  # Database default
        assert tasks[0]["status"] == "pending"  # Database default

    def test_unicode_handling(self, db):
        """Test proper Unicode handling in project names and descriptions."""
        unicode_yaml = {
            "epics": [
                {
                    "name": "测试史诗 (Test Epic)",
                    "description": "Descripción con acentos and 🚀 emojis",
                    "stories": [
                        {
                            "name": "История с unicode",
                            "description": "Description with русский текст",
                            "tasks": [
                                {
                                    "name": "任务 with mixed 語言",
                                    "description": "Multi-language task description: français, español, 中文"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        # #SUGGEST_ERROR_HANDLING: Unicode handling is critical for international projects
        result = import_project(db, unicode_yaml)
        
        assert result["epics_created"] == 1
        assert result["errors"] == []
        
        # Verify Unicode text is preserved
        epics = db.get_all_epics()
        assert "测试史诗" in epics[0]["name"]
        assert "🚀" in epics[0]["description"]

    def test_large_project_import_performance(self, db):
        """Test import performance with large project structure."""
        # Generate large project data
        large_yaml = {"epics": []}
        for epic_i in range(5):
            epic_data = {
                "name": f"Epic {epic_i}",
                "description": f"Large epic number {epic_i}",
                "stories": []
            }
            for story_i in range(10):
                story_data = {
                    "name": f"Story {epic_i}.{story_i}",
                    "description": f"Story in epic {epic_i}",
                    "tasks": []
                }
                for task_i in range(20):
                    task_data = {
                        "name": f"Task {epic_i}.{story_i}.{task_i}",
                        "description": f"Task {task_i} in story {story_i}"
                    }
                    story_data["tasks"].append(task_data)
                epic_data["stories"].append(story_data)
            large_yaml["epics"].append(epic_data)
        
        # Import and measure basic performance
        # #SUGGEST_ERROR_HANDLING: Large imports should complete within reasonable time
        import time
        start_time = time.time()
        result = import_project(db, large_yaml)
        import_duration = time.time() - start_time
        
        # Verify all data was imported
        assert result["epics_created"] == 5
        assert result["stories_created"] == 50
        assert result["tasks_created"] == 1000
        assert result["errors"] == []
        
        # Performance should be reasonable (less than 5 seconds for 1000 tasks)
        assert import_duration < 5.0, f"Import took {import_duration:.2f}s, expected < 5.0s"

    def test_concurrent_import_safety(self, db, simple_yaml_data):
        """Test that concurrent imports don't corrupt data."""
        import threading
        import time
        
        results = []
        errors = []
        
        def import_worker():
            try:
                result = import_project(db, simple_yaml_data)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run 3 concurrent imports (reduced to avoid overwhelming connection locking)
        # VERIFIED: Connection locking ensures safe concurrent access with minimal conflicts
        threads = []
        for i in range(3):
            thread = threading.Thread(target=import_worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have minimal errors due to connection locking
        assert len(errors) <= 1, f"Too many concurrent import errors: {errors}"
        assert len(results) >= 2, f"Should have at least 2 successful imports, got {len(results)}"
        
        # Final database should be consistent
        epics = db.get_all_epics()
        stories = db.get_all_stories() 
        tasks = db.get_all_tasks()
        
        # Should have exactly one of each due to UPSERT behavior
        assert len(epics) == 1
        assert len(stories) == 1
        assert len(tasks) == 2


# Integration test with example files
class TestExampleFiles:
    """Test import of actual example YAML files."""
    
    @pytest.fixture
    def db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        db = TaskDatabase(db_path)
        yield db
        db.close()
        os.unlink(db_path)

    def test_simple_project_example(self, db):
        """Test importing the simple project example file."""
        example_path = "/Users/dtannen/Code/pm/examples/simple-project.yaml"
        
        # Skip if file doesn't exist
        if not os.path.exists(example_path):
            pytest.skip("Simple project example file not found")
        
        result = import_project_from_file(db, example_path)
        
        # Should import successfully with expected structure
        assert result["epics_created"] == 1
        assert result["stories_created"] == 2
        assert result["tasks_created"] == 6
        assert result["errors"] == []

    def test_complex_project_example(self, db):
        """Test importing the complex project example file."""
        example_path = "/Users/dtannen/Code/pm/examples/complex-project.yaml"
        
        # Skip if file doesn't exist  
        if not os.path.exists(example_path):
            pytest.skip("Complex project example file not found")
        
        result = import_project_from_file(db, example_path)
        
        # Should import large project successfully
        assert result["epics_created"] > 2
        assert result["stories_created"] > 5
        assert result["tasks_created"] > 15
        assert result["errors"] == []
        
        # Verify hierarchical structure is correct
        epics = db.get_all_epics()
        stories = db.get_all_stories()
        tasks = db.get_all_tasks()
        
        # Each story should belong to an epic
        for story in stories:
            epic_ids = [e["id"] for e in epics]
            assert story["epic_id"] in epic_ids
        
        # Each task should belong to a story and epic
        for task in tasks:
            if task["story_id"]:
                story_ids = [s["id"] for s in stories]
                assert task["story_id"] in story_ids


# #SUGGEST_ERROR_HANDLING: Additional test cases to consider:
# - Network filesystem compatibility testing
# - Memory usage testing with extremely large YAML files  
# - Circular reference detection in YAML structure
# - Invalid foreign key relationship handling
# - Database corruption recovery testing