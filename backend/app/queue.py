"""Queue service for managing track queue."""
from typing import Optional
import aiosqlite
import secrets
from datetime import datetime

from .db import get_db
from .schema import QueueEntry, QueueEntryCreate, QueueStatus, Track, TrackStatus


async def enqueue(entry_create: QueueEntryCreate, session_id: str, db: Optional[aiosqlite.Connection] = None) -> QueueEntry:
    """Enqueue a track to a session's queue."""
    if db is None:
        db = await get_db().connection()

    # Get next position
    cursor = await db.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 FROM queue_entries WHERE session_id = ?",
        (session_id,)
    )
    row = await cursor.fetchone()
    position = row[0] if row and row[0] is not None else 0

    entry_id = secrets.token_hex(16)
    now = int(datetime.now().timestamp())

    await db.execute(
        "INSERT INTO queue_entries (id, session_id, track_id, position, status, added_by, source, metadata, added_at) "
        "VALUES (?, ?, NULL, ?, 'pending', ?, ?, ?, ?)",
        (entry_id, session_id, position, entry_create.client_id, entry_create.source.value,
         {"source_url": entry_create.source_url}, now)
    )
    await db.commit()

    return QueueEntry(
        id=entry_id,
        session_id=session_id,
        track_id=None,
        position=position,
        status=QueueStatus.pending,
        added_by=entry_create.client_id,
        source=entry_create.source.value,
        metadata={"source_url": entry_create.source_url},
        added_at=now
    )


async def reorder(entry_id: str, new_position: int, client_id: str, db: Optional[aiosqlite.Connection] = None) -> QueueEntry:
    """Reorder a queue entry to a new position."""
    if db is None:
        db = await get_db().connection()

    cursor = await db.execute("SELECT session_id, position FROM queue_entries WHERE id = ?", (entry_id,))
    row = await cursor.fetchone()
    if not row:
        raise ValueError("Queue entry not found")

    session_id, old_position = row[0], row[1]
    if old_position == new_position:
        # Fetch current entry and return
        return await _fetch_entry(entry_id, db)

    # Step 1: shift entries between old and new
    if old_position < new_position:
        await db.execute(
            "UPDATE queue_entries SET position = position - 1 "
            "WHERE session_id = ? AND position > ? AND position <= ?",
            (session_id, old_position, new_position)
        )
    else:
        await db.execute(
            "UPDATE queue_entries SET position = position + 1 "
            "WHERE session_id = ? AND position >= ? AND position < ?",
            (session_id, new_position, old_position)
        )

    await db.commit()

    # Step 2: move the target entry
    await db.execute("UPDATE queue_entries SET position = ? WHERE id = ?", (new_position, entry_id))
    await db.commit()

    return await _fetch_entry(entry_id, db)


async def _fetch_entry(entry_id: str, db: aiosqlite.Connection) -> QueueEntry:
    """Fetch a queue entry by ID."""
    cursor = await db.execute("SELECT * FROM queue_entries WHERE id = ?", (entry_id,))
    row = await cursor.fetchone()
    if not row:
        raise ValueError("Queue entry not found")
    cols = [d[0] for d in cursor.description]
    return QueueEntry(**dict(zip(cols, row)))


async def remove(entry_id: str, client_id: str, db: Optional[aiosqlite.Connection] = None) -> None:
    """Remove a queue entry."""
    if db is None:
        db = await get_db().connection()

    # Get session_id for renumbering
    cursor = await db.execute("SELECT session_id FROM queue_entries WHERE id = ?", (entry_id,))
    row = await cursor.fetchone()
    if not row:
        return
    session_id = row[0]

    await db.execute("DELETE FROM queue_entries WHERE id = ?", (entry_id,))

    # Renumber remaining entries
    await db.execute(
        "UPDATE queue_entries SET position = position - 1 "
        "WHERE session_id = ? AND position > ?",
        (session_id,
         (await db.execute(
             "SELECT position FROM queue_entries WHERE session_id = ? AND position > (SELECT position FROM queue_entries WHERE session_id = ? AND id = ?) "
             "ORDER BY position LIMIT 1",
             (session_id, session_id, entry_id),
         )).fetchone()[0] if (
             await db.execute(
                 "SELECT position FROM queue_entries WHERE session_id = ? AND position > (SELECT position FROM queue_entries WHERE session_id = ? AND id = ?) "
                 "ORDER BY position LIMIT 1",
                 (session_id, session_id, entry_id),
             ).fetchone()
         ) else None)
    )
    # Simpler: just renumber all entries above the deleted one's old position
    await db.commit()


async def clear_session(session_id: str, client_id: str, db: Optional[aiosqlite.Connection] = None) -> None:
    """Clear all queue entries for a session."""
    if db is None:
        db = await get_db().connection()

    await db.execute("DELETE FROM queue_entries WHERE session_id = ?", (session_id,))
    await db.commit()


async def get_queue(session_id: str, db: Optional[aiosqlite.Connection] = None) -> list[QueueEntry]:
    """Get all queue entries for a session."""
    if db is None:
        db = await get_db().connection()

    cursor = await db.execute(
        "SELECT id, session_id, track_id, position, status, added_by, source, metadata, added_at FROM queue_entries "
        "WHERE session_id = ? ORDER BY position",
        (session_id,)
    )
    rows = await cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    return [QueueEntry(**dict(zip(cols, row))) for row in rows]


async def get_queue_by_passcode(passcode: str, db: Optional[aiosqlite.Connection] = None) -> list[QueueEntry]:
    """Get queue entries by passcode."""
    if db is None:
        db = await get_db().connection()

    db2 = await get_db().connection()
    cursor = await db2.execute(
        "SELECT id FROM sessions WHERE passcode = ? AND status = 'active'",
        (passcode,)
    )
    row = await cursor.fetchone()
    if not row:
        return []

    return await get_queue(row[0], db)


async def advance_to_next(session_id: str, db: Optional[aiosqlite.Connection] = None) -> Optional[Track]:
    """Advance to the next track in the queue."""
    if db is None:
        db = await get_db().connection()

    # Remove current playing track from queue
    await db.execute("DELETE FROM queue_entries WHERE session_id = ? AND status = 'playing'", (session_id,))

    # Get next entry
    cursor = await db.execute(
        "SELECT id, session_id, track_id, position, status, added_by, source, metadata, added_at FROM queue_entries "
        "WHERE session_id = ? ORDER BY position LIMIT 1",
        (session_id,)
    )
    row = await cursor.fetchone()
    if not row:
        await db.commit()
        return None

    cols = [d[0] for d in cursor.description]
    entry = QueueEntry(**dict(zip(cols, row)))

    # Get track details
    track_cursor = await db.execute(
        "SELECT id, hash, title, artist, duration, storage_path, "
        "lyrics_format, lyrics_source, lyric_lines, fallback_text, status, created_at "
        "FROM tracks WHERE id = ?",
        (entry.track_id,)
    )
    track_row = await track_cursor.fetchone()
    if track_row:
        track_cols = [d[0] for d in track_cursor.description]
        await db.commit()
        return Track(**dict(zip(track_cols, track_row)))

    await db.commit()
    return None
