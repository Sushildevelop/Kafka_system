import asyncio
from collections import defaultdict

from fastapi import WebSocket


class GroupChatConnectionManager:
    """In-process WebSocket fan-out for the Kafka learning project."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, group_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[group_id].add(websocket)

    async def disconnect(self, group_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(group_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(group_id, None)

    async def broadcast(self, group_id: str, message: dict) -> None:
        async with self._lock:
            connections = list(self._connections.get(group_id, set()))
        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            await self.disconnect(group_id, websocket)


chat_connection_manager = GroupChatConnectionManager()
