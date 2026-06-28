"""Track playback state per session and push live updates via WebSocket.

Public API
--
    start(session_id, track_id) → mark a track as playing
    pause(session_id)           → pause playback
    seek(session_id, position)  → jump to position (seconds)
    tick(session_id, dt)        → advance playback by dt seconds
    get_session_state(session_id)   → playback state for a session
    broadcast_state(state)       → broadcast to all WS clients

Events are broadcast to all connected WebSocket clients.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Any

from fastapi import APIRouter

from app.schema import PlaybackState
from app.db import get_db

router = APIRouter(prefix="/api/playback", tags=["playback"])


# ── In-memory state ────────────────────────────────────────────

@dataclass
class _SessionState:
    session_id: str
    track_id: Optional[str] = None
    current_position: float = 0.0
    is_playing: bool = False
    started_at: Optional[int] = None


# Global in-memory state (sufficient for karaoke with a few concurrent sessions)
_sessions: dict[str, _SessionState] = {}


def _get(session_id: str) -> _SessionState:
    if session_id not in _sessions:
        _sessions[session_id] = _SessionState(session_id=session_id)
    return _sessions[session_id]


# ── Actions ─────────────────────────────────────────────────────

async def start_track(session_id: str, track_id: str) -> PlaybackState:
    """Begin playback of *track_id* for *session_id*."""
    db = get_db()
    db_conn = await db.connection()
    state = _get(session_id)
    state.session_id = session_id
    state.track_id = track_id
    state.current_position = 0.0
    state.is_playing = True
    state.started_at = int(time.time())

    # Persist
    await db_conn.execute(
        "INSERT INTO sessions_playback "
        "(session_id, track_id, position, is_playing, started_at) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(session_id) DO UPDATE SET "
        "track_id = ?, position = ?, is_playing = ?, started_at = ?",
        (state.session_id, state.track_id,
         state.current_position, int(state.is_playing), state.started_at,
         state.track_id, state.current_position,
         int(state.is_playing), state.started_at)
    )
    await db_conn.commit()

    await broadcast_state(state)
    return to_playback(state)


async def pause(session_id: str) -> PlaybackState:
    state = _get(session_id)
    state.is_playing = False
    await _persist(state)
    await broadcast_state(state)
    return to_playback(state)


async def seek(session_id: str, position: int) -> PlaybackState:
    state = _get(session_id)
    state.current_position = position
    await _persist(state)
    return to_playback(state)


async def tick(session_id: str, dt: float) -> PlaybackState:
    state = _get(session_id)
    state.current_position += dt
    await _persist(state)
    await broadcast_state(state)
    return to_playback(state)


# ── Helpers ─────────────────────────────────────────────────────

async def _persist(state: _SessionState):
    db = get_db()
    db_conn = await db.connection()
    await db_conn.execute(
        "INSERT INTO sessions_playback "
        "(session_id, track_id, position, is_playing, started_at) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(session_id) DO UPDATE SET "
        "track_id = ?, position = ?, is_playing = ?, started_at = ?",
        (state.session_id, state.track_id or None,
         state.current_position, int(state.is_playing), state.started_at,
         state.track_id, state.current_position,
         int(state.is_playing), state.started_at)
    )
    await db_conn.commit()


def get_session_state(session_id: str) -> PlaybackState:
    return to_playback(_get(session_id))


def to_playback(state: _SessionState) -> PlaybackState:
    return PlaybackState(
        session_id=state.session_id,
        track_id=state.track_id,
        current_position=state.current_position,
        is_playing=state.is_playing,
        started_at=state.started_at,
    )


async def broadcast_state(state: _SessionState):
    """Broadcast current playback state to all connected WebSocket clients."""
    # Stub — will be implemented via the WebSocket manager
    pass


# ── Routes ──────────────────────────────────────────────────────

@router.get("/{session_id}", response_model=PlaybackState)
def get_position(session_id: str) -> PlaybackState:
    """Get playback position for a session."""
    return get_session_state(session_id)


@router.get("", response_model=list[dict])
def list_positions():
    """List all tracked playback positions."""
    return [to_playback(s).model_dump() for s in _sessions.values()]


# ── Streaming Client Manager (stub) ─────────────────────

class StreamingClientManager:
    """Manages streaming playback clients per session.

    Stub — wired up to the WebSocket manager for future real-time streaming.
    """

    async def start(self, session_id: str, track_id: str):
        """Start streaming a track."""
        pass

    async def stop(self, session_id: str):
        """Stop streaming for a session."""
        pass
