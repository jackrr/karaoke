import asyncio
import sqlite3

import aiosqlite

from .config import settings

# Singleton database connect coroutine
_db_connect_task = None
_db_conn: aiosqlite.Connection | None = None  # cache actual connection
_db_init_lock = asyncio.Lock()


def start_db(path: str | None = None) -> None:
    """Initialize the database on first call (from lifespan or test startup)."""
    global _db_conn, _db_connect_task
    if _db_connect_task is not None:
        return
    db_path = path or settings.database_path
    _db_connect_task = aiosqlite.connect(db_path)


async def _ensure_last_active_at_column(conn: aiosqlite.Connection) -> None:
    """Add `last_active_at` to a `sessions` table created before this column
    existed. `CREATE TABLE IF NOT EXISTS` above is a no-op against an
    already-existing on-disk database, so this ALTER TABLE is what actually
    backfills the column there. Guarded because it's also a no-op on a fresh
    database (column already present from the CREATE TABLE) or on any
    subsequent call."""
    try:
        await conn.execute(
            "ALTER TABLE sessions ADD COLUMN last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        )
    except sqlite3.OperationalError:
        pass


async def touch_session(conn: aiosqlite.Connection, session_id: str) -> None:
    """Bump a session's `last_active_at` to now.

    Piggybacks on the caller's own commit — callers should already be about
    to commit their own change, so this doesn't commit itself.
    """
    await conn.execute(
        "UPDATE sessions SET last_active_at = CURRENT_TIMESTAMP WHERE id = ?",
        (session_id,),
    )


async def create_tables(conn: aiosqlite.Connection) -> None:
    """Create database tables if they don't exist."""
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            host_client_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await _ensure_last_active_at_column(conn)
    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_last_active_at
        ON sessions (last_active_at)
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_members (
            session_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            left_at TIMESTAMP,
            PRIMARY KEY (session_id, client_id)
        )
        """
    )
    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_members_session_id
        ON session_members (session_id)
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES sessions(id),
            source_url TEXT NOT NULL,
            youtube_video_id TEXT NOT NULL,
            title TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT,
            audio_path TEXT,
            lyrics_path TEXT,
            lyrics_source TEXT,
            duration_seconds REAL,
            requested_by_client_id TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tracks_session_id ON tracks (session_id)
        """
    )
    await conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tracks_session_video
            ON tracks (session_id, youtube_video_id)
            WHERE status != 'error'
        """
    )
    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tracks_session_position
        ON tracks (session_id, position)
        """
    )
    await conn.commit()


async def cleanup_tables(conn: aiosqlite.Connection) -> None:
    """Drop database tables (for test teardown)."""
    await conn.execute("DROP TABLE IF EXISTS tracks")
    await conn.execute("DROP TABLE IF EXISTS session_members")
    await conn.execute("DROP TABLE IF EXISTS sessions")
    await conn.commit()


async def get_db() -> aiosqlite.Connection:
    """Return the singleton async database connection (cached after first use)."""
    global _db_conn, _db_connect_task
    if _db_conn is not None:
        return _db_conn
    if _db_connect_task is None:
        raise RuntimeError(
            "Database connection not initialized. Ensure the app lifespan or test client has started."
        )
    async with _db_init_lock:
        # Re-check: another caller may have finished initializing while we waited on the lock.
        if _db_conn is None:
            _db_conn = await _db_connect_task
            await create_tables(_db_conn)
    return _db_conn


async def close_db() -> None:
    global _db_conn, _db_connect_task
    if _db_conn is not None:
        try:
            await _db_conn.close()
        except Exception:
            pass
    _db_conn = None
    _db_connect_task = None


def reset_db() -> None:
    """Close and clear the db connection (for fresh test runs)."""
    global _db_conn, _db_connect_task
    if _db_conn is not None:
        try:
            _db_conn.close()  # ty: ignore[unused-awaitable] — sync-only cleanup, not an async API
        except Exception:
            pass
    _db_conn = None
    _db_connect_task = None
