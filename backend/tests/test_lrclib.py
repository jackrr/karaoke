import httpx2
import pytest

import app.lrclib as lrclib_module
from app.lrclib import fetch_synced_lyrics


class _FakeResponse:
    def __init__(self, status_code: int = 200, json_data=None, raise_json_error: bool = False):
        self.status_code = status_code
        self._json_data = json_data
        self._raise_json_error = raise_json_error

    def json(self):
        if self._raise_json_error:
            raise ValueError("malformed json")
        return self._json_data


class _FakeAsyncClient:
    """Stands in for `httpx2.AsyncClient` in tests: returns canned responses
    per-endpoint instead of touching the network, mirroring the interface
    `fetch_synced_lyrics` relies on (async context manager + `get`)."""

    get_response: _FakeResponse | Exception | None = None
    search_response: _FakeResponse | Exception | None = None
    calls: list[str] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str, params: dict | None = None):
        _FakeAsyncClient.calls.append(url)
        if url == "/get":
            response = _FakeAsyncClient.get_response
        elif url == "/search":
            response = _FakeAsyncClient.search_response
        else:
            raise AssertionError(f"unexpected url {url}")
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(autouse=True)
def _patch_client(monkeypatch):
    _FakeAsyncClient.get_response = None
    _FakeAsyncClient.search_response = None
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(lrclib_module.httpx2, "AsyncClient", _FakeAsyncClient)
    yield


async def test_get_endpoint_returns_synced_lyrics() -> None:
    _FakeAsyncClient.get_response = _FakeResponse(
        200, {"syncedLyrics": "[00:01.00]Hello"}
    )
    result = await fetch_synced_lyrics(title="Song", artist="Artist")
    assert result == "[00:01.00]Hello"
    assert _FakeAsyncClient.calls == ["/get"]


async def test_get_404_falls_back_to_search() -> None:
    _FakeAsyncClient.get_response = _FakeResponse(404, {})
    _FakeAsyncClient.search_response = _FakeResponse(
        200, [{"syncedLyrics": ""}, {"syncedLyrics": "[00:02.00]World"}]
    )
    result = await fetch_synced_lyrics(title="Song")
    assert result == "[00:02.00]World"
    assert _FakeAsyncClient.calls == ["/get", "/search"]


async def test_get_lacks_synced_lyrics_falls_back_to_search() -> None:
    _FakeAsyncClient.get_response = _FakeResponse(200, {"syncedLyrics": ""})
    _FakeAsyncClient.search_response = _FakeResponse(
        200, [{"syncedLyrics": "[00:03.00]Yo"}]
    )
    result = await fetch_synced_lyrics(title="Song")
    assert result == "[00:03.00]Yo"


async def test_no_synced_lyrics_anywhere_returns_none() -> None:
    _FakeAsyncClient.get_response = _FakeResponse(404, {})
    _FakeAsyncClient.search_response = _FakeResponse(200, [])
    result = await fetch_synced_lyrics(title="Song")
    assert result is None


async def test_search_entries_without_synced_lyrics_returns_none() -> None:
    _FakeAsyncClient.get_response = _FakeResponse(404, {})
    _FakeAsyncClient.search_response = _FakeResponse(
        200, [{"syncedLyrics": None}, {"plainLyrics": "no timing"}]
    )
    result = await fetch_synced_lyrics(title="Song")
    assert result is None


async def test_http_error_on_get_returns_none() -> None:
    _FakeAsyncClient.get_response = httpx2.ConnectError("boom")
    _FakeAsyncClient.search_response = _FakeResponse(200, [])
    result = await fetch_synced_lyrics(title="Song")
    assert result is None


async def test_timeout_error_returns_none() -> None:
    _FakeAsyncClient.get_response = httpx2.TimeoutException("timed out")
    _FakeAsyncClient.search_response = _FakeResponse(200, [])
    result = await fetch_synced_lyrics(title="Song")
    assert result is None


async def test_search_error_after_get_miss_returns_none() -> None:
    _FakeAsyncClient.get_response = _FakeResponse(404, {})
    _FakeAsyncClient.search_response = httpx2.ConnectError("boom")
    result = await fetch_synced_lyrics(title="Song")
    assert result is None


async def test_malformed_json_returns_none() -> None:
    _FakeAsyncClient.get_response = _FakeResponse(200, raise_json_error=True)
    _FakeAsyncClient.search_response = _FakeResponse(200, [])
    result = await fetch_synced_lyrics(title="Song")
    assert result is None


async def test_duration_and_album_passed_through_without_error() -> None:
    _FakeAsyncClient.get_response = _FakeResponse(
        200, {"syncedLyrics": "[00:01.00]Hi"}
    )
    result = await fetch_synced_lyrics(
        title="Song", artist="Artist", album="Album", duration=123.7
    )
    assert result == "[00:01.00]Hi"
