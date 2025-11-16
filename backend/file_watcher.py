"""
File System Watcher for Real-Time Collaboration.

This module monitors the workspace directory for file changes and broadcasts
them to connected WebSocket clients. It uses the watchdog library for
efficient file system monitoring.

Features:
- Monitors workspace directory for file modifications
- Filters out temporary files and directories
- Broadcasts changes via WebSocket manager
- Debounces rapid changes to avoid broadcast spam
- Thread-safe operations with proper cleanup
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

logger = logging.getLogger(__name__)


class WorkspaceFileHandler(FileSystemEventHandler):
    """
    Handles file system events for workspace files.

    Monitors file modifications and broadcasts changes to WebSocket clients.
    Implements debouncing to avoid duplicate broadcasts for rapid changes.
    """

    def __init__(self, workspace_root: Path, ws_manager, debounce_seconds: float = 0.5):
        """
        Initialize file handler.

        Args:
            workspace_root: Path to workspace directory being monitored
            ws_manager: WebSocket connection manager for broadcasting
            debounce_seconds: Minimum time between broadcasts for same file
        """
        super().__init__()
        self.workspace_root = workspace_root
        self.ws_manager = ws_manager
        self.debounce_seconds = debounce_seconds

        # Track recently modified files with timestamps to debounce
        self._recent_changes: dict[str, float] = {}

        logger.info(f"📁 [FileWatcher] Initialized for {workspace_root}")

    def _should_ignore_path(self, path: str) -> bool:
        """
        Determine if path should be ignored.

        Filters out:
        - Hidden files/directories (start with .)
        - Temporary files (.tmp, .swp, etc.)
        - Python cache (__pycache__, .pyc)
        - Editor temp files (~, .bak)

        Args:
            path: File path to check

        Returns:
            True if path should be ignored, False otherwise
        """
        path_obj = Path(path)

        # Ignore hidden files/directories
        if any(part.startswith('.') for part in path_obj.parts):
            return True

        # Ignore temporary and cache files
        ignore_patterns = {
            '.tmp', '.swp', '.pyc', '.pyo', '~', '.bak',
            '__pycache__', '.DS_Store'
        }

        if path_obj.name in ignore_patterns:
            return True

        if any(path_obj.name.endswith(pattern) for pattern in ignore_patterns):
            return True

        return False

    def _should_broadcast(self, file_path: str) -> bool:
        """
        Determine if change should be broadcast based on debounce logic.

        Args:
            file_path: Path to file that changed

        Returns:
            True if change should be broadcast, False if debounced
        """
        now = time.time()
        last_change = self._recent_changes.get(file_path, 0)

        # If file was modified recently (within debounce window), skip
        if now - last_change < self.debounce_seconds:
            logger.debug(f"⏭️  [FileWatcher] Debounced: {file_path} (last change {now - last_change:.2f}s ago)")
            return False

        # Update timestamp and allow broadcast
        self._recent_changes[file_path] = now
        return True

    def on_modified(self, event):
        """
        Handle file modification events.

        Args:
            event: FileSystemEvent from watchdog
        """
        # Only handle file modifications (not directory)
        if event.is_directory:
            return

        # Only handle FileModifiedEvent
        if not isinstance(event, FileModifiedEvent):
            return

        file_path = event.src_path

        # Ignore filtered paths
        if self._should_ignore_path(file_path):
            return

        # Get relative path from workspace root
        try:
            relative_path = Path(file_path).relative_to(self.workspace_root)
            relative_path_str = str(relative_path)
        except ValueError:
            # Path is outside workspace (shouldn't happen but be safe)
            logger.warning(f"⚠️  [FileWatcher] Path outside workspace: {file_path}")
            return

        # Check debounce
        if not self._should_broadcast(file_path):
            return

        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                new_content = f.read()
        except UnicodeDecodeError:
            # Skip binary files
            logger.debug(f"⏭️  [FileWatcher] Skipped binary file: {relative_path_str}")
            return
        except Exception as e:
            logger.error(f"❌ [FileWatcher] Error reading {relative_path_str}: {e}")
            return

        logger.info(
            f"📝 [FileWatcher] File modified: {relative_path_str} "
            f"({len(new_content)} chars)"
        )

        # Broadcast change asynchronously
        # We don't have old_content, so pass empty string
        # This will cause conflict detection on client side if needed
        asyncio.run(
            self.ws_manager.broadcast_file_change(
                file_path=relative_path_str,
                old_content="",  # Unknown - let client detect conflicts
                new_content=new_content,
                editor_user_id="file_system",  # Mark as external change
                change_metadata={
                    "timestamp": time.time(),
                    "change_type": "external",
                    "file_size": len(new_content),
                    "editor": "file_system"
                }
            )
        )


class FileWatcher:
    """
    File system watcher service for workspace monitoring.

    Manages watchdog Observer lifecycle and handles graceful shutdown.
    """

    def __init__(self, workspace_root: Path, ws_manager):
        """
        Initialize file watcher.

        Args:
            workspace_root: Path to workspace directory to monitor
            ws_manager: WebSocket connection manager for broadcasting
        """
        self.workspace_root = workspace_root
        self.ws_manager = ws_manager
        self.observer: Observer | None = None
        self.event_handler: WorkspaceFileHandler | None = None

        logger.info(f"🔍 [FileWatcher] Created for {workspace_root}")

    def start(self):
        """
        Start file system monitoring.

        Creates workspace directory if it doesn't exist and starts
        the watchdog Observer in a background thread.
        """
        # Ensure workspace directory exists
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # Create event handler
        self.event_handler = WorkspaceFileHandler(
            self.workspace_root,
            self.ws_manager,
            debounce_seconds=0.5  # Wait 500ms between broadcasts for same file
        )

        # Create and start observer
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            path=str(self.workspace_root),
            recursive=True  # Monitor all subdirectories
        )
        self.observer.start()

        logger.info(
            f"✅ [FileWatcher] Started monitoring {self.workspace_root} "
            f"(recursive: True)"
        )

    def stop(self):
        """
        Stop file system monitoring.

        Gracefully shuts down the watchdog Observer and waits for
        background thread to complete.
        """
        if self.observer:
            logger.info("🛑 [FileWatcher] Stopping observer...")
            self.observer.stop()
            self.observer.join(timeout=5.0)  # Wait up to 5 seconds
            self.observer = None
            logger.info("✅ [FileWatcher] Stopped")
        else:
            logger.debug("ℹ️  [FileWatcher] Observer not running")
