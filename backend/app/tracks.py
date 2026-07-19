import asyncio
import shutil
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import settings
from .database import get_db
from .websocket_manager import _is_active_member, manager
from .youtube import extract_video_id, run_yt_dlp_sync, vtt_to_lrc

tracks_router = APIRouter()

_TRACK_COLUMNS = (
    "id, session_id, source_url, youtube_video_id, title, status, error_message, "
    "audio_path, lyrics_path, lyrics_source, duration_seconds, requested_by_client_id, "
    "created_at, updated_at"
)


class TrackCreate(BaseModel):
    url: str
    client_id: str


def _row_to_track(row: Any) -> dict:
    (
        id_,
        session_id,
        source_url,
        youtube_video_id,
        title,
        status,
        error_message,
        audio_path,
        lyrics_path,
        lyrics_source,
        duration_seconds,
        requested_by_client_id,
        created_at,
        updated_at,
    ) = row
    return {
        "id": id_,
        "session_id": session_id,
        "source_url": source_url,
        "youtube_video_id": youtube_video_id,
        "title": title,
        "status": status,
        "error_message": error_message,
        "audio_path": audio_path,
        "lyrics_path": lyrics_path,
        "lyrics_source": lyrics_source,
        "duration_seconds": duration_seconds,
        "requested_by_client_id": requested_by_client_id,
        "created_at": created_at,
        "updated_at": updated_at,
    }


async def _get_track(db, track_id: str) -> dict | None:
    async with db.execute(
        f"SELECT {_TRACK_COLUMNS} FROM tracks WHERE id = ?", (track_id,)
    ) as cursor:
        row = await cursor.fetchone()
    return _row_to_track(row) if row else None


async def _session_exists(db, session_id: str) -> bool:
    async with db.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)) as cursor:
        row = await cursor.fetchone()
    return row is not None


@tracks_router.post("/sessions/{session_id}/tracks", status_code=202, response_model=None)
async def create_track(
    session_id: str, body: TrackCreate, background_tasks: BackgroundTasks
) -> dict | JSONResponse:
    video_id = extract_video_id(body.url)
    if video_id is None:
        raise HTTPException(status_code=422, detail="Not a valid YouTube URL")

    db = await get_db()
    if not await _session_exists(db, session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    if not await _is_active_member(session_id, body.client_id):
        raise HTTPException(
            status_code=403, detail="Not an active member of this session"
        )

    track_id = str(uuid4())
    try:
        await db.execute(
            "INSERT INTO tracks (id, session_id, source_url, youtube_video_id, "
            "status, requested_by_client_id) VALUES (?, ?, ?, ?, 'pending', ?)",
            (track_id, session_id, body.url, video_id, body.client_id),
        )
        await db.commit()
    except sqlite3.IntegrityError:
        async with db.execute(
            f"SELECT {_TRACK_COLUMNS} FROM tracks "
            "WHERE session_id = ? AND youtube_video_id = ? AND status != 'error'",
            (session_id, video_id),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            raise HTTPException(
                status_code=409, detail="This track is already queued for this session"
            )
        return JSONResponse(status_code=409, content=_row_to_track(row))

    track = await _get_track(db, track_id)
    if track is None:
        raise HTTPException(status_code=500, detail="Track vanished after insert")
    await manager.broadcast_event(session_id, "track_added", track)

    background_tasks.add_task(
        process_track_download, track_id, session_id, body.url, settings.storage_dir
    )

    return track


@tracks_router.get("/sessions/{session_id}/tracks")
async def list_tracks(session_id: str) -> dict:
    db = await get_db()
    if not await _session_exists(db, session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    async with db.execute(
        f"SELECT {_TRACK_COLUMNS} FROM tracks WHERE session_id = ? ORDER BY created_at",
        (session_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return {"tracks": [_row_to_track(row) for row in rows]}


async def _update_track(db, track_id: str, **fields) -> None:
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    await db.execute(
        f"UPDATE tracks SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*fields.values(), track_id),
    )
    await db.commit()


async def process_track_download(
    track_id: str, session_id: str, url: str, storage_dir: str
) -> None:
    db = await get_db()
    dest_dir = Path(storage_dir) / "tracks" / track_id

    async def _broadcast_current() -> None:
        track = await _get_track(db, track_id)
        if track is not None:
            await manager.broadcast_event(session_id, "track_updated", track)

    try:
        await _update_track(db, track_id, status="downloading")
        await _broadcast_current()

        dest_dir.mkdir(parents=True, exist_ok=True)
        result = await asyncio.to_thread(run_yt_dlp_sync, url, dest_dir)

        if result.vtt_path is not None:
            await _update_track(db, track_id, status="fetching_lyrics")
            await _broadcast_current()
            vtt_content = await asyncio.to_thread(result.vtt_path.read_text)
            lrc_content = vtt_to_lrc(vtt_content)
            lyrics_path = dest_dir / "lyrics.lrc"
            await asyncio.to_thread(lyrics_path.write_text, lrc_content)
            lyrics_source = "captions"
            lyrics_path_str: str | None = str(lyrics_path)
        else:
            lyrics_source = "none"
            lyrics_path_str = None

        await _update_track(
            db,
            track_id,
            status="downloaded",
            audio_path=str(result.audio_path),
            title=result.title,
            duration_seconds=result.duration_seconds,
            lyrics_path=lyrics_path_str,
            lyrics_source=lyrics_source,
        )
        await _broadcast_current()
    except Exception:
        await _update_track(
            db,
            track_id,
            status="error",
            error_message="Failed to download this video. Please try again.",
        )
        await _broadcast_current()
        shutil.rmtree(dest_dir, ignore_errors=True)
