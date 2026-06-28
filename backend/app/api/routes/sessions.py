"""Session API routes: create, join, query sessions and list clients.

Endpoints
===--------
POST   /api/sessions              → create a new session
POST   /api/sessions/join         → join session by passcode
GET    /api/sessions/{passcode}   → get session info
GET    /api/sessions/{id}/clients → list connected clients
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.sessions import create_session, join_session, get_session_by_passcode
from app.sessions import remove_client as remove_client_svc
from app.db import get_db
from app.schema import Session, SessionCreate, SessionJoin

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# -- request / response models --

class CreateSessionReq(BaseModel):
    client_id: str  # the host's client ID


class JoinSessionReq(BaseModel):
    passcode: str
    client_id: str
    client_type: str = "guest"


# -- routes --

@router.post("", response_model=Session)
async def create_session_route(body: CreateSessionReq) -> Session:
    """Create a new karaoke session; *client_id* becomes the host."""
    passcode = secrets.token_urlsafe(6)[:6].upper()
    if not passcode.isalnum():
        # fallback: pure alphanumeric
        passcode = secrets.token_hex(3).upper()
    session = await create_session(body.client_id)
    if session is None:
        raise HTTPException(500, "Could not create session")
    session.passcode = passcode
    return session


@router.post("/join", response_model=Session)
async def join_session_route(body: JoinSessionReq) -> Session:
    """Join an existing session. First caller becomes host if none is set."""
    session = await join_session(body.passcode, body.client_id)
    if session is None:
        raise HTTPException(404, "Session not found or expired")
    return session


@router.get("/{passcode}", response_model=Session)
async def get_session_info(passcode: str) -> Session:
    """Get session info by passcode."""
    session = await get_session_by_passcode(passcode)
    if session is None:
        raise HTTPException(404, "Session not found")
    return session


@router.get("/{session_id}/clients")
async def list_clients(session_id: str):
    """List every client in a session."""
    db = get_db()
    from app.sessions import get_session_clients
    import aiosqlite
    db_conn: aiosqlite.Connection = await db.connection()
    cursor = await db_conn.execute(
        "SELECT client_id, session_id, client_type, joined_at, connected, last_seen "
        "FROM clients WHERE session_id = ?",
        (session_id,)
    )
    rows = await cursor.fetchall()
    return [
        {"client_id": c, "session_id": s, "client_type": t, "joined_at": j, "connected": cn, "last_seen": ls}
        for c, s, t, j, cn, ls in rows
    ]
