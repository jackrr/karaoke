"""Database recovery helpers for the karaoke session management layer."""
from typing import Optional, Dict
from pathlib import Path
import aiosqlite


class RecoveryHelper:
    """Recover session and queue state from database."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        await aiosqlite.connect(self.db_path)
    
    async def close(self):
        if self.db:
            await self.db.close()
    
    async def recover_session(self, session_id: str) -> Optional[dict]:
        """Recover session data from the database."""
        if not self.db:
            await self.connect()
        cursor = await self.db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    
    async def recover_queue(self, session_id: str) -> list[dict]:
        """Recover the queue for a session."""
        if not self.db:
            await self.connect()
        cursor = await self.db.execute(
            "SELECT * FROM queue_entries WHERE session_id = ? ORDER BY position",
            (session_id,)
        )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in rows]
    
    async def recover_track_status(self, track_id: str) -> Optional[str]:
        """Recover the processing status of a track."""
        if not self.db:
            await self.connect()
        cursor = await self.db.execute(
            "SELECT status FROM tracks WHERE id = ?", (track_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None
    
    async def recover_client_history(self, client_id: str) -> Optional[dict]:
        """Recover client state."""
        if not self.db:
            await self.connect()
        cursor = await self.db.execute(
            "SELECT * FROM clients WHERE client_id = ?", (client_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
