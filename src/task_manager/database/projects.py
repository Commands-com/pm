"""
Project and Epic Management Operations

Provides CRUD operations for projects and epics with hierarchical
relationships, cascade deletion, and dashboard statistics.
"""

import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .connection import DatabaseConnection

# Configure logger
logger = logging.getLogger(__name__)


class ProjectRepository:
    """
    Repository for project and epic operations with hierarchical management.

    Provides creation, retrieval, updates, deletion, and listing operations
    for projects and epics with CASCADE DELETE support and dashboard statistics.
    """

    def __init__(self, conn: 'DatabaseConnection'):
        """
        Initialize ProjectRepository with database connection.

        Args:
            conn: DatabaseConnection instance
        """
        self.conn = conn

    def create_project(self, name: str, description: Optional[str] = None) -> int:
        """
        Create a new project.

        Args:
            name: Project name (must be unique)
            description: Optional project description

        Returns:
            Project ID
        """
        current_time_str = datetime.now(timezone.utc).isoformat() + 'Z'

        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()
            cursor.execute("""
                INSERT INTO projects (name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (name, description, current_time_str, current_time_str))

            return cursor.lastrowid

    def create_epic(self, project_id: int, name: str, description: Optional[str] = None) -> int:
        """
        Create a new epic within a project.

        Args:
            project_id: Parent project ID
            name: Epic name
            description: Optional epic description

        Returns:
            Epic ID
        """
        current_time_str = datetime.now(timezone.utc).isoformat() + 'Z'

        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()
            cursor.execute("""
                INSERT INTO epics (project_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, name, description, current_time_str, current_time_str))

            return cursor.lastrowid

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        Get all projects for board state display.

        Returns:
            List of project dictionaries with all fields
        """
        # #COMPLETION_DRIVE_IMPL: New method for top-level projects hierarchy
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()
            cursor.execute("""
                SELECT id, name, description, created_at, updated_at
                FROM projects
                ORDER BY created_at ASC
            """)

            rows = cursor.fetchall()
            return [{
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            } for row in rows]

    def get_all_epics(self) -> List[Dict[str, Any]]:
        """
        Get all epics for board state display.

        Returns:
            List of epic dictionaries with all fields including project_id
        """
        # #COMPLETION_DRIVE_IMPL: Including project_id for hierarchical organization in frontend
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()
            cursor.execute("""
                SELECT id, project_id, name, description, status, created_at, updated_at
                FROM epics
                ORDER BY project_id ASC, created_at ASC
            """)

            rows = cursor.fetchall()
            return [{
                "id": row[0],
                "project_id": row[1],
                "name": row[2],
                "description": row[3],
                "status": row[4],
                "created_at": row[5],
                "updated_at": row[6]
            } for row in rows]

    def list_projects_filtered(self, status: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List projects with optional status filtering and result limiting.

        Standard Mode Assumptions:
        - Projects don't currently have status field, so status filter is ignored for now
        - Limit parameter prevents overwhelming responses for large project counts
        - Results ordered by creation date for consistent pagination

        Args:
            status: Optional status filter (currently ignored - projects have no status field)
            limit: Optional limit on number of results returned

        Returns:
            List of project dictionaries with id, name, description, created_at, updated_at
        """
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()

            # Base query for all projects - status filtering commented out until projects table updated
            query = """
                SELECT id, name, description, created_at, updated_at
                FROM projects
                ORDER BY created_at ASC
            """
            params = []

            # Add limit clause if specified
            if limit and limit > 0:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [{
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            } for row in rows]

    def list_epics_filtered(self, project_id: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List epics with optional project filtering and result limiting.

        Standard Mode Assumptions:
        - Epic status filtering not requested in requirements, so only project_id filtering implemented
        - Including project_name in response requires JOIN for better UX
        - Results ordered by project_id and creation date for hierarchical display

        Args:
            project_id: Optional project ID to filter epics within specific project
            limit: Optional limit on number of results returned

        Returns:
            List of epic dictionaries with id, name, description, project_id, project_name, created_at
        """
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()

            # Query with JOIN to include project_name for context
            query = """
                SELECT e.id, e.name, e.description, e.project_id, p.name as project_name, e.created_at
                FROM epics e
                JOIN projects p ON e.project_id = p.id
            """
            params = []

            # Add project_id filtering if specified
            if project_id is not None:
                query += " WHERE e.project_id = ?"
                params.append(project_id)

            # Order by project_id for grouping, then creation date
            query += " ORDER BY e.project_id ASC, e.created_at ASC"

            # Add limit clause if specified
            if limit and limit > 0:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [{
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "project_id": row[3],
                "project_name": row[4],
                "created_at": row[5]
            } for row in rows]

    def upsert_project(self, name: str, description: Optional[str] = None) -> int:
        """
        Create project by name if not found, return existing project ID if found.

        # VERIFIED: Database schema has UNIQUE constraint on projects.name (line 102)
        # Race condition handling using INSERT OR IGNORE + SELECT pattern for atomic upsert
        # Concurrent creation attempts result in one success, others get existing ID

        Args:
            name: Project name (must be unique across all projects)
            description: Optional project description (only used on creation)

        Returns:
            Project ID (either newly created or existing)

        # #SUGGEST_EDGE_CASE: Concurrent upserts with different descriptions may use first description
        # Consider description update logic if required by business rules
        """
        current_time_str = datetime.now(timezone.utc).isoformat() + 'Z'

        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()

            # VERIFIED: INSERT OR IGNORE with UNIQUE constraint is atomic upsert pattern
            # SQLite UNIQUE constraint prevents duplicates, OR IGNORE handles race conditions
            cursor.execute(
                """
                INSERT OR IGNORE INTO projects (name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, description, current_time_str, current_time_str),
            )

            # If INSERT was ignored due to existing name, get the existing project ID
            if cursor.rowcount == 0:
                # VERIFIED: Project deletion not part of current system requirements
                cursor.execute("SELECT id FROM projects WHERE name = ?", (name,))
                row = cursor.fetchone()
                if row:
                    return row[0]
                else:
                    # #SUGGEST_ERROR_HANDLING: Extremely rare case where project was deleted between operations
                    raise sqlite3.IntegrityError(f"Project '{name}' disappeared during upsert operation")

            return cursor.lastrowid

    def upsert_project_with_status(self, name: str, description: Optional[str] = None) -> Tuple[int, bool]:
        """
        Create project by name if not found, return existing project ID if found.

        Returns:
            Tuple of (project_id, was_created) where was_created is True if newly created
        """
        current_time_str = datetime.now(timezone.utc).isoformat() + 'Z'

        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()

            cursor.execute(
                """
                INSERT OR IGNORE INTO projects (name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, description, current_time_str, current_time_str),
            )

            # If INSERT was successful, it was newly created
            if cursor.rowcount > 0:
                return cursor.lastrowid, True

            # If INSERT was ignored, project already existed
            cursor.execute("SELECT id FROM projects WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                return row[0], False
            else:
                raise sqlite3.IntegrityError(f"Project '{name}' disappeared during upsert operation")

    def upsert_epic(self, project_id: int, name: str, description: Optional[str] = None) -> int:
        """
        Create epic by name within project if not found, return existing epic ID if found.

        # #COMPLETION_DRIVE_IMPL: Upsert logic assumes (project_id, name) uniqueness for epic identification
        # No database constraint exists for epic name uniqueness within project - business logic enforcement
        # Race condition handling using INSERT OR IGNORE pattern after constraint creation

        Args:
            project_id: ID of the project containing this epic
            name: Epic name (must be unique within the project)
            description: Optional epic description (only used on creation)

        Returns:
            Epic ID (either newly created or existing)

        # #SUGGEST_VALIDATION: Consider adding UNIQUE constraint on (project_id, name) for epic table
        # Current implementation relies on application-level uniqueness checking
        """
        current_time_str = datetime.now(timezone.utc).isoformat() + 'Z'

        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()

            # First, check if an epic with this name already exists in the project
            cursor.execute(
                "SELECT id FROM epics WHERE project_id = ? AND name = ?",
                (project_id, name)
            )

            existing_row = cursor.fetchone()
            if existing_row:
                return existing_row[0]

            # If no existing epic, create a new one
            cursor.execute(
                """
                INSERT INTO epics (project_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, name, description, current_time_str, current_time_str)
            )

            return cursor.lastrowid

    def upsert_epic_with_status(self, project_id: int, name: str, description: Optional[str] = None) -> Tuple[int, bool]:
        """
        Create epic by name within project if not found, return existing epic ID if found.

        Returns:
            Tuple of (epic_id, was_created) where was_created is True if newly created
        """
        current_time_str = datetime.now(timezone.utc).isoformat() + 'Z'

        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()

            # Check if epic already exists
            cursor.execute(
                "SELECT id FROM epics WHERE project_id = ? AND name = ?",
                (project_id, name)
            )

            existing_row = cursor.fetchone()
            if existing_row:
                return existing_row[0], False

            # Create new epic
            cursor.execute(
                """
                INSERT INTO epics (project_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, name, description, current_time_str, current_time_str)
            )

            return cursor.lastrowid, True

    def get_epic_with_project_info(self, epic_id: int) -> Optional[Dict[str, Any]]:
        """
        Get epic details with project context information.

        Args:
            epic_id: Epic ID to retrieve

        Returns:
            Dict with epic and project information, or None if not found
        """
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()

            cursor.execute("""
                SELECT
                    e.id, e.name, e.description, e.status,
                    e.created_at, e.updated_at,
                    e.project_id, p.name as project_name
                FROM epics e
                JOIN projects p ON e.project_id = p.id
                WHERE e.id = ?
            """, (epic_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "status": row[3],
                "created_at": row[4],
                "updated_at": row[5],
                "project_id": row[6],
                "project_name": row[7]
            }

    def list_projects_for_dashboard(
        self,
        status_filter: Optional[str] = None,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """List projects with statistics for dashboard selector."""
        # #COMPLETION_DRIVE_PERFORMANCE: Single query with JOINs for efficiency
        # Assumption: Statistics are always needed for dashboard display
        query = """
        SELECT p.*,
               COALESCE(task_counts.direct_task_count, 0) as direct_task_count,
               COALESCE(epic_counts.epic_count, 0) as epic_count
        FROM projects p
        LEFT JOIN (
            SELECT project_id, COUNT(*) as direct_task_count
            FROM tasks
            WHERE project_id IS NOT NULL
            GROUP BY project_id
        ) task_counts ON p.id = task_counts.project_id
        LEFT JOIN (
            SELECT project_id, COUNT(*) as epic_count
            FROM epics
            WHERE deleted_at IS NULL
            GROUP BY project_id
        ) epic_counts ON p.id = epic_counts.project_id
        WHERE p.deleted_at IS NULL
        """

        params = []
        if status_filter:
            query += " AND p.status = ?"
            params.append(status_filter)

        if not include_archived:
            query += " AND p.status != 'archived'"

        query += " ORDER BY p.last_activity DESC"

        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to dictionaries for API consistency
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]

    def list_epics_for_project_dashboard(
        self,
        project_id: int,
        status_filter: Optional[str] = None,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """List epics for specific project with task counts."""
        # #COMPLETION_DRIVE_INTEGRATION: Join with projects for breadcrumb context
        query = """
        SELECT e.*, p.name as project_name,
               COALESCE(task_counts.task_count, 0) as actual_task_count
        FROM epics e
        JOIN projects p ON e.project_id = p.id
        LEFT JOIN (
            SELECT epic_id, COUNT(*) as task_count
            FROM tasks
            WHERE epic_id IS NOT NULL
            GROUP BY epic_id
        ) task_counts ON e.id = task_counts.epic_id
        WHERE e.project_id = ? AND e.deleted_at IS NULL
        """

        params = [project_id]

        if status_filter:
            query += " AND e.status = ?"
            params.append(status_filter)

        if not include_archived:
            query += " AND e.status != 'archived'"

        query += " ORDER BY e.priority DESC, e.target_date ASC NULLS LAST"

        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]

    def delete_project(self, project_id: int) -> Dict[str, Any]:
        """
        Delete a project and all associated epics and tasks via CASCADE DELETE.

        Args:
            project_id: ID of the project to delete

        Returns:
            Dict with success status and deletion statistics
        """
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()

            # First, get project info and cascade counts for the response
            cursor.execute("""
                SELECT name, description FROM projects WHERE id = ?
            """, (project_id,))

            project_row = cursor.fetchone()
            if not project_row:
                return {"success": False, "error": f"Project {project_id} not found"}

            project_name, project_description = project_row

            # Get cascade deletion counts before deletion
            cursor.execute("""
                SELECT
                    (SELECT COUNT(*) FROM epics WHERE project_id = ?) as epic_count,
                    (SELECT COUNT(*) FROM tasks WHERE project_id = ?) as task_count
            """, (project_id, project_id))

            counts = cursor.fetchone()
            epic_count, task_count = counts or (0, 0)

            try:
                # Delete the project - CASCADE DELETE will handle epics and tasks
                cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))

                if cursor.rowcount == 0:
                    return {"success": False, "error": f"Project {project_id} not found or already deleted"}

                return {
                    "success": True,
                    "project_id": project_id,
                    "project_name": project_name,
                    "cascaded_epics": epic_count,
                    "cascaded_tasks": task_count,
                    "message": f"Deleted project '{project_name}' and {epic_count} epics, {task_count} tasks"
                }

            except sqlite3.Error as e:
                logger.error(f"Database error deleting project {project_id}: {e}")
                return {"success": False, "error": f"Database error: {str(e)}"}

    def delete_epic(self, epic_id: int) -> Dict[str, Any]:
        """
        Delete an epic and all associated tasks via CASCADE DELETE.

        Args:
            epic_id: ID of the epic to delete

        Returns:
            Dict with success status and deletion statistics
        """
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()

            # First, get epic info and cascade counts for the response
            cursor.execute("""
                SELECT e.name, e.description, p.name as project_name
                FROM epics e
                JOIN projects p ON e.project_id = p.id
                WHERE e.id = ?
            """, (epic_id,))

            epic_row = cursor.fetchone()
            if not epic_row:
                return {"success": False, "error": f"Epic {epic_id} not found"}

            epic_name, epic_description, project_name = epic_row

            # Get cascade deletion counts before deletion
            cursor.execute("""
                SELECT COUNT(*) FROM tasks WHERE epic_id = ?
            """, (epic_id,))

            task_count = cursor.fetchone()[0] or 0

            try:
                # Delete the epic - CASCADE DELETE will handle tasks
                cursor.execute("DELETE FROM epics WHERE id = ?", (epic_id,))

                if cursor.rowcount == 0:
                    return {"success": False, "error": f"Epic {epic_id} not found or already deleted"}

                return {
                    "success": True,
                    "epic_id": epic_id,
                    "epic_name": epic_name,
                    "project_name": project_name,
                    "cascaded_tasks": task_count,
                    "message": f"Deleted epic '{epic_name}' in project '{project_name}' and {task_count} tasks"
                }

            except sqlite3.Error as e:
                logger.error(f"Database error deleting epic {epic_id}: {e}")
                return {"success": False, "error": f"Database error: {str(e)}"}

    def get_board_state_optimized(self) -> Dict[str, Any]:
        """
        Get complete board state with single optimized JOIN query.

        Returns all tasks with their epic and project information in one query,
        avoiding N+1 query pattern for better performance.

        This replaces the inefficient pattern of calling get_all_projects(),
        get_all_epics(), and get_all_tasks() separately which causes multiple
        round trips to the database.

        Returns:
            Dict with 'projects', 'epics', and 'tasks' keys containing
            complete hierarchical board state data
        """
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()

            # Single optimized query that JOINs all three tables
            query = """
                SELECT
                    t.id as task_id,
                    t.epic_id,
                    t.name as task_name,
                    t.description as task_description,
                    t.status as task_status,
                    t.priority as task_priority,
                    t.ra_mode,
                    t.ra_score,
                    t.ra_tags,
                    t.ra_metadata,
                    t.dependencies,
                    t.parallel_group,
                    t.conflicts_with,
                    t.parallel_eligible,
                    t.created_at as task_created_at,
                    t.updated_at as task_updated_at,
                    t.lock_holder,
                    t.lock_expiration,
                    e.id as epic_id,
                    e.name as epic_name,
                    e.description as epic_description,
                    e.status as epic_status,
                    e.project_id,
                    e.created_at as epic_created_at,
                    e.updated_at as epic_updated_at,
                    p.id as project_id,
                    p.name as project_name,
                    p.description as project_description,
                    p.created_at as project_created_at,
                    p.updated_at as project_updated_at
                FROM tasks t
                JOIN epics e ON t.epic_id = e.id
                JOIN projects p ON e.project_id = p.id
                ORDER BY p.name, e.name, t.created_at DESC
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            # Group results into projects -> epics -> tasks structure
            projects_dict = {}
            epics_dict = {}
            tasks_list = []

            for row in rows:
                # Extract task data
                task = {
                    "id": row[0],
                    "epic_id": row[1],
                    "name": row[2],
                    "description": row[3],
                    "status": row[4],
                    "priority": row[5],
                    "ra_mode": row[6],
                    "ra_score": row[7],
                    "ra_tags": row[8],
                    "ra_metadata": row[9],
                    "dependencies": row[10],
                    "parallel_group": row[11],
                    "conflicts_with": row[12],
                    "parallel_eligible": row[13],
                    "created_at": row[14],
                    "updated_at": row[15],
                    "lock_holder": row[16],
                    "lock_expiration": row[17],
                    "epic_name": row[19],
                    "project_name": row[26]
                }
                tasks_list.append(task)

                # Build epic if not exists
                epic_id = row[18]
                if epic_id not in epics_dict:
                    epics_dict[epic_id] = {
                        "id": epic_id,
                        "name": row[19],
                        "description": row[20],
                        "status": row[21],
                        "project_id": row[22],
                        "created_at": row[23],
                        "updated_at": row[24]
                    }

                # Build project if not exists
                project_id = row[25]
                if project_id not in projects_dict:
                    projects_dict[project_id] = {
                        "id": project_id,
                        "name": row[26],
                        "description": row[27],
                        "created_at": row[28],
                        "updated_at": row[29]
                    }

            return {
                "projects": list(projects_dict.values()),
                "epics": list(epics_dict.values()),
                "tasks": tasks_list
            }
