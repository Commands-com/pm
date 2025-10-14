"""
Task Database Layer - Refactored Module Structure

This package provides SQLite-based database operations organized into
focused repository modules for better maintainability:

- connection.py: Database connection and schema management
- locks.py: Atomic task locking for agent coordination
- sessions.py: Dashboard session and event management
- projects.py: Project and epic CRUD operations
- tasks.py: Task operations with RA metadata support
- knowledge.py: Knowledge management system

The TaskDatabase class provides backward-compatible interface by
delegating to specialized repository classes.
"""

from .connection import DatabaseConnection
from .locks import LockRepository
from .sessions import SessionRepository
from .projects import ProjectRepository
from .tasks import TaskRepository
from .knowledge import KnowledgeRepository

__all__ = [
    'TaskDatabase',
    'DatabaseConnection',
    'LockRepository',
    'SessionRepository',
    'ProjectRepository',
    'TaskRepository',
    'KnowledgeRepository',
]


class TaskDatabase:
    """
    SQLite database with atomic locking for AI agent task coordination.

    This class provides a unified interface to all database operations,
    delegating to specialized repository classes for organization.

    Features:
    - WAL mode for concurrent read/write access
    - Atomic lock acquisition/release with expiration
    - Thread-safe operations across multiple agents
    - Response Awareness (RA) methodology support
    - Knowledge management system
    - Dashboard session tracking
    """

    def __init__(self, db_path: str, lock_timeout_seconds: int = 300):
        """
        Initialize TaskDatabase with SQLite WAL mode configuration.

        Args:
            db_path: Path to SQLite database file
            lock_timeout_seconds: Default lock expiration timeout
        """
        # Initialize connection (this also initializes the database and schema)
        self._conn = DatabaseConnection(db_path, lock_timeout_seconds)

        # Initialize repository instances
        self._locks = LockRepository(self._conn)
        self._sessions = SessionRepository(self._conn)
        self._projects = ProjectRepository(self._conn)
        self._tasks = TaskRepository(self._conn)
        self._knowledge = KnowledgeRepository(self._conn)

        # Expose connection properties for backward compatibility
        self.db_path = self._conn.db_path
        self.lock_timeout_seconds = self._conn.lock_timeout_seconds
        self._connection = self._conn.connection
        self._connection_lock = self._conn.connection_lock

    # ========================================================================
    # Connection Management Methods
    # ========================================================================

    def close(self):
        """Close database connection."""
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _get_current_time_str(self) -> str:
        """Get current UTC time as ISO string for database operations."""
        return self._conn._get_current_time_str()

    def initialize_fresh(self) -> None:
        """Initialize database with clean slate - drops all existing tables first."""
        self._conn.initialize_fresh()

    def _transaction(self):
        """Context manager for explicit transaction control."""
        return self._conn._transaction()

    # ========================================================================
    # Lock Management Methods - Delegate to LockRepository
    # ========================================================================

    def acquire_task_lock_atomic(self, task_id: int, agent_id: str,
                                lock_duration_seconds: int = None) -> bool:
        """Atomically acquire lock on a task."""
        return self._locks.acquire_task_lock_atomic(task_id, agent_id, lock_duration_seconds)

    def release_lock(self, task_id: int, agent_id: str) -> bool:
        """Release task lock with agent ownership validation."""
        return self._locks.release_lock(task_id, agent_id)

    def get_task_lock_status(self, task_id: int):
        """Get current lock status for a task."""
        return self._locks.get_task_lock_status(task_id)

    def cleanup_expired_locks(self) -> int:
        """Manually clean up expired locks."""
        return self._locks.cleanup_expired_locks()

    def cleanup_expired_locks_with_ids(self):
        """Clean up expired locks and return list of affected task IDs."""
        return self._locks.cleanup_expired_locks_with_ids()

    # ========================================================================
    # Session Management Methods - Delegate to SessionRepository
    # ========================================================================

    def register_session(self, session_id: str, user_agent: str, capabilities: dict) -> None:
        """Register dashboard session."""
        return self._sessions.register_session(session_id, user_agent, capabilities)

    def update_session_heartbeat(self, session_id: str, current_project_id: int = None,
                                 current_epic_id: int = None) -> None:
        """Update session heartbeat and context."""
        return self._sessions.update_session_heartbeat(session_id, current_project_id, current_epic_id)

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count removed."""
        return self._sessions.cleanup_expired_sessions()

    def log_event(self, event_type: str, event_data: dict, session_id: str = None,
                 entity_type: str = None, entity_id: int = None) -> None:
        """Log event for missed event recovery."""
        return self._sessions.log_event(event_type, event_data, session_id, entity_type, entity_id)

    def get_missed_events(self, session_id: str, since, event_types: list = None):
        """Retrieve missed events for session."""
        return self._sessions.get_missed_events(session_id, since, event_types)

    # ========================================================================
    # Project and Epic Management Methods - Delegate to ProjectRepository
    # ========================================================================

    def create_project(self, name: str, description: str = None) -> int:
        """Create a new project."""
        return self._projects.create_project(name, description)

    def create_epic(self, project_id: int, name: str, description: str = None) -> int:
        """Create a new epic within a project."""
        return self._projects.create_epic(project_id, name, description)

    def get_all_projects(self):
        """Get all projects for board state display."""
        return self._projects.get_all_projects()

    def get_all_epics(self):
        """Get all epics for board state display."""
        return self._projects.get_all_epics()

    def list_projects_filtered(self, status: str = None, limit: int = None):
        """List projects with optional filtering."""
        return self._projects.list_projects_filtered(status, limit)

    def list_epics_filtered(self, project_id: int = None, limit: int = None):
        """List epics with optional filtering."""
        return self._projects.list_epics_filtered(project_id, limit)

    def upsert_project(self, name: str, description: str = None) -> int:
        """Create project by name if not found, return existing ID if found."""
        return self._projects.upsert_project(name, description)

    def upsert_project_with_status(self, name: str, description: str = None):
        """Create project with creation status return."""
        return self._projects.upsert_project_with_status(name, description)

    def upsert_epic(self, project_id: int, name: str, description: str = None) -> int:
        """Create epic by name within project if not found."""
        return self._projects.upsert_epic(project_id, name, description)

    def upsert_epic_with_status(self, project_id: int, name: str, description: str = None):
        """Create epic with creation status return."""
        return self._projects.upsert_epic_with_status(project_id, name, description)

    def get_epic_with_project_info(self, epic_id: int):
        """Get epic details with project context information."""
        return self._projects.get_epic_with_project_info(epic_id)

    def list_projects_for_dashboard(self, status_filter: str = None, include_archived: bool = False):
        """List projects with statistics for dashboard selector."""
        return self._projects.list_projects_for_dashboard(status_filter, include_archived)

    def list_epics_for_project_dashboard(self, project_id: int, status_filter: str = None,
                                        include_archived: bool = False):
        """List epics for specific project with task counts."""
        return self._projects.list_epics_for_project_dashboard(project_id, status_filter, include_archived)

    def delete_project(self, project_id: int):
        """Delete a project and all associated epics and tasks."""
        return self._projects.delete_project(project_id)

    def delete_epic(self, epic_id: int):
        """Delete an epic and all associated tasks."""
        return self._projects.delete_epic(epic_id)

    def get_board_state_optimized(self):
        """Get complete board state with single optimized JOIN query."""
        return self._projects.get_board_state_optimized()

    # ========================================================================
    # Task Management Methods - Delegate to TaskRepository
    # ========================================================================

    def create_task(self, *args, **kwargs):
        """Create a new task."""
        return self._tasks.create_task(*args, **kwargs)

    def get_task_details(self, task_id: int):
        """Return comprehensive task details including RA metadata fields."""
        return self._tasks.get_task_details(task_id)

    def get_task_by_id(self, task_id: int):
        """Get task by ID with all fields."""
        return self._tasks.get_task_by_id(task_id)

    def get_available_tasks(self, limit: int = None):
        """Get available tasks (unlocked or expired locks)."""
        return self._tasks.get_available_tasks(limit)

    def get_all_tasks(self):
        """Get all tasks for board state display with lock information."""
        return self._tasks.get_all_tasks()

    def list_tasks_filtered(self, project_id: int = None, epic_id: int = None,
                          status: str = None, limit: int = None):
        """List tasks with hierarchical filtering."""
        return self._tasks.list_tasks_filtered(project_id, epic_id, status, limit)

    def update_task_status(self, task_id: int, status: str, agent_id: str):
        """Update task status with auto-locking semantics."""
        return self._tasks.update_task_status(task_id, status, agent_id)

    def update_task_ra_fields(self, *args, **kwargs):
        """Update task RA metadata fields."""
        return self._tasks.update_task_ra_fields(*args, **kwargs)

    def add_task_log(self, task_id: int, kind: str, payload: dict = None) -> int:
        """Add a log entry to a task."""
        return self._tasks.add_task_log(task_id, kind, payload)

    def get_task_logs(self, task_id: int, limit: int = None):
        """Get task logs with optional limit."""
        return self._tasks.get_task_logs(task_id, limit)

    def get_latest_task_log(self, task_id: int, kind: str = None):
        """Get the latest log entry for a task."""
        return self._tasks.get_latest_task_log(task_id, kind)

    def _process_ra_tags_with_ids(self, *args, **kwargs):
        """Process RA tags to ensure they have unique IDs."""
        return self._tasks._process_ra_tags_with_ids(*args, **kwargs)

    def _extract_tag_type(self, tag_text: str) -> str:
        """Extract tag type from string format tag."""
        return self._tasks._extract_tag_type(tag_text)

    def create_task_with_ra_metadata(self, *args, **kwargs):
        """Create task with full RA metadata support."""
        return self._tasks.create_task_with_ra_metadata(*args, **kwargs)

    def add_task_log_entry(self, *args, **kwargs):
        """Add task log entry with sequencing."""
        return self._tasks.add_task_log_entry(*args, **kwargs)

    def get_task_details_with_relations(self, task_id: int):
        """Get comprehensive task details with project/epic context."""
        return self._tasks.get_task_details_with_relations(task_id)

    def get_task_logs_paginated(self, *args, **kwargs):
        """Get task logs with pagination support."""
        return self._tasks.get_task_logs_paginated(*args, **kwargs)

    def resolve_task_dependencies(self, dependency_ids: list):
        """Resolve task dependencies to summaries."""
        return self._tasks.resolve_task_dependencies(dependency_ids)

    def update_task_atomic(self, *args, **kwargs):
        """Update task fields atomically with RA metadata support."""
        return self._tasks.update_task_atomic(*args, **kwargs)

    def list_tasks_with_context_dashboard(self, *args, **kwargs):
        """List tasks with project/epic context for dashboard."""
        return self._tasks.list_tasks_with_context_dashboard(*args, **kwargs)

    def create_task_with_project_context(self, *args, **kwargs):
        """Create task with automatic project_id assignment."""
        return self._tasks.create_task_with_project_context(*args, **kwargs)

    def delete_task(self, task_id: int):
        """Delete a task."""
        return self._tasks.delete_task(task_id)

    def cleanup_orphaned_tasks(self):
        """Clean up orphaned tasks."""
        return self._tasks.cleanup_orphaned_tasks()

    def create_large_dataset_for_performance_testing(self, scale_factor: int = 2):
        """Create large dataset for performance testing."""
        return self._tasks.create_large_dataset_for_performance_testing(scale_factor)

    # ========================================================================
    # Knowledge Management Methods - Delegate to KnowledgeRepository
    # ========================================================================

    def get_knowledge(self, *args, **kwargs):
        """Retrieve knowledge items with flexible filtering."""
        return self._knowledge.get_knowledge(*args, **kwargs)

    def upsert_knowledge(self, *args, **kwargs):
        """Create or update knowledge item."""
        return self._knowledge.upsert_knowledge(*args, **kwargs)

    def append_knowledge_log(self, *args, **kwargs):
        """Append log entry to knowledge item history."""
        return self._knowledge.append_knowledge_log(*args, **kwargs)

    def get_knowledge_logs(self, *args, **kwargs):
        """Get knowledge logs with pagination."""
        return self._knowledge.get_knowledge_logs(*args, **kwargs)

    def delete_knowledge_item(self, knowledge_id: int) -> bool:
        """Delete a knowledge item."""
        return self._knowledge.delete_knowledge_item(knowledge_id)


# Maintain backward compatibility - export TaskDatabase as the main interface
__all__ = ['TaskDatabase']
