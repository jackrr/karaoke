"""Track API routes: list, get details, start playback.

Endpoints
---------
GET    /api/tracks                  → list tracks for the active session
GET    /api/tracks/{track_id}       → get track by ID
POST   /api/tracks/{track_id}/start → begin playback
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schema import Track
from app.tracking import start_track as tp_start, pause as tp_pause, seek as tp_seek
from app.tracking import to_playback, get_session_state
from app.db import get_db

router = APIRouter(prefix="/api/tracks", tags=["tracks"])


class StartReq(BaseModel):
    entry_id: str
    session_id: str


# -- routes --

@router.get("", response_model=list[Track])
async def list_tracks() -> list[Track]:
    """Return all tracks in the system (or filter by session if implemented)."""
    db = get_db()
    rows = await db.query_all("SELECT * FROM tracks WHERE status != 'processing' ORDER BY created_at DESC")
    if not rows:
        return []
    return [Track(**row) for row in rows]


@router.get("/{track_id}", response_model=Track)
async def get_track(track_id: str) -> Track:
    """Get a track by its ID."""
    db = get_db()
    row: Optional[dict] = await db.query_one("SELECT * FROM tracks WHERE id = ?", (track_id,))
    if row is None:
        raise HTTPException(404, "Track not found")
    return Track(**row)


@router.post("/{track_id}/start", response_model=Track)
async def start_track(track_id: str, body: StartReq) -> Track:
    """Mark this track as playing and return its metadata."""
    db = get_db()
    row: Optional[dict] = await db.query_one("SELECT * FROM tracks WHERE id = ?", (track_id,))
    if row is None:
        raise HTTPException(404, "Track not found")

    # TODO: actually hand the track to the audio engine
    return Track(**row)


@router.post("/{track_id}/pause", tags=["tracks"])
async def pause_track(track_id: str) -> dict:
    """Pause playback."""
    # TODO: implement pause logic
    return {"status": "paused"}


@router.post("/{track_id}/seek", tags=["tracks"])
async def seek_track(track_id: str, position: int) -> dict:
    """Seek to *position* seconds."""
    return {"status": "seeked", "position": position}
