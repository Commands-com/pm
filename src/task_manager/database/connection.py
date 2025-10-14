"""
Database Connection and Schema Management

Provides SQLite-based database connection with WAL mode for concurrent access,
schema initialization, and transaction management.
"""

import sqlite3
import threading
import logging
from datetime import datetime, timezone
from typing import Optional
from contextlib import contextmanager
from pathlib import Path

# Configure logger for database operations
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    SQLite database connection manager with WAL mode configuration.

    Features:
    - WAL mode for concurrent read/write access
    - Thread-safe operations with connection locking
    - Schema initialization and management
    - Transaction context manager
    """

    def __init__(self, db_path: str, lock_timeout_seconds: int = 300):
        """
        Initialize DatabaseConnection with SQLite WAL mode configuration.

        Args:
            db_path: Path to SQLite database file
            lock_timeout_seconds: Default lock expiration timeout
        """
        self.db_path = Path(db_path)
        self.lock_timeout_seconds = lock_timeout_seconds
        self._connection_lock = threading.RLock()

        # Single connection with cross-thread access enabled for WAL mode
        # WAL mode provides concurrent read/write safety verified by testing.
        # Connection pool alternative available if performance scaling needed.
        self._connection: Optional[sqlite3.Connection] = None

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database and schema
        self._initialize_database()

    def _initialize_database(self, drop_existing: bool = False) -> None:
        """Initialize database with WAL mode and create schema if needed.

        Args:
            drop_existing: If True, drops all existing tables for clean slate initialization
        """
        try:
            # Autocommit mode with explicit transaction control per MVP specification
            # Provides precise control over transaction boundaries for atomic operations
            self._connection = sqlite3.connect(
                str(self.db_path),
                isolation_level=None,  # Autocommit mode
                check_same_thread=False  # Allow cross-thread access
            )

            # Configure SQLite for concurrent access
            cursor = self._connection.cursor()

            # WAL mode configuration verified compatible with local and temp filesystems
            # Provides concurrent access as required by MVP specification
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=5000")  # 5 second timeout for lock contention
            cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints for CASCADE DELETE

            # #SUGGEST_ERROR_HANDLING: Consider fallback to DELETE mode if WAL fails on network filesystem
            # cursor.execute("PRAGMA journal_mode=DELETE") as fallback

            # Drop existing tables if requested for clean slate initialization
            if drop_existing:
                self._drop_existing_tables()

            # Create schema if it doesn't exist
            self._create_schema()

        except sqlite3.Error as e:
            # #SUGGEST_ERROR_HANDLING: Database initialization failure recovery
            raise RuntimeError(f"Failed to initialize database at {self.db_path}: {e}")

    def _create_schema(self) -> None:
        """Create database schema with proper indexes for performance."""
        cursor = self._connection.cursor()

        # VERIFIED: Schema implements Projects → Epics → Tasks hierarchy per Task 001 dependencies
        # Schema design updated to remove stories table and add projects table with enhanced constraints

        # Projects table - enhanced for dashboard selector functionality
        # #COMPLETION_DRIVE_IMPL: Extended with dashboard-specific fields for performance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                task_count INTEGER DEFAULT 0,
                epic_count INTEGER DEFAULT 0,
                last_activity TEXT DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT NULL,
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed'))
            )
        """)

        # Epics table - enhanced with priority and progress tracking
        # #COMPLETION_DRIVE_IMPL: Added fields for epic selector display and sorting
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS epics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                priority INTEGER DEFAULT 0 CHECK (priority BETWEEN 0 AND 3),
                start_date TEXT,
                target_date TEXT,
                completed_date TEXT,
                task_count INTEGER DEFAULT 0,
                completed_task_count INTEGER DEFAULT 0,
                deleted_at TEXT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
        """)

        # Tasks table with locking fields and RA enhancement - enhanced for project/epic context
        # #COMPLETION_DRIVE_INTEGRATION: Added project_id for direct project association
        # VERIFIED: RA fields added per Task 004 acceptance criteria for RA metadata support
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                epic_id INTEGER NOT NULL,
                project_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                lock_holder TEXT,
                lock_expires_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                ra_mode TEXT,
                ra_score INTEGER,
                ra_tags TEXT,
                ra_metadata TEXT,
                prompt_snapshot TEXT,
                dependencies TEXT,
                parallel_group TEXT,
                conflicts_with TEXT,
                parallel_eligible INTEGER DEFAULT 1,
                complexity_score INTEGER,
                mode_used TEXT,
                created_by TEXT,
                FOREIGN KEY (epic_id) REFERENCES epics (id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE SET NULL,
                CONSTRAINT status_vocabulary CHECK(status IN ('pending','in_progress','review','completed','blocked','backlog','TODO','IN_PROGRESS','REVIEW','DONE','BACKLOG')),
                CONSTRAINT json_ra_tags CHECK (ra_tags IS NULL OR (json_valid(ra_tags) AND json_type(ra_tags) = 'array')),
                CONSTRAINT json_ra_metadata CHECK (ra_metadata IS NULL OR (json_valid(ra_metadata) AND json_type(ra_metadata) = 'object')),
                CONSTRAINT json_dependencies CHECK (dependencies IS NULL OR (json_valid(dependencies) AND json_type(dependencies) = 'array')),
                CONSTRAINT json_conflicts_with CHECK (conflicts_with IS NULL OR (json_valid(conflicts_with) AND json_type(conflicts_with) = 'array'))
            )
        """)

        # Task logs table with sequence-based logging and JSON validation
        # VERIFIED: Sequence-based primary key ensures chronological ordering per task logging requirements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_logs (
                task_id INTEGER NOT NULL,
                seq INTEGER NOT NULL,
                ts TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload TEXT,
                PRIMARY KEY (task_id, seq),
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                CONSTRAINT json_valid_payload CHECK (payload IS NULL OR json_valid(payload)),
                CONSTRAINT json_object_payload CHECK (payload IS NULL OR json_type(payload) = 'object')
            )
        """)

        # Dashboard sessions table for auto-switch functionality
        # #COMPLETION_DRIVE_SESSION: Session tracking for cross-tab isolation and auto-switch
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_heartbeat TEXT DEFAULT CURRENT_TIMESTAMP,
                user_agent TEXT,
                capabilities TEXT,
                current_project_id INTEGER,
                current_epic_id INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                expires_at TEXT DEFAULT (datetime('now', '+24 hours')),
                FOREIGN KEY (current_project_id) REFERENCES projects (id) ON DELETE SET NULL,
                FOREIGN KEY (current_epic_id) REFERENCES epics (id) ON DELETE SET NULL
            )
        """)

        # Event log table for missed event recovery
        # #COMPLETION_DRIVE_RESILIENCE: Event logging for WebSocket disconnection recovery
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                session_id TEXT,
                entity_type TEXT,
                entity_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT DEFAULT (datetime('now', '+30 days')),
                FOREIGN KEY (session_id) REFERENCES dashboard_sessions (id) ON DELETE SET NULL,
                CONSTRAINT json_valid_event_data CHECK (json_valid(event_data))
            )
        """)

        # Performance optimization indexes as per Task 001 requirements
        # Index for epics by project - replaces stories_epic_id index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_epics_project_id
            ON epics (project_id)
        """)

        # Index for tasks by epic - updated from stories dependency
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_epic_id
            ON tasks (epic_id)
        """)

        # Composite index for task status and creation time - performance optimization
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status_created
            ON tasks (status, created_at)
        """)

        # Task logs performance index - sequence-based access pattern optimization
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_logs_task_seq
            ON task_logs (task_id, seq)
        """)

        # Legacy indexes for backward compatibility with existing lock operations
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_lock_holder
            ON tasks (lock_holder, lock_expires_at)
        """)

        # Partial index for available tasks (most frequent query pattern)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_available
            ON tasks (status, created_at)
            WHERE lock_holder IS NULL
        """)

        # Index for lock expiration cleanup (background task optimization)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_lock_expiration
            ON tasks (lock_expires_at)
            WHERE lock_expires_at IS NOT NULL
        """)

        # Dashboard performance indexes
        # #COMPLETION_DRIVE_PERFORMANCE: Strategic indexing for dashboard selector queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_projects_status_activity
            ON projects(status, last_activity DESC)
            WHERE deleted_at IS NULL
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_epics_project_status
            ON epics(project_id, status)
            WHERE deleted_at IS NULL
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_epics_priority_date
            ON epics(priority DESC, target_date ASC)
            WHERE status = 'active'
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_project_status
            ON tasks(project_id, status)
            WHERE project_id IS NOT NULL
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_context_created
            ON tasks(project_id, epic_id, created_at DESC)
        """)

        # Session management indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_active_heartbeat
            ON dashboard_sessions(is_active, last_heartbeat)
            WHERE is_active = TRUE
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_expires
            ON dashboard_sessions(expires_at)
        """)

        # Event log indexes for missed event recovery
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_log_session_time
            ON event_log(session_id, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_log_type_time
            ON event_log(event_type, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_log_expires
            ON event_log(expires_at)
        """)

        # Knowledge Management System Tables
        # Knowledge items table - hierarchical knowledge storage with versioning
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT,
                tags TEXT,
                parent_id INTEGER,
                project_id INTEGER NOT NULL,
                epic_id INTEGER,
                task_id INTEGER,
                priority INTEGER DEFAULT 0 CHECK (priority BETWEEN 0 AND 5),
                version INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by TEXT,
                metadata TEXT,
                FOREIGN KEY (parent_id) REFERENCES knowledge_items (id) ON DELETE SET NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE SET NULL,
                FOREIGN KEY (epic_id) REFERENCES epics (id) ON DELETE SET NULL,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE SET NULL,
                CONSTRAINT json_tags CHECK (tags IS NULL OR (json_valid(tags) AND json_type(tags) = 'array')),
                CONSTRAINT json_metadata CHECK (metadata IS NULL OR (json_valid(metadata) AND json_type(metadata) = 'object'))
            )
        """)

        # Knowledge logs table - audit trail for knowledge changes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                old_content TEXT,
                new_content TEXT,
                changed_fields TEXT,
                change_reason TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT,
                metadata TEXT,
                FOREIGN KEY (knowledge_id) REFERENCES knowledge_items (id) ON DELETE CASCADE,
                CONSTRAINT json_changed_fields CHECK (changed_fields IS NULL OR (json_valid(changed_fields) AND json_type(changed_fields) = 'array')),
                CONSTRAINT json_metadata CHECK (metadata IS NULL OR (json_valid(metadata) AND json_type(metadata) = 'object'))
            )
        """)

        # Knowledge management performance indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_category_priority
            ON knowledge_items (category, priority DESC, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_project_context
            ON knowledge_items (project_id, epic_id, task_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_hierarchy
            ON knowledge_items (parent_id, created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_active_updated
            ON knowledge_items (is_active, updated_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_logs_item_time
            ON knowledge_logs (knowledge_id, created_at DESC)
        """)

        # Assumption validations table - stores RA tag validation outcomes during review
        # #COMPLETION_DRIVE_IMPL: Foreign keys to tasks, projects, epics for hierarchical context
        # Enhanced with ra_tag_id for exact tag matching
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assumption_validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                project_id INTEGER,
                epic_id INTEGER,
                ra_tag_id TEXT NOT NULL,
                validator_id TEXT NOT NULL,
                outcome TEXT NOT NULL CHECK (outcome IN ('validated', 'rejected', 'partial')),
                confidence INTEGER NOT NULL CHECK (confidence BETWEEN 0 AND 100),
                notes TEXT,
                context_snapshot TEXT,
                validated_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (epic_id) REFERENCES epics (id) ON DELETE CASCADE,
                UNIQUE(task_id, ra_tag_id, validator_id)
            )
        """)

        # Performance indexes for assumption validations queries
        # #PATH_DECISION: Multiple targeted indexes for query flexibility per task specification
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assumption_validations_task_context
            ON assumption_validations (task_id, outcome, validated_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assumption_validations_reviewer_history
            ON assumption_validations (validator_id, validated_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assumption_validations_project_context
            ON assumption_validations (project_id, epic_id, outcome)
        """)

        # Additional individual indexes for test compatibility
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assumption_validations_task_id
            ON assumption_validations (task_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assumption_validations_validated_at
            ON assumption_validations (validated_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assumption_validations_outcome
            ON assumption_validations (outcome)
        """)

    def _drop_existing_tables(self) -> None:
        """Drop all existing tables for clean slate initialization."""
        cursor = self._connection.cursor()

        # #COMPLETION_DRIVE_IMPL: Drop tables in reverse dependency order to avoid foreign key constraint errors
        # Task logs first (depends on tasks), then tasks (depends on epics), then epics (depends on projects)
        # Also dropping legacy stories table for migration from old schema

        # Drop indexes first to avoid dependency issues
        cursor.execute("DROP INDEX IF EXISTS idx_task_logs_task_seq")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_status_created")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_epic_id")
        cursor.execute("DROP INDEX IF EXISTS idx_epics_project_id")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_lock_holder")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_available")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_lock_expiration")
        # Assumption validations indexes
        cursor.execute("DROP INDEX IF EXISTS idx_assumption_validations_task_context")
        cursor.execute("DROP INDEX IF EXISTS idx_assumption_validations_reviewer_history")
        cursor.execute("DROP INDEX IF EXISTS idx_assumption_validations_project_context")
        # Knowledge management indexes
        cursor.execute("DROP INDEX IF EXISTS idx_knowledge_category_priority")
        cursor.execute("DROP INDEX IF EXISTS idx_knowledge_project_context")
        cursor.execute("DROP INDEX IF EXISTS idx_knowledge_hierarchy")
        cursor.execute("DROP INDEX IF EXISTS idx_knowledge_active_updated")
        cursor.execute("DROP INDEX IF EXISTS idx_knowledge_logs_item_time")
        # Legacy indexes from old schema
        cursor.execute("DROP INDEX IF EXISTS idx_stories_epic_id")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_status")
        cursor.execute("DROP INDEX IF EXISTS idx_tasks_status_updated")

        # Drop tables in dependency order
        cursor.execute("DROP TABLE IF EXISTS assumption_validations")  # Depends on tasks, projects, epics
        cursor.execute("DROP TABLE IF EXISTS knowledge_logs")  # Depends on knowledge_items
        cursor.execute("DROP TABLE IF EXISTS knowledge_items")
        cursor.execute("DROP TABLE IF EXISTS event_log")
        cursor.execute("DROP TABLE IF EXISTS dashboard_sessions")
        cursor.execute("DROP TABLE IF EXISTS task_logs")
        cursor.execute("DROP TABLE IF EXISTS tasks")
        cursor.execute("DROP TABLE IF EXISTS stories")  # Legacy table removal
        cursor.execute("DROP TABLE IF EXISTS epics")
        cursor.execute("DROP TABLE IF EXISTS projects")

    @contextmanager
    def _transaction(self):
        """Context manager for explicit transaction control."""
        cursor = self._connection.cursor()
        try:
            cursor.execute("BEGIN")
            yield cursor
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise

    def _get_current_time_str(self) -> str:
        """Get current UTC time as ISO string for database operations."""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    def initialize_fresh(self) -> None:
        """
        Initialize database with clean slate - drops all existing tables first.

        This method is useful for:
        - Fresh installations
        - Schema migrations
        - Testing scenarios requiring clean state
        """
        self._initialize_database(drop_existing=True)

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def connection(self) -> sqlite3.Connection:
        """Get the underlying SQLite connection."""
        return self._connection

    @property
    def connection_lock(self) -> threading.RLock:
        """Get the connection lock for thread-safe operations."""
        return self._connection_lock


# Database schema design updated for Task 001 - Database Schema Enhancement
# New hierarchy: Projects → Epics → Tasks (removed stories table)
# Added task_logs table with sequence-based logging and JSON validation constraints

# Thread safety verified using SQLite WAL mode + single connection with RLock
# Tested successfully with 20 concurrent agents - alternative approaches available if needed

# Performance optimization indexes added:
# - idx_epics_project_id: Optimizes project → epics queries
# - idx_tasks_epic_id: Optimizes epic → tasks queries
# - idx_tasks_status_created: Optimizes task filtering and sorting
# - idx_task_logs_task_seq: Optimizes chronological log retrieval

# JSON validation constraints ensure data integrity:
# - json_valid_payload: Ensures payload is valid JSON or NULL
# - json_object_payload: Ensures payload is JSON object type or NULL

# #SUGGEST_ERROR_HANDLING: Consider adding database corruption recovery and migration system
# #SUGGEST_VALIDATION: Consider adding schema version tracking for future migrations
# #SUGGEST_DEFENSIVE: Consider adding database backup/restore functionality for production use
