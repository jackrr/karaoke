"""FastAPI application with mounted API routes and WebSocket endpoint."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket

from app.config import settings
from app.websocket.manager import WebSocketManager
from app.db import init_db, close_db
from app.tracking import StreamingClientManager

# ── Logging ──────────────

logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(
        "%(levelname)s:%(name)s:%(message)s"
    ))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

# ── Lifespan ─────────────

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """Startup: connect DB, init WS manager.  Shutdown: cleanup."""
    logger.info("Starting up Karaoke app…")
    db_conn = await init_db()
    app.state.db = db_conn
    app.state.settings = settings

    ws_mgr = WebSocketManager()
    app.state.ws_manager = ws_mgr
    ws_mgr.start_heartbeat()

    logger.info("Karaoke app started")
    yield
    logger.info("Shutting down Karaoke app…")
    await close_db()

# ── App ──────────────────

app = FastAPI(
    title=settings.app_name if hasattr(settings, "app_name") else "Karaoke",
    debug=settings.demo if hasattr(settings, "demo") else False,
    lifespan=lifespan,
)

# ── CORS ─────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if hasattr(settings, "cors_origins") else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount API routes ─────

from app.api.routes import get_api_router
api_router = get_api_router()
app.include_router(api_router, prefix="/api")  # mounts at /api/* (sessions/queue/tracks/upload/jellyfin)

# ── WebSocket endpoint ───

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    ws_manager = app.state.ws_manager
    await ws_manager.handle_connection(websocket, session_id)

# ── Healthcheck ──────────

@app.get("/health")
def health():
    return {"status": "ok"}
