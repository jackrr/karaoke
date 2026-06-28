"""Backend application package.

Exports:
    init_db()          — get the Database singleton
    close_db()         — graceful shutdown coroutine
    lifespan()         — FastAPI lifespan context manager (startup + shutdown)
"""

from contextlib import asynccontextmanager

from app.db import init_db, close_db

from app.config import settings


@asynccontextmanager
async def lifespan(app):  # type: ignore[no-untyped-def]
    """Startup and shutdown hooks for FastAPI."""
    # Startup
    from app.db import get_db

    db = get_db()
    await db.connect()
    app.state.settings = settings
    app.state.db = db
    app.state.session_expiry_secs = 24 * 3600
    app.state.heartbeat_interval = 15

    yield  # app runs here

    # Shutdown
    await close_db()
