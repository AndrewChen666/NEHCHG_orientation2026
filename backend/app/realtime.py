import asyncio
from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

from fastapi import WebSocket


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, session_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            self._subscribers[session_id].add(websocket)

    async def unsubscribe(self, session_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(session_id)
            if subscribers is None:
                return
            subscribers.discard(websocket)
            if not subscribers:
                self._subscribers.pop(session_id, None)

    async def publish(self, session_id: UUID, event: dict[str, object]) -> None:
        async with self._lock:
            subscribers: Iterable[WebSocket] = tuple(self._subscribers.get(session_id, ()))
        stale: list[WebSocket] = []
        for websocket in subscribers:
            try:
                await websocket.send_json(event)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            await self.unsubscribe(session_id, websocket)

