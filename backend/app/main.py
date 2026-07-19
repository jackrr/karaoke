import secrets
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .database import close_db, get_db, start_db
from .tracks import tracks_router
from .websocket_manager import ws_router, manager


class SessionCreate(BaseModel):
    name: str
    display_name: str
    client_id: str | None = None


class SessionCreateResponse(BaseModel):
    id: str
    name: str
    passcode: str
    host_client_id: str
    client_id: str


class SessionJoin(BaseModel):
    passcode: str
    display_name: str
    client_id: str | None = None


class SessionJoinByPasscode(BaseModel):
    passcode: str
    display_name: str
    client_id: str | None = None


class SessionJoinResponse(BaseModel):
    id: str
    name: str
    client_id: str
    is_host: bool


class SessionLeave(BaseModel):
    client_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_db()
    yield
    await close_db()


app = FastAPI(title="Karaoke API", lifespan=lifespan)
app.include_router(ws_router)
app.include_router(tracks_router)


async def _generate_unique_passcode(db) -> str:
    """Generate a zero-padded 6-digit passcode unique across sessions.

    Retries on collision — vanishingly unlikely with 1e6 possible codes, but
    the retry loop keeps the invariant enforced even under contention.
    """
    for _ in range(50):
        candidate = f"{secrets.randbelow(1_000_000):06d}"
        async with db.execute(
            "SELECT 1 FROM sessions WHERE passcode = ?", (candidate,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return candidate
    raise RuntimeError("Failed to generate a unique passcode")


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
async def create_session(body: SessionCreate) -> SessionCreateResponse:
    db = await get_db()
    sid = str(uuid4())
    host_client_id = body.client_id or str(uuid4())

    for _ in range(10):
        passcode = await _generate_unique_passcode(db)
        try:
            await db.execute(
                "INSERT INTO sessions (id, name, passcode, host_client_id) VALUES (?, ?, ?, ?)",
                (sid, body.name, passcode, host_client_id),
            )
        except sqlite3.IntegrityError:
            # Another concurrent create grabbed this passcode between our
            # pre-check and this insert — regenerate and retry.
            continue
        break
    else:
        raise RuntimeError("Failed to create session with a unique passcode")

    await _upsert_member(db, sid, host_client_id, body.display_name)
    return SessionCreateResponse(
        id=sid,
        name=body.name,
        passcode=passcode,
        host_client_id=host_client_id,
        client_id=host_client_id,
    )


async def _upsert_member(db, session_id: str, client_id: str, display_name: str) -> None:
    await db.execute(
        "INSERT INTO session_members (session_id, client_id, display_name) "
        "VALUES (?, ?, ?) "
        "ON CONFLICT(session_id, client_id) DO UPDATE SET "
        "display_name = excluded.display_name, left_at = NULL",
        (session_id, client_id, display_name),
    )
    await db.commit()


@app.post("/sessions/{session_id}/join")
async def join_session(session_id: str, body: SessionJoin) -> SessionJoinResponse:
    db = await get_db()
    async with db.execute(
        "SELECT name, passcode, host_client_id FROM sessions WHERE id = ?", (session_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    name, passcode, host_client_id = row
    if body.passcode != passcode:
        raise HTTPException(status_code=403, detail="Incorrect passcode")

    client_id = body.client_id or str(uuid4())
    await _upsert_member(db, session_id, client_id, body.display_name)

    return SessionJoinResponse(
        id=session_id,
        name=name,
        client_id=client_id,
        is_host=client_id == host_client_id,
    )


@app.post("/sessions/join")
async def join_session_by_passcode(body: SessionJoinByPasscode) -> SessionJoinResponse:
    """Join a session by passcode alone, for the "I have a code" flow where the
    client doesn't already know the session's id."""
    db = await get_db()
    async with db.execute(
        "SELECT id, name, host_client_id FROM sessions WHERE passcode = ?", (body.passcode,)
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No session found for that passcode")
    session_id, name, host_client_id = row

    client_id = body.client_id or str(uuid4())
    await _upsert_member(db, session_id, client_id, body.display_name)

    return SessionJoinResponse(
        id=session_id,
        name=name,
        client_id=client_id,
        is_host=client_id == host_client_id,
    )


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    db = await get_db()
    async with db.execute(
        "SELECT id, name, passcode, host_client_id, created_at FROM sessions WHERE id = ?",
        (session_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    sid, name, passcode, host_client_id, created_at = row

    async with db.execute(
        "SELECT client_id, display_name FROM session_members "
        "WHERE session_id = ? AND left_at IS NULL",
        (session_id,),
    ) as cursor:
        members = await cursor.fetchall()
    participants = [
        {
            "client_id": member_client_id,
            "display_name": display_name,
            "is_host": member_client_id == host_client_id,
        }
        for member_client_id, display_name in members
    ]

    return {
        "id": sid,
        "name": name,
        "passcode": passcode,
        "host_client_id": host_client_id,
        "created_at": created_at,
        "online": len(manager.active.get(session_id, {})),
        "participants": participants,
    }


@app.post("/sessions/{session_id}/leave", status_code=204)
async def leave_session(session_id: str, body: SessionLeave) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE session_members SET left_at = CURRENT_TIMESTAMP "
        "WHERE session_id = ? AND client_id = ? AND left_at IS NULL",
        (session_id, body.client_id),
    )
    await db.commit()
    await manager.broadcast_event(session_id, "member_left", {"client_id": body.client_id})


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
