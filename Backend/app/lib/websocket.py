from typing import Dict, List
import asyncio

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """
    Simple per-project WebSocket connection manager.

    - Each project_id has its own list of WebSocket connections.
    - You can send to one socket, all sockets for a project, or broadcast to everyone.
    """

    def __init__(self) -> None:
        # project_id -> list[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # FIX #9: Lock to prevent race conditions during disconnect
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, project_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            if project_id not in self.active_connections:
                self.active_connections[project_id] = []
            self.active_connections[project_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, project_id: str) -> None:
        """Thread-safe disconnect."""
        async with self._lock:
            connections = self.active_connections.get(project_id, [])
            if websocket in connections:
                connections.remove(websocket)
            if not connections and project_id in self.active_connections:
                del self.active_connections[project_id]

    async def send_json(self, websocket: WebSocket, data: dict) -> None:
        await websocket.send_json(data)

    async def send_to_project(self, project_id: str, message: dict) -> None:
        """
        Send a JSON message to all clients connected for a given project_id.
        Thread-safe: takes a snapshot of connections under lock.
        """
        # Take a snapshot under lock to avoid iteration issues
        async with self._lock:
            connections = list(self.active_connections.get(project_id, []))
        
        disconnected: List[WebSocket] = []

        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                # mark for removal
                disconnected.append(ws)

        # Clean up dead connections (uses the async disconnect now)
        for ws in disconnected:
            await self.disconnect(ws, project_id)

    async def broadcast_json(self, message: dict) -> None:
        """
        Broadcast a JSON message to all connected websockets across all projects.
        """
        projects = list(self.active_connections.keys())
        for project_id in projects:
            await self.send_to_project(project_id, message)

    async def broadcast(self, project_id: str, message: dict) -> None:
        """
        Convenience / backwards-compatible alias: broadcast to a single project.
        """
        await self.send_to_project(project_id, message)


manager = ConnectionManager()
