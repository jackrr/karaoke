"""
Routes package — registers all FastAPI routers.

Mounting is handled in ``app.main.mount_routes()`` which is called from
``lifespan``.
"""
from fastapi import APIRouter

from app.api.routes import sessions, queue, tracks, upload, jellyfin

def get_router() -> APIRouter:
    """Create a router with all sub-routes attached."""
    router = APIRouter(tags=["api"])
    router.include_router(sessions.router)
    router.include_router(queue.router)
    router.include_router(tracks.router)
    router.include_router(upload.router)
    router.include_router(jellyfin.router)
    return router
