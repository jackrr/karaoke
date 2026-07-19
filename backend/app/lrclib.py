"""Pure, testable helper for fetching synced lyrics from lrclib.net.

Deliberately has no FastAPI or DB imports — `tracks.py` wires this into the
web app and background-task machinery, calling it as a fallback when
yt-dlp doesn't provide timed captions. The seam for tests is
`httpx2.AsyncClient`: tests monkeypatch it with a fake client/response, so
no real network call is ever made.
"""

import httpx2

_BASE_URL = "https://lrclib.net/api"
_TIMEOUT = 10.0
_USER_AGENT = "karaoke-app (https://github.com/jackrr/karaoke)"


async def fetch_synced_lyrics(
    title: str,
    artist: str | None = None,
    album: str | None = None,
    duration: float | None = None,
) -> str | None:
    """Look up synced (LRC) lyrics for a track on lrclib.net.

    Tries the exact-match `/api/get` endpoint first, then falls back to the
    free-text `/api/search` endpoint. Returns the first non-empty
    `syncedLyrics` found, or None if no match is found or any error occurs.
    Never raises — this is a soft-fail fallback and a lrclib outage must
    never fail the whole track download pipeline.
    """
    headers = {"User-Agent": _USER_AGENT}
    try:
        async with httpx2.AsyncClient(
            base_url=_BASE_URL, timeout=_TIMEOUT, headers=headers
        ) as client:
            synced = await _try_get(client, title, artist, album, duration)
            if synced:
                return synced
            return await _try_search(client, title, artist)
    except Exception:
        return None


async def _try_get(
    client: httpx2.AsyncClient,
    title: str,
    artist: str | None,
    album: str | None,
    duration: float | None,
) -> str | None:
    params: dict[str, str] = {"track_name": title}
    if artist:
        params["artist_name"] = artist
    if album:
        params["album_name"] = album
    if duration is not None:
        params["duration"] = str(int(duration))

    try:
        resp = await client.get("/get", params=params)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception:
        return None

    if not isinstance(data, dict):
        return None
    synced = data.get("syncedLyrics")
    return synced if synced else None


async def _try_search(
    client: httpx2.AsyncClient, title: str, artist: str | None
) -> str | None:
    params: dict[str, str] = {"q": title}
    if artist:
        params["artist_name"] = artist

    try:
        resp = await client.get("/search", params=params)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception:
        return None

    if not isinstance(data, list):
        return None
    for entry in data:
        if isinstance(entry, dict):
            synced = entry.get("syncedLyrics")
            if synced:
                return synced
    return None
