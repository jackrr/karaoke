from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .database import close_db, get_db, start_db
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
    app.mount(
        "/_app", StaticFiles(directory=str(_FRONTEND_STATIC_PATH / "_app")), name="frontend-assets"
    )

    _INDEX_HTML_PATH = _FRONTEND_STATIC_PATH / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        """Serve a static file if it exists, else fall back to the SPA shell.

        `full_path` is client-side routed (e.g. `/session/<id>`), so any path
        that isn't a real static asset must still return `index.html` for the
        SvelteKit router to pick up.
        """
        candidate = (_FRONTEND_STATIC_PATH / full_path).resolve()
        if (
            candidate.is_file()
            and candidate.is_relative_to(_FRONTEND_STATIC_PATH)
        ):
            return FileResponse(candidate)
        return FileResponse(_INDEX_HTML_PATH)
