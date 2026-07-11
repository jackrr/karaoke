import aiosqlite

from .config import settings

# Singleton database connect coroutine
_db_connect_task = None
_db_conn: aiosqlite.Connection | None = None  # cache actual connection


def start_db(path: str | None = None) -> None:
    """Initialize the database on first call (from lifespan or test startup)."""
    global _db_conn, _db_connect_task
    if _db_connect_task is not None:
        return
    db_path = path or settings.database_path
    _db_connect_task = aiosqlite.connect(db_path)


async def get_db() -> aiosqlite.Connection:
    """Return the singleton async database connection (cached after first use)."""
    global _db_conn, _db_connect_task
    if _db_conn is not None:
        return _db_conn
    if _db_connect_task is None:
        raise RuntimeError(
            "Database connection not initialized. Ensure the app lifespan or test client has started."
        )
    _db_conn = await _db_connect_task
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
