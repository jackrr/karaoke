import asyncio

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


async def create_tables(conn: aiosqlite.Connection) -> None:
    """Create database tables if they don't exist."""
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            passcode TEXT NOT NULL UNIQUE,
            host_client_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
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
    await conn.commit()


async def cleanup_tables(conn: aiosqlite.Connection) -> None:
    """Drop database tables (for test teardown)."""
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
