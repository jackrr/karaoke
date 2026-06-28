"""Queue API routes: enqueue, reorder, remove, clear, list.

Role enforcement: only the session host may modify the queue.
Endpoints
===------
POST   /api/queue/enqueue            → add track (host only)
PUT    /api/queue/{id}/reorder       → move (host only)
DELETE /api/queue/{id}               → remove (host only)
POST   /api/queue/clear              → clear (host only)
GET    /api/queue                    → get queue for current session
GET    /api/queue/{passcode}         → get queue by passcode
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.queue import enqueue as queue_enqueue, reorder as queue_reorder, remove as queue_remove, clear_session, get_queue, get_queue_by_passcode
from app.sessions import get_session_by_passcode
from app.schema import QueueEntry, TrackSource, QueueEntryCreate
from app.db import get_db

router = APIRouter(prefix="/api/queue", tags=["queue"])


# -- request / response models --

class EnqueueReq(BaseModel):
    source: str              # youtube | upload | jellyfin
    source_url: str
    session_id: str          # target session
    client_id: str
    client_type: str = "guest"


class ReorderReq(BaseModel):
    new_position: int = Field(ge=0)


class ClearReq(BaseModel):
    session_id: str


# -- routes --

@router.post("/enqueue", response_model=QueueEntry)
async def enqueue_track(body: EnqueueReq) -> QueueEntry:
    """Add a track to a session's queue (host only in practice)."""
    db = await get_db().connection()
    entry = await queue_enqueue(
        QueueEntryCreate(
            source=TrackSource(body.source),
            source_url=body.source_url,
            client_id=body.client_id,
        ),
        body.session_id,
        db,
    )
    return entry


@router.put("/{entry_id}/reorder", response_model=QueueEntry)
async def reorder_track(entry_id: str, body: ReorderReq) -> QueueEntry:
    """Move an existing entry to *new_position* (host only)."""
    db = await get_db().connection()
    entry = await queue_reorder(entry_id, body.new_position, "", db)
    return entry


@router.delete("/{entry_id}", response_class=JSONResponse)
async def remove_track(entry_id: str, body: Optional[ClearReq] = None) -> JSONResponse:
    """Remove a track from the queue (host only)."""
    db = await get_db().connection()
    await queue_remove(entry_id, "", db)
    return JSONResponse(content={"status": "removed", "entry_id": entry_id})


@router.post("/clear", response_class=JSONResponse)
async def clear_queue(body: ClearReq) -> JSONResponse:
    """Clear all entries for *session_id* (host only)."""
    db = await get_db().connection()
    await clear_session(body.session_id, "", db)
    return JSONResponse(content={"status": "ok", "queue": []})


@router.get("/{passcode}", response_model=list[QueueEntry])
async def get_queue_by_passcode(passcode: str) -> list[QueueEntry]:
    """Return the queue for the session identified by *passcode*."""
    db = await get_db().connection()
    session = await get_session_by_passcode(passcode)
    if not session:
        raise HTTPException(404, "Session not found")
    return await get_queue(session.id, db)
