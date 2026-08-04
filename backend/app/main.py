import asyncio
import contextlib
import logging
import secrets
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import settings
from .database import close_db, get_db, start_db, touch_session
from .reaper import run_reaper_loop
from .tracks import _session_exists, tracks_router
from .websocket_manager import _is_active_member, ws_router, manager

# Uvicorn only configures its own "uvicorn.*" loggers, not the root logger,
# so our app-level loggers (e.g. app.tracks) would otherwise have no handler
# and silently drop everything below WARNING.
logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s")


class SessionCreate(BaseModel):
    display_name: str
    client_id: str | None = None
    vocal_volume_fraction: float | None = Field(default=None, ge=0.0, le=1.0)


class SessionCreateResponse(BaseModel):
    id: str
    code: str
    host_client_id: str
    client_id: str
    vocal_volume_fraction: float


class SessionSettingsUpdate(BaseModel):
    client_id: str
    vocal_volume_fraction: float = Field(ge=0.0, le=1.0)


class SessionJoinByCode(BaseModel):
    code: str
    display_name: str
    client_id: str | None = None


class SessionJoinResponse(BaseModel):
    id: str
    client_id: str
    is_host: bool


class SessionLeave(BaseModel):
    client_id: str


class PlaybackUpdate(BaseModel):
    client_id: str
    track_id: str
    is_playing: bool


class PlaybackRequest(BaseModel):
    client_id: str
    track_id: str


logger = logging.getLogger(__name__)


def _ensure_data_dirs() -> None:
    if settings.database_path != ":memory:":
        parent = Path(settings.database_path).expanduser().parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)


def _log_gpu_status() -> None:
    try:
        import torch

        available = torch.cuda.is_available()
        if available:
            logger.info("CUDA available: True (device: %s)", torch.cuda.get_device_name(0))
        else:
            logger.info("CUDA available: False")
            if settings.demucs_device == "auto":
                logger.warning(
                    "No GPU detected — demucs separation will run on CPU and be much slower"
                )
    except Exception as exc:
        logger.info("Could not determine GPU availability: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_data_dirs()
    _log_gpu_status()
    start_db()
    reaper_task = asyncio.create_task(
        run_reaper_loop(
            settings.storage_dir, settings.session_ttl_seconds, settings.reaper_interval_seconds
        )
    )
    yield
    reaper_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await reaper_task
    await close_db()


app = FastAPI(title="Karaoke API", lifespan=lifespan)
app.include_router(ws_router)
app.include_router(tracks_router)


async def _generate_unique_code(db) -> str:
    """Generate a zero-padded 6-digit code unique across sessions.

    Retries on collision — vanishingly unlikely with 1e6 possible codes, but
    the retry loop keeps the invariant enforced even under contention.
    """
    for _ in range(50):
        candidate = f"{secrets.randbelow(1_000_000):06d}"
        async with db.execute(
            "SELECT 1 FROM sessions WHERE code = ?", (candidate,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return candidate
    raise RuntimeError("Failed to generate a unique code")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sessions")
async def list_sessions() -> dict:
    db = await get_db()
    async with db.execute("SELECT COUNT(*) FROM sessions") as cursor:
        row = await cursor.fetchone()
    assert row is not None
    return {"count": row[0]}


@app.post("/sessions", status_code=201)
async def create_session(body: SessionCreate) -> SessionCreateResponse:
    db = await get_db()
    sid = str(uuid4())
    host_client_id = body.client_id or str(uuid4())
    fraction = (
        body.vocal_volume_fraction
        if body.vocal_volume_fraction is not None
        else settings.vocal_volume_fraction
    )

    for _ in range(10):
        code = await _generate_unique_code(db)
        try:
            await db.execute(
                "INSERT INTO sessions (id, code, host_client_id, vocal_volume_fraction) "
                "VALUES (?, ?, ?, ?)",
                (sid, code, host_client_id, fraction),
            )
        except sqlite3.IntegrityError:
            # Another concurrent create grabbed this code between our
            # pre-check and this insert — regenerate and retry.
            continue
        break
    else:
        raise RuntimeError("Failed to create session with a unique code")

    await _upsert_member(db, sid, host_client_id, body.display_name)
    await touch_session(db, sid)
    await db.commit()
    return SessionCreateResponse(
        id=sid,
        code=code,
        host_client_id=host_client_id,
        client_id=host_client_id,
        vocal_volume_fraction=fraction,
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


@app.post("/sessions/join")
async def join_session_by_code(body: SessionJoinByCode) -> SessionJoinResponse:
    """Join a session by code alone, for the "I have a code" flow where the
    client doesn't already know the session's id."""
    db = await get_db()
    async with db.execute(
        "SELECT id, host_client_id FROM sessions WHERE code = ?", (body.code,)
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No session found for that code")
    session_id, host_client_id = row

    client_id = body.client_id or str(uuid4())
    await _upsert_member(db, session_id, client_id, body.display_name)
    await touch_session(db, session_id)
    await db.commit()

    return SessionJoinResponse(
        id=session_id,
        client_id=client_id,
        is_host=client_id == host_client_id,
    )


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    db = await get_db()
    async with db.execute(
        "SELECT id, code, host_client_id, created_at, now_playing_track_id, is_playing, "
        "vocal_volume_fraction "
        "FROM sessions WHERE id = ?",
        (session_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    (
        sid,
        code,
        host_client_id,
        created_at,
        now_playing_track_id,
        is_playing,
        vocal_volume_fraction,
    ) = row

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
        "code": code,
        "host_client_id": host_client_id,
        "created_at": created_at,
        "online": len(manager.active.get(session_id, {})),
        "participants": participants,
        "now_playing_track_id": now_playing_track_id,
        "is_playing": bool(is_playing),
        "vocal_volume_fraction": (
            vocal_volume_fraction
            if vocal_volume_fraction is not None
            else settings.vocal_volume_fraction
        ),
    }


@app.get("/sessions/{session_id}/settings")
async def get_session_settings(session_id: str) -> dict:
    db = await get_db()
    async with db.execute(
        "SELECT vocal_volume_fraction FROM sessions WHERE id = ?", (session_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    (vocal_volume_fraction,) = row
    return {
        "vocal_volume_fraction": (
            vocal_volume_fraction
            if vocal_volume_fraction is not None
            else settings.vocal_volume_fraction
        )
    }


@app.put("/sessions/{session_id}/settings")
async def update_session_settings(session_id: str, body: SessionSettingsUpdate) -> dict:
    db = await get_db()
    if not await _session_exists(db, session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    if not await _is_active_member(session_id, body.client_id):
        raise HTTPException(
            status_code=403, detail="Not an active member of this session"
        )

    await db.execute(
        "UPDATE sessions SET vocal_volume_fraction = ? WHERE id = ?",
        (body.vocal_volume_fraction, session_id),
    )
    await touch_session(db, session_id)
    await db.commit()

    await manager.broadcast_event(
        session_id,
        "session_settings_updated",
        {"vocal_volume_fraction": body.vocal_volume_fraction},
    )
    return {"vocal_volume_fraction": body.vocal_volume_fraction}


@app.post("/sessions/{session_id}/leave", status_code=204)
async def leave_session(session_id: str, body: SessionLeave) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE session_members SET left_at = CURRENT_TIMESTAMP "
        "WHERE session_id = ? AND client_id = ? AND left_at IS NULL",
        (session_id, body.client_id),
    )
    await touch_session(db, session_id)
    await db.commit()
    await manager.broadcast_event(session_id, "member_left", {"client_id": body.client_id})


@app.post("/sessions/{session_id}/playback")
async def update_playback_state(session_id: str, body: PlaybackUpdate) -> dict:
    db = await get_db()
    async with db.execute(
        "SELECT host_client_id FROM sessions WHERE id = ?", (session_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    (host_client_id,) = row

    if body.client_id != host_client_id:
        raise HTTPException(status_code=403, detail="Only the host can update playback state")

    if not await _is_active_member(session_id, body.client_id):
        raise HTTPException(
            status_code=403, detail="Not an active member of this session"
        )

    async with db.execute(
        "SELECT status FROM tracks WHERE id = ? AND session_id = ?",
        (body.track_id, session_id),
    ) as cursor:
        track_row = await cursor.fetchone()
    if track_row is None:
        raise HTTPException(status_code=404, detail="Track not found in this session")
    (track_status,) = track_row
    if track_status != "ready":
        raise HTTPException(status_code=409, detail="Track is not ready for playback")

    await db.execute(
        "UPDATE sessions SET now_playing_track_id = ?, is_playing = ?, "
        "playback_updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (body.track_id, int(body.is_playing), session_id),
    )
    await touch_session(db, session_id)
    await db.commit()

    await manager.broadcast_event(
        session_id,
        "playback_state_changed",
        {"track_id": body.track_id, "is_playing": body.is_playing},
    )
    return {"track_id": body.track_id, "is_playing": body.is_playing}


@app.post("/sessions/{session_id}/playback/request")
async def request_playback(session_id: str, body: PlaybackRequest) -> dict:
    db = await get_db()
    async with db.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)) as cursor:
        session_row = await cursor.fetchone()
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not await _is_active_member(session_id, body.client_id):
        raise HTTPException(
            status_code=403, detail="Not an active member of this session"
        )

    async with db.execute(
        "SELECT 1 FROM tracks WHERE id = ? AND session_id = ?",
        (body.track_id, session_id),
    ) as cursor:
        track_row = await cursor.fetchone()
    if track_row is None:
        raise HTTPException(status_code=404, detail="Track not found in this session")

    await manager.broadcast_event(
        session_id,
        "play_requested",
        {"track_id": body.track_id, "requested_by_client_id": body.client_id},
    )
    return {"track_id": body.track_id, "requested_by_client_id": body.client_id}


# The container image mirrors the repo layout (/app/backend/app, /app/frontend/build),
# so this relative path is load-bearing for deploys as well as local dev.
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
