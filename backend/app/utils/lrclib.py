"""LRCLIB lyrics client for fetching karaoke-friendly lyrics."""
import httpx
from typing import Optional


class LRCLIBClient:
    """Client for the LRCLIB lyrics API."""

    def __init__(self, base_url: str = "https://lrclib.net/api"):
        self.base_url = base_url.rstrip("/")

    async def search_lyrics(self, title: str, artist: str) -> Optional[dict]:
        """Search for lyrics matching title and artist."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.base_url}/search"
                resp = await client.get(url, params={"track_name": title, "artist_name": artist})
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None
