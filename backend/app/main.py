from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel

from .database import close_db, get_db, start_db
from .websocket_manager import ws_router


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
