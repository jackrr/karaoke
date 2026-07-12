from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .database import close_db, create_tables, get_db, start_db
from .websocket_manager import ws_router, manager


class SessionCreate(BaseModel):
    name: str


class SessionResponse(BaseModel):
    id: str
    name: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_db()
    yield
    await close_db()


app = FastAPI(title="Karaoke API", lifespan=lifespan)
app.include_router(ws_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sessions")
async def list_sessions() -> dict:
    db = await get_db()
    async with db.execute("SELECT id, name FROM sessions ORDER BY created_at DESC") as cursor:
        rows = await cursor.fetchall()
    return {"sessions": [{"id": row[0], "name": row[1]} for row in rows]}


@app.post("/sessions", status_code=201)
async def create_session(body: SessionCreate) -> SessionResponse:
    db = await get_db()
    sid = str(uuid4())
    await db.execute("INSERT INTO sessions (id, name) VALUES (?, ?)", (sid, body.name))
    await db.commit()
    return SessionResponse(id=sid, name=body.name)


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    db = await get_db()
    async with db.execute(
        "SELECT id, name, created_at FROM sessions WHERE id = ?", (session_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": row[0],
        "name": row[1],
        "created_at": row[2],
        "online": len(manager.active.get(session_id, set())),
    }


@app.post("/sessions/{session_id}/leave", status_code=204)
async def leave_session(session_id: str) -> None:
    pass  # WebSocket cleanup handled in disconnect handler


_FRONTEND_STATIC_PATH = Path(__file__).resolve().parent.parent.parent / "frontend" / "build"
if _FRONTEND_STATIC_PATH.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_STATIC_PATH), html=True), name="frontend")
