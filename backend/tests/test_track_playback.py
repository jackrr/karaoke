import asyncio
from pathlib import Path

from httpx import AsyncClient

import app.tracks as tracks_module

VALID_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


async def _create_session(async_client: AsyncClient, name: str = "s") -> dict:
    resp = await async_client.post("/sessions", json={"name": name, "display_name": "Host"})
    assert resp.status_code == 201
    return resp.json()


async def _wait_for_status(async_client: AsyncClient, session_id: str, statuses: set[str], timeout: float = 2.0) -> dict:
    """Poll GET tracks until the single track reaches one of `statuses`."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        resp = await async_client.get(f"/sessions/{session_id}/tracks")
        assert resp.status_code == 200
        tracks = resp.json()["tracks"]
        if tracks and tracks[0]["status"] in statuses:
            return tracks[0]
        await asyncio.sleep(0.01)
    raise AssertionError(f"track never reached {statuses}")


def _fake_download_factory(*, with_captions: bool):
    """Build a fake `run_yt_dlp_sync` replacement that writes canned files
    instead of touching the network."""

    def _fake_run_yt_dlp_sync(url: str, dest_dir: Path):
        from app.youtube import DownloadResult

        dest_dir.mkdir(parents=True, exist_ok=True)
        audio_path = dest_dir / "audio.m4a"
        audio_path.write_bytes(b"fake audio")
        vtt_path = None
        if with_captions:
            vtt_path = dest_dir / "video.en.vtt"
            vtt_path.write_text(
                "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello\n"
            )
        return DownloadResult(
            audio_path=audio_path,
            title="Fake Title",
            duration_seconds=42.0,
            vtt_path=vtt_path,
        )

    return _fake_run_yt_dlp_sync


async def _create_downloaded_track(
    async_client: AsyncClient, monkeypatch, *, with_captions: bool = False
) -> tuple[dict, dict]:
    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=with_captions)
    )
    session = await _create_session(async_client)
    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": VALID_URL, "client_id": session["client_id"]},
    )
    assert resp.status_code == 202
    track = await _wait_for_status(async_client, session["id"], {"downloaded", "error"})
    assert track["status"] == "downloaded"
    return session, track


async def test_audio_stream_returns_200_with_correct_bytes(
    async_client: AsyncClient, monkeypatch
) -> None:
    session, track = await _create_downloaded_track(async_client, monkeypatch)
    resp = await async_client.get(
        f"/sessions/{session['id']}/tracks/{track['id']}/audio"
    )
    assert resp.status_code == 200
    assert resp.content == b"fake audio"


async def test_audio_stream_honors_range_requests(
    async_client: AsyncClient, monkeypatch
) -> None:
    session, track = await _create_downloaded_track(async_client, monkeypatch)
    resp = await async_client.get(
        f"/sessions/{session['id']}/tracks/{track['id']}/audio",
        headers={"Range": "bytes=2-4"},
    )
    assert resp.status_code == 206
    assert resp.headers["content-range"] == "bytes 2-4/10"
    assert resp.content == b"fake audio"[2:5]


async def test_audio_stream_404_when_session_does_not_exist(
    async_client: AsyncClient, monkeypatch
) -> None:
    _, track = await _create_downloaded_track(async_client, monkeypatch)
    resp = await async_client.get(
        f"/sessions/nonexistent/tracks/{track['id']}/audio"
    )
    assert resp.status_code == 404


async def test_audio_stream_404_when_track_belongs_to_different_session(
    async_client: AsyncClient, monkeypatch
) -> None:
    _, track = await _create_downloaded_track(async_client, monkeypatch)
    other_session = await _create_session(async_client, name="other")
    resp = await async_client.get(
        f"/sessions/{other_session['id']}/tracks/{track['id']}/audio"
    )
    assert resp.status_code == 404


async def test_audio_stream_409_when_track_not_downloaded_yet(
    async_client: AsyncClient, monkeypatch
) -> None:
    def _hang_briefly(url: str, dest_dir: Path):
        import time

        time.sleep(1)

    monkeypatch.setattr(tracks_module, "run_yt_dlp_sync", _hang_briefly)
    session = await _create_session(async_client)
    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": VALID_URL, "client_id": session["client_id"]},
    )
    assert resp.status_code == 202
    track_id = resp.json()["id"]

    audio_resp = await async_client.get(
        f"/sessions/{session['id']}/tracks/{track_id}/audio"
    )
    assert audio_resp.status_code == 409


async def test_audio_stream_404_when_file_deleted_after_download(
    async_client: AsyncClient, monkeypatch
) -> None:
    session, track = await _create_downloaded_track(async_client, monkeypatch)
    Path(track["audio_path"]).unlink()
    resp = await async_client.get(
        f"/sessions/{session['id']}/tracks/{track['id']}/audio"
    )
    assert resp.status_code == 404


async def test_lyrics_endpoint_returns_lrc_text(
    async_client: AsyncClient, monkeypatch
) -> None:
    session, track = await _create_downloaded_track(
        async_client, monkeypatch, with_captions=True
    )
    resp = await async_client.get(
        f"/sessions/{session['id']}/tracks/{track['id']}/lyrics"
    )
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "Hello" in resp.text


async def test_lyrics_endpoint_404_when_no_lyrics(
    async_client: AsyncClient, monkeypatch
) -> None:
    session, track = await _create_downloaded_track(
        async_client, monkeypatch, with_captions=False
    )
    assert track["lyrics_source"] == "none"
    resp = await async_client.get(
        f"/sessions/{session['id']}/tracks/{track['id']}/lyrics"
    )
    assert resp.status_code == 404


async def test_lyrics_endpoint_409_when_track_not_downloaded_yet(
    async_client: AsyncClient, monkeypatch
) -> None:
    def _hang_briefly(url: str, dest_dir: Path):
        import time

        time.sleep(1)

    monkeypatch.setattr(tracks_module, "run_yt_dlp_sync", _hang_briefly)
    session = await _create_session(async_client)
    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": VALID_URL, "client_id": session["client_id"]},
    )
    assert resp.status_code == 202
    track_id = resp.json()["id"]

    lyrics_resp = await async_client.get(
        f"/sessions/{session['id']}/tracks/{track_id}/lyrics"
    )
    assert lyrics_resp.status_code == 409
