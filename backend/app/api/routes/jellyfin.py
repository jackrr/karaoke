"""Jellyfin API proxy routes: browse library, search, and initiate streaming."""
import httpx
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/jellyfin", tags=["jellyfin"])


class JellyfinConfig(BaseModel):
    server_url: str
    api_key: str


@router.get("/browse/{server}")
async def browse_library(server: str):
    """Browse a Jellyfin server's audio library (proxy).

    Expects the Jellyfin server URL and API key to be stored in
    the database under the active session's config table.
    """
    config = await get_jellyfin_config(server)
    if not config:
        raise HTTPException(status_code=404, detail="Jellyfin server not configured")

    # Proxy the request to the Jellyfin server
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{config['server_url']}/Users/me/Items",
            headers={"X-MediaBrowser-Token": config["api_key"]},
            params={"Recursive": True, "MediaTypes": "Audio", "SortBy": "SortName"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Jellyfin error: {resp.text}")

        return resp.json()


@router.get("/search/{server}")
async def search_library(server: str, q: str):
    """Search a Jellyfin server's audio library.

    Query parameter ``q`` must be URL-encoded.
    """
    config = await get_jellyfin_config(server)
    if not config:
        raise HTTPException(status_code=404, detail="Jellyfin server not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{config['server_url']}/Users/me/Items",
            headers={"X-MediaBrowser-Token": config["api_key"]},
            params={"SearchTerm": q, "MediaTypes": "Audio"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Jellyfin error: {resp.text}")
        return resp.json()


@router.post("/stream")
async def stream_jellyfin(req: JellyfinConfig):
    """Initiate a stream from a Jellyfin server.

    Returns a Jellyfin auth URL or token for downstream playback.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        session_resp = await client.post(
            f"{req.server_url}/Sessions",
            headers={"X-MediaBrowser-Token": req.api_key},
            json={"Auth": {"Name": "karaoke-stream", "DeviceName": "karaoke-webapp", "DeviceId": "karaoke"}},
        )
        if session_resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Jellyfin session error: {session_resp.text}")
        return {"session_id": session_resp.json().get("Id")}


async def get_jellyfin_config(server_id: str) -> dict | None:
    """Look up Jellyfin server config from the active session."""
    # Placeholder: will read from a DB table once schema exists
    return None
