"""DMUCS (Track Service) — Jellyfin client for karaoke."""
from pathlib import Path
from typing import Optional
import asyncio

from .db import get_db
from .schema import Track, TrackStatus
import aiosqlite

class TrackService:
    """Jellyfin integration for karaoke."""
    
    def __init__(self, db: aiosqlite, jellyfin_client: Optional['JellyfinClient'] = None):
        self.db = db
        self.jellyfin_client = jellyfin_client
    
    async def get_streams(self, session_id: str) -> list[Track]:
        """Get all streams for a session."""
        cursor = await self.db.execute("SELECT * FROM tracks WHERE session_id = ? ORDER BY created_at DESC", (session_id,))
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [Track(**dict(zip(cols, row))) for row in rows]
    
    async def update_track_status(self, track_id: str, status: TrackStatus):
        """Update a track's processing status."""
        await self.db.execute("UPDATE tracks SET status = ? WHERE id = ?", (status.value, track_id))
        await self.db.commit()
    
    async def get_stream(self, track_id: str) -> Optional[Track]:
        """Get a single stream."""
        cursor = await self.db.execute("SELECT * FROM tracks WHERE id = ?", (track_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return Track(**dict(zip(cols, row)))

# module-level instance
track_service = TrackService(None)  # placeholder

from .jellyfin_client import JellyfinClient
