"""Collect all sub-routers into a single FastAPI router mounted at *prefix=/api*.

Public interface
------------
    get_api_router() → FastAPI router (ready to include)
"""
from fastapi import APIRouter

from app.api.routes import jellyfin, queue, sessions, tracks, upload


def get_api_router() -> APIRouter:
    """Return a router with all API sub-routes attached at *prefix="/api"*."""
    api = APIRouter(prefix="/api")
    api.include_router(sessions.router)
    api.include_router(queue.router)
    api.include_router(tracks.router)
    api.include_router(upload.router)
    api.include_router(jellyfin.router)
    return api
