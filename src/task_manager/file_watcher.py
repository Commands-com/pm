"""
File watcher for planning mode live updates.

Monitors .pm directory for changes to markdown files and broadcasts
updates via WebSocket to connected planning mode clients.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Set

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

logger = logging.getLogger(__name__)


class PlanningFileHandler(FileSystemEventHandler):
    """
    File system event handler for planning documents.

    Monitors .pm/prds/ and .pm/epics/ directories for markdown file changes
    and queues WebSocket broadcast events for connected planning clients.
    """

    def __init__(self, connection_manager, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.connection_manager = connection_manager
        # Main asyncio loop to schedule coroutines from watchdog thread
        self.loop: Optional[asyncio.AbstractEventLoop] = loop
        self.processed_events: Set[str] = set()
        self.event_cooldown = 1.0  # Seconds to debounce rapid file changes

    def on_modified(self, event):
        """Handle file modification events."""
        if self._should_process_event(event):
            self._schedule(self._broadcast_event('file_updated', event))

    def on_created(self, event):
        """Handle file creation events."""
        if self._should_process_event(event):
            self._schedule(self._broadcast_event('file_created', event))

    def on_deleted(self, event):
        """Handle file deletion events."""
        if self._should_process_event(event):
            self._schedule(self._broadcast_event('file_deleted', event))

    def _schedule(self, coro):
        """Schedule coroutine on the main asyncio loop from watchdog thread."""
        try:
            if self.loop and not self.loop.is_closed():
                return asyncio.run_coroutine_threadsafe(coro, self.loop)
            else:
                # Best-effort: try to get a running loop in this context (rare)
                loop = asyncio.get_running_loop()
                return asyncio.run_coroutine_threadsafe(coro, loop)
        except RuntimeError as e:
            # No running loop available; log and drop the event gracefully
            logger.warning(f"Unable to schedule coroutine; no running loop: {e}")
            return None

    def _should_process_event(self, event) -> bool:
        """
        Determine if an event should be processed.

        Filters for markdown files in prds/ and epics/ directories only.
        Implements basic debouncing to avoid spam from rapid file changes.
        """
        # Skip directory events
        if event.is_directory:
            return False

        # Only process .md files
        if not event.src_path.endswith('.md'):
            return False

        # Only process files in prds/ or epics/ subdirectories
        path = Path(event.src_path)
        if not any(parent.name in ['prds', 'epics'] for parent in path.parents):
            return False

        # Basic debouncing - avoid duplicate events for same file
        event_key = f"{event.src_path}:{event.event_type}"
        if event_key in self.processed_events:
            return False

        self.processed_events.add(event_key)

        # Clear processed events after cooldown period
        self._schedule(self._clear_event_after_delay(event_key))

        return True

    async def _clear_event_after_delay(self, event_key: str):
        """Clear processed event after cooldown period."""
        await asyncio.sleep(self.event_cooldown)
        self.processed_events.discard(event_key)

    async def _broadcast_event(self, event_type: str, event):
        """
        Broadcast file system event to planning WebSocket clients.

        Args:
            event_type: Type of event (file_updated, file_created, file_deleted)
            event: Watchdog file system event object
        """
        try:
            path = Path(event.src_path)

            # Determine file type from parent directory
            file_type = None
            for parent in path.parents:
                if parent.name in ['prds', 'epics']:
                    file_type = parent.name
                    break

            if not file_type:
                logger.warning(f"Could not determine file type for {event.src_path}")
                return

            # Get file info if file still exists
            file_info = {}
            if event_type != 'file_deleted' and path.exists():
                try:
                    stat = path.stat()
                    file_info = {
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
                    }
                except (OSError, IOError) as e:
                    logger.warning(f"Could not get file stats for {path}: {e}")

            # Broadcast event
            event_data = {
                'event_type': event_type,
                'file_path': str(path),
                'file_type': file_type.rstrip('s'),  # 'prds' -> 'prd', 'epics' -> 'epic'
                'filename': path.name,
                'name': path.stem,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                **file_info
            }

            # Use the planning-specific broadcast method
            await self.connection_manager.broadcast_planning(event_data)

            logger.info(f"Broadcasted {event_type} for {path.name}")

        except Exception as e:
            logger.error(f"Failed to broadcast file event: {e}")


class PlanningFileWatcher:
    """
    File watcher manager for planning mode.

    Manages watchdog Observer lifecycle and coordinates with WebSocket broadcasting.
    """

    def __init__(self, connection_manager, watch_path: str = ".pm"):
        self.connection_manager = connection_manager
        self.watch_path = Path(watch_path)
        self.observer: Optional[Observer] = None
        self.handler: Optional[PlanningFileHandler] = None
        self.is_running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self):
        """
        Start file watching for planning documents.

        Sets up watchdog Observer to monitor .pm directory for changes.
        """
        try:
            if self.is_running:
                logger.warning("File watcher already running")
                return

            # Check if watch directory exists
            if not self.watch_path.exists():
                logger.warning(f"Watch directory {self.watch_path} does not exist - creating it")
                self.watch_path.mkdir(parents=True, exist_ok=True)
                # Create prds and epics subdirectories
                (self.watch_path / "prds").mkdir(exist_ok=True)
                (self.watch_path / "epics").mkdir(exist_ok=True)

            # Capture the currently running asyncio loop
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                self.loop = None

            # Initialize handler and observer (pass main loop for thread-safe scheduling)
            self.handler = PlanningFileHandler(self.connection_manager, loop=self.loop)
            self.observer = Observer()

            # Watch the entire .pm directory recursively
            self.observer.schedule(self.handler, str(self.watch_path), recursive=True)

            # Start observer in thread
            self.observer.start()
            self.is_running = True

            logger.info(f"Started file watcher for {self.watch_path}")

        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            await self.stop()

    async def stop(self):
        """Stop file watching."""
        try:
            if self.observer and self.observer.is_alive():
                self.observer.stop()
                self.observer.join(timeout=5.0)

            self.observer = None
            self.handler = None
            self.is_running = False

            logger.info("Stopped file watcher")

        except Exception as e:
            logger.error(f"Error stopping file watcher: {e}")

    def is_watching(self) -> bool:
        """Check if file watcher is currently active."""
        return self.is_running and self.observer and self.observer.is_alive()


# Global file watcher instance
_file_watcher: Optional[PlanningFileWatcher] = None


async def start_file_watcher(connection_manager) -> PlanningFileWatcher:
    """
    Start the global file watcher instance.

    Args:
        connection_manager: WebSocket connection manager for broadcasting

    Returns:
        PlanningFileWatcher instance
    """
    global _file_watcher

    if _file_watcher is None:
        _file_watcher = PlanningFileWatcher(connection_manager)

    await _file_watcher.start()
    return _file_watcher


async def stop_file_watcher():
    """Stop the global file watcher instance."""
    global _file_watcher

    if _file_watcher:
        await _file_watcher.stop()
        _file_watcher = None


def get_file_watcher() -> Optional[PlanningFileWatcher]:
    """Get the current file watcher instance."""
    return _file_watcher
