from contextlib import asynccontextmanager
from typing import Dict, Set
from uuid import uuid4

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .database import close_db, get_db, start_db, is_db_created, start_db

# --- WebSocket manager ---


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


# --- Routes ---


class SessionCreate(BaseModel):
    name: str


class SessionResponse(BaseModel):
    id: str
    name: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_db()
    start_db()  # Initialize the DB for this lifespan instance
    yield
    await close_db()


app = FastAPI(title="Karaoke API", lifespan=lifespan)
app.include_router(ws_router)


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sessions")
async def list_sessions() -> dict:
    db = await get_db()
    async with db.execute("SELECT id, name FROM sessions ORDER BY created_at DESC") as cursor:
        rows = await cursor.fetchall()
    return {
        "sessions": [{"id": row[0], "name": row[1]} for row in rows]
    }


@app.post("/sessions", status_code=201)
async def create_session(body: SessionCreate) -> SessionResponse:
    db = await get_db()
    sid = str(uuid4())
    await db.execute("INSERT INTO sessions (id, name) VALUES (?, ?)", (sid, body.name))
    await db.commit()
    return SessionResponse(id=sid, name=body.name)
