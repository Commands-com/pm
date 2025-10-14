"""
Session and Event Management Operations

Provides dashboard session management, heartbeat tracking, and event logging
for WebSocket disconnection recovery and cross-tab coordination.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .connection import DatabaseConnection

# Configure logger
logger = logging.getLogger(__name__)


class SessionRepository:
    """
    Repository for dashboard session and event management operations.

    Provides session registration, heartbeat tracking, expiration cleanup,
    and event logging for missed event recovery after WebSocket disconnections.
    """

    def __init__(self, conn: 'DatabaseConnection'):
        """
        Initialize SessionRepository with database connection.

        Args:
            conn: DatabaseConnection instance
        """
        self.conn = conn

    def register_session(
        self,
        session_id: str,
        user_agent: str,
        capabilities: Dict[str, Any]
    ) -> None:
        """
        Register dashboard session.

        Args:
            session_id: Unique session identifier
            user_agent: Browser user agent string
            capabilities: Session capabilities dictionary
        """
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()
            now = datetime.now(timezone.utc).isoformat() + 'Z'
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat() + 'Z'

            cursor.execute("""
                INSERT OR REPLACE INTO dashboard_sessions
                (id, user_agent, capabilities, created_at, last_heartbeat, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, user_agent, json.dumps(capabilities), now, now, expires_at))

    def update_session_heartbeat(
        self,
        session_id: str,
        current_project_id: Optional[int] = None,
        current_epic_id: Optional[int] = None
    ) -> None:
        """
        Update session heartbeat and context.

        Args:
            session_id: Session to update
            current_project_id: Current project context (optional)
            current_epic_id: Current epic context (optional)
        """
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()
            now = datetime.now(timezone.utc).isoformat() + 'Z'

            cursor.execute("""
                UPDATE dashboard_sessions
                SET last_heartbeat = ?,
                    current_project_id = ?,
                    current_epic_id = ?
                WHERE id = ?
            """, (now, current_project_id, current_epic_id, session_id))

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions and return count removed.

        Returns:
            Number of sessions removed
        """
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()
            now = datetime.now(timezone.utc).isoformat() + 'Z'

            cursor.execute("""
                DELETE FROM dashboard_sessions
                WHERE expires_at < ? OR
                      (is_active = FALSE AND last_heartbeat < datetime(?, '-1 hour'))
            """, (now, now))

            removed_count = cursor.rowcount
            return removed_count

    def log_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        session_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None
    ) -> None:
        """
        Log event for missed event recovery.

        Args:
            event_type: Type of event (e.g., 'task_created', 'task_updated')
            event_data: Event data dictionary
            session_id: Associated session ID (optional)
            entity_type: Entity type (e.g., 'task', 'project') (optional)
            entity_id: Entity ID (optional)
        """
        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()
            now = datetime.now(timezone.utc).isoformat() + 'Z'
            expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat() + 'Z'

            cursor.execute("""
                INSERT INTO event_log (
                    event_type, event_data, session_id,
                    entity_type, entity_id, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (event_type, json.dumps(event_data), session_id,
                  entity_type, entity_id, now, expires_at))

    def get_missed_events(
        self,
        session_id: str,
        since: datetime,
        event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve missed events for session.

        Args:
            session_id: Session requesting missed events
            since: Retrieve events since this datetime
            event_types: Optional list of event types to filter (default: all types)

        Returns:
            List of event dictionaries with type, data, and timestamp
        """
        query = """
        SELECT event_type, event_data, created_at
        FROM event_log
        WHERE created_at > ? AND session_id != ?
        """

        params = [since.isoformat() + 'Z', session_id]

        if event_types:
            placeholders = ','.join('?' * len(event_types))
            query += f" AND event_type IN ({placeholders})"
            params.extend(event_types)

        query += " ORDER BY created_at ASC LIMIT 100"

        with self.conn.connection_lock:
            cursor = self.conn.connection.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            events = []
            for row in rows:
                row_dict = dict(zip([col[0] for col in cursor.description], row))
                event_data = json.loads(row_dict['event_data'])
                event_data['type'] = row_dict['event_type']
                event_data['timestamp'] = row_dict['created_at']
                events.append(event_data)

            return events
