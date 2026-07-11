from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self) -> None:
        self.active: Dict[str, set[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active.setdefault(session_id, set()).add(ws)

    def discard(self, session_id: str, ws: WebSocket) -> None:
        if session_id in self.active:
            self.active[session_id].discard(ws)
            if not self.active[session_id]:
                del self.active[session_id]

    async def broadcast(self, session_id: str, message: str) -> None:
        dead: list[WebSocket] = []
        for ws in list(self.active.get(session_id, set())):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.discard(session_id, ws)


manager = ConnectionManager()

ws_router = APIRouter()


@ws_router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(session_id, data)
    except WebSocketDisconnect:
        manager.discard(session_id, websocket)
