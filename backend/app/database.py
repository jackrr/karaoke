import aiosqlite

from .config import settings

# Singleton database connection
db_conn: aiosqlite.Connection | None = None


def start_db() -> None:
    """Initialize the database on first call (from lifespan or test startup)."""
    global db_conn
    if db_conn is not None:
        return

    db_path = settings.database_path
    db_conn = aiosqlite.connect(db_path)


async def get_db() -> aiosqlite.Connection:
    """Return the singleton async database connection."""
    if db_conn is None:
        raise RuntimeError(
            "Database connection not initialized. Ensure the app lifespan or test client has started."
        )
    return db_conn


async def close_db() -> None:
    global db_conn
    if db_conn is not None:
        await db_conn.close()
        db_conn = None


def reset_db() -> None:
    """Close and clear the db connection (for fresh test runs)."""
    global db_conn
    db_conn = None
