import os
import json
import tempfile
import asyncio
from pathlib import Path
from typing import Optional

import aiohttp


class JellyfinClient:
    """Jellyfin API client for browsing and streaming music."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self._admin_token: Optional[str] = None

    async def connect(self) -> Optional[str]:
        """Authenticate and get admin token. Returns token or None on failure."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/Users/AuthenticateByName",
                    json={"Username": self.username, "Pw": self.password}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._admin_token = data.get("AccessToken")
                        return self._admin_token
        except aiohttp.ClientError:
            return None

    def _headers(self) -> dict:
        if self._admin_token:
            return {"X-MediaBrowser-Token": self._admin_token}
        return {}

    async def browse_library(self, library_id: Optional[str] = None) -> list[dict]:
        """Browse Jellyfin library returns item list."""
        url = f"{self.base_url}/Users/{self._get_user_id()}/Items"
        if library_id:
            url += f"?parentId={library_id}&Fields=MediaSourceInfo,Chapters"
        params = {}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers=self._headers(), params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except aiohttp.ClientError:
            return []

    async def search(self, query: str, limit: int = 20) -> list[dict]:
        """Search Jellyfin with Music filter."""
        url = f"{self.base_url}/Users/{self._get_user_id()}/Items"
        params = {
            "SearchTerm": query,
            "IncludeItemTypes": "MusicAudio",
            "Limit": limit,
            "Fields": "MediaSourceInfo,Chapters",
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers=self._headers(), params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except aiohttp.ClientError:
            return []

    async def stream(self, item_id: str) -> Optional[dict]:
        """Generate streaming URL for an item."""
        url = f"{self.base_url}/Audio/{item_id}/stream"
        params = {"container": "ts", "audioCodec": "aac", "static": "true"}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers=self._headers(), params=params) as resp:
                    if resp.status == 200:
                        return {"url": resp.url, "headers": self._headers()}
        except aiohttp.ClientError:
            return None

    def _get_user_id(self) -> str:
        """Get authenticated user ID (simplified)."""
        return "admin"  # placeholder - fetch from auth response in real usage
