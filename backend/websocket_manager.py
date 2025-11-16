"""
WebSocket Connection Manager for Real-Time Collaborative Editing.

This module implements file-based WebSocket rooms with:
- Multi-user connection management per file
- Large file chunking (>100KB)
- Thread-safe operations with async locks
- Automatic room cleanup
- Editor exclusion from broadcasts (no echo-back)

Reference: INTEGRATION_CONTRACT.md for type definitions and interfaces.
"""

import asyncio
import logging
import time
from typing import Dict, Optional

from fastapi import WebSocket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants (must match INTEGRATION_CONTRACT.md)
CHUNK_SIZE_BYTES = 102400  # 100KB


class ConnectionManager:
    """
    Manages WebSocket connections with file-based rooms.

    Attributes:
        active_connections: Dict mapping file paths to user connections
                           {file_path: {user_id: websocket}}
    """

    def __init__(self):
        """Initialize connection manager with empty rooms and async lock."""
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        file_path: str,
        user_id: str
    ) -> None:
        """
        Add authenticated client to file-specific room.

        Args:
            websocket: FastAPI WebSocket connection
            file_path: Relative file path from workspace root
            user_id: Authenticated user identifier
        """
        async with self._lock:
            # Create room if it doesn't exist
            if file_path not in self.active_connections:
                self.active_connections[file_path] = {}
                logger.info(f"Created new room for file: {file_path}")

            # Add user to room
            self.active_connections[file_path][user_id] = websocket
            room_size = len(self.active_connections[file_path])
            logger.info(
                f"User {user_id} connected to {file_path} "
                f"(room size: {room_size})"
            )

    async def disconnect(
        self,
        websocket: WebSocket,
        file_path: str,
        user_id: str
    ) -> None:
        """
        Remove client and cleanup empty rooms.

        Args:
            websocket: FastAPI WebSocket connection
            file_path: Relative file path from workspace root
            user_id: User identifier
        """
        async with self._lock:
            # Remove user from room if exists
            if file_path in self.active_connections:
                if user_id in self.active_connections[file_path]:
                    del self.active_connections[file_path][user_id]
                    logger.info(f"User {user_id} disconnected from {file_path}")

                # Cleanup empty rooms
                if not self.active_connections[file_path]:
                    del self.active_connections[file_path]
                    logger.info(f"Removed empty room for file: {file_path}")
                else:
                    room_size = len(self.active_connections[file_path])
                    logger.info(
                        f"Room {file_path} still active "
                        f"(remaining users: {room_size})"
                    )

    async def broadcast_file_change(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        editor_user_id: str = "ai_agent",
        change_metadata: Optional[dict] = None
    ) -> None:
        """
        Broadcast file changes to all connected clients (except editor).

        For large files (>100KB), automatically chunks the message.

        Args:
            file_path: Relative file path from workspace root
            old_content: Content before change (for conflict detection)
            new_content: Content after change
            editor_user_id: ID of user/agent making the change (default: "ai_agent")
            change_metadata: Optional metadata dict with timestamp, file_size, etc.
        """
        # Skip if no active connections for this file
        if file_path not in self.active_connections:
            logger.info(f"⚠️  No active connections for {file_path}, skipping broadcast")
            return

        # Build metadata
        if change_metadata is None:
            change_metadata = {}

        # Add default metadata fields
        metadata = {
            "timestamp": change_metadata.get("timestamp", time.time()),
            "editor": change_metadata.get("editor", editor_user_id),
            "file_size": change_metadata.get("file_size", len(new_content))
        }

        # Determine if chunking is needed
        content_size = len(new_content.encode('utf-8'))
        needs_chunking = content_size > CHUNK_SIZE_BYTES

        async with self._lock:
            # Get all connections except the editor
            recipients = {
                uid: ws
                for uid, ws in self.active_connections[file_path].items()
                if uid != editor_user_id
            }

            if not recipients:
                logger.info(
                    f"⚠️  No recipients for broadcast to {file_path} "
                    f"(editor {editor_user_id} excluded, total connections: {len(self.active_connections[file_path])})"
                )
                return

            logger.info(
                f"✅ Broadcasting change to {file_path} "
                f"(recipients: {len(recipients)}, chunked: {needs_chunking}, editor: {editor_user_id})"
            )

        # Broadcast to all recipients
        if needs_chunking:
            await self._broadcast_chunked(
                recipients,
                file_path,
                old_content,
                new_content,
                metadata
            )
        else:
            await self._broadcast_single(
                recipients,
                file_path,
                old_content,
                new_content,
                metadata
            )

    async def _broadcast_single(
        self,
        recipients: Dict[str, WebSocket],
        file_path: str,
        old_content: str,
        new_content: str,
        metadata: dict
    ) -> None:
        """
        Broadcast single message to all recipients.

        Args:
            recipients: Dict of {user_id: websocket}
            file_path: Relative file path
            old_content: Content before change
            new_content: Content after change
            metadata: Change metadata
        """
        message = {
            "type": "file_change",
            "file_path": file_path,
            "old_content": old_content,
            "new_content": new_content,
            "metadata": metadata
        }

        # Send to all recipients concurrently
        await self._send_to_all(recipients, message)

    async def _broadcast_chunked(
        self,
        recipients: Dict[str, WebSocket],
        file_path: str,
        old_content: str,
        new_content: str,
        metadata: dict
    ) -> None:
        """
        Broadcast large file in chunks to all recipients.

        Args:
            recipients: Dict of {user_id: websocket}
            file_path: Relative file path
            old_content: Content before change
            new_content: Content after change
            metadata: Change metadata
        """
        # Calculate chunks
        content_bytes = new_content.encode('utf-8')
        total_chunks = (len(content_bytes) + CHUNK_SIZE_BYTES - 1) // CHUNK_SIZE_BYTES

        logger.info(
            f"Chunking {file_path}: {len(content_bytes)} bytes "
            f"into {total_chunks} chunks"
        )

        # Send chunks sequentially
        for chunk_index in range(total_chunks):
            start_byte = chunk_index * CHUNK_SIZE_BYTES
            end_byte = min(start_byte + CHUNK_SIZE_BYTES, len(content_bytes))
            chunk_bytes = content_bytes[start_byte:end_byte]
            chunk_text = chunk_bytes.decode('utf-8')

            message = {
                "type": "file_change_chunk",
                "file_path": file_path,
                "old_content": old_content if chunk_index == 0 else None,
                "content_chunk": chunk_text,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "metadata": metadata if chunk_index == 0 else None
            }

            # Send chunk to all recipients
            await self._send_to_all(recipients, message)

            logger.debug(
                f"Sent chunk {chunk_index + 1}/{total_chunks} "
                f"of {file_path} ({len(chunk_bytes)} bytes)"
            )

    async def _send_to_all(
        self,
        recipients: Dict[str, WebSocket],
        message: dict
    ) -> None:
        """
        Send message to all recipients, handling disconnections.

        Args:
            recipients: Dict of {user_id: websocket}
            message: Message dictionary to send as JSON
        """
        # Create tasks for concurrent sending
        send_tasks = [
            self._safe_send(user_id, websocket, message)
            for user_id, websocket in recipients.items()
        ]

        # Execute all sends concurrently
        await asyncio.gather(*send_tasks, return_exceptions=True)

    async def _safe_send(
        self,
        user_id: str,
        websocket: WebSocket,
        message: dict
    ) -> None:
        """
        Safely send message to a single websocket with error handling.

        Args:
            user_id: User identifier (for logging)
            websocket: WebSocket connection
            message: Message dictionary to send as JSON
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(
                f"Failed to send to user {user_id}: {type(e).__name__}: {e}"
            )
            # Note: Connection cleanup will happen in disconnect()
            # when the WebSocket endpoint detects the broken connection

    async def broadcast(self, message: dict) -> None:
        """
        Broadcast a message to ALL connected clients across all rooms.

        This is used for system-wide events like tool approval requests.

        Args:
            message: Message dictionary to send as JSON
        """
        async with self._lock:
            # Get all connected websockets across all rooms
            all_websockets = {}
            for file_path, users in self.active_connections.items():
                for user_id, websocket in users.items():
                    all_websockets[f"{file_path}:{user_id}"] = websocket

            if not all_websockets:
                logger.info("⚠️ No active connections for broadcast")
                return

            logger.info(f"📡 Broadcasting message to {len(all_websockets)} clients")

        # Send to all clients concurrently
        send_tasks = [
            self._safe_send(connection_id, websocket, message)
            for connection_id, websocket in all_websockets.items()
        ]
        await asyncio.gather(*send_tasks, return_exceptions=True)


# Singleton instance
manager = ConnectionManager()
