import asyncio
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from httpx import AsyncClient

import app.tracks as tracks_module
from app import stems
from app.database import get_db
from tests.conftest import WsTestClient

VALID_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


async def _fake_fetch_synced_lyrics_none(**kwargs):
    return None


async def _create_session(async_client: AsyncClient, name: str = "s") -> dict:
    resp = await async_client.post("/sessions", json={"name": name, "display_name": "Host"})
    assert resp.status_code == 201
    return resp.json()


async def _join_session(
    async_client: AsyncClient, session: dict, client_id: str, display_name: str = "Guest"
) -> dict:
    resp = await async_client.post(
        f"/sessions/{session['id']}/join",
        json={"passcode": session["passcode"], "display_name": display_name, "client_id": client_id},
    )
    assert resp.status_code == 200
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


def _fake_download_factory(*, with_captions: bool, fail: bool = False):
    """Build a fake `run_yt_dlp_sync` replacement that writes canned files
    instead of touching the network."""

    def _fake_run_yt_dlp_sync(url: str, dest_dir: Path):
        from app.youtube import DownloadResult

        if fail:
            raise RuntimeError("simulated failure")

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


def _fake_run_demucs_sync_factory(*, fail: bool = False):
    """Build a fake `run_demucs_sync` replacement that writes canned stem
    files instead of running real model inference."""

    def _fake_run_demucs_sync(audio_path: Path, dest_dir: Path, model: str):
        if fail:
            raise RuntimeError("simulated failure")

        stem_dir = dest_dir / model / audio_path.stem
        stem_dir.mkdir(parents=True, exist_ok=True)
        vocals_path = stem_dir / "vocals.wav"
        no_vocals_path = stem_dir / "no_vocals.wav"
        samples = np.array([[0.1, 0.1], [0.2, 0.2]], dtype=np.float32)
        sf.write(str(vocals_path), samples, 44100, subtype="FLOAT")
        sf.write(str(no_vocals_path), samples, 44100, subtype="FLOAT")
        return stems.SeparationResult(vocals_path=vocals_path, no_vocals_path=no_vocals_path)

    return _fake_run_demucs_sync


async def test_post_invalid_url_returns_422(async_client: AsyncClient) -> None:
    session = await _create_session(async_client)
    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": "https://example.com/not-youtube", "client_id": "c1"},
    )
    assert resp.status_code == 422

    db = await get_db()
    async with db.execute("SELECT COUNT(*) FROM tracks") as cursor:
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 0


async def test_post_with_non_member_client_id_returns_403(async_client: AsyncClient) -> None:
    session = await _create_session(async_client)
    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": VALID_URL, "client_id": "not-a-member"},
    )
    assert resp.status_code == 403

    db = await get_db()
    async with db.execute("SELECT COUNT(*) FROM tracks") as cursor:
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 0


async def test_post_to_nonexistent_session_returns_404(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/sessions/nonexistent/tracks",
        json={"url": VALID_URL, "client_id": "c1"},
    )
    assert resp.status_code == 404


async def test_post_valid_url_downloads_successfully(async_client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=True)
    )
    monkeypatch.setattr(tracks_module, "run_demucs_sync", _fake_run_demucs_sync_factory())
    session = await _create_session(async_client)

    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": VALID_URL, "client_id": session["client_id"]},
    )
    assert resp.status_code == 202
    created = resp.json()
    assert created["status"] == "pending"
    assert created["youtube_video_id"] == "dQw4w9WgXcQ"

    track = await _wait_for_status(async_client, session["id"], {"ready", "error"})
    assert track["status"] == "ready"
    assert track["audio_path"]
    assert track["audio_path"].endswith("mixed.wav")
    assert track["title"] == "Fake Title"
    assert track["lyrics_source"] == "captions"
    assert track["lyrics_path"]


async def test_no_captions_reaches_ready_with_no_lyrics(
    async_client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    monkeypatch.setattr(tracks_module, "run_demucs_sync", _fake_run_demucs_sync_factory())
    monkeypatch.setattr(tracks_module, "fetch_synced_lyrics", _fake_fetch_synced_lyrics_none)
    session = await _create_session(async_client)

    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": VALID_URL, "client_id": session["client_id"]},
    )
    assert resp.status_code == 202

    track = await _wait_for_status(async_client, session["id"], {"ready", "error"})
    assert track["status"] == "ready"
    assert track["audio_path"].endswith("mixed.wav")
    assert track["lyrics_source"] == "none"
    assert track["lyrics_path"] is None


async def test_no_captions_falls_back_to_lrclib(
    async_client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    monkeypatch.setattr(tracks_module, "run_demucs_sync", _fake_run_demucs_sync_factory())

    canned_lrc = "[00:01.00]Fallback lyrics"

    async def _fake_fetch_synced_lyrics(**kwargs):
        return canned_lrc

    monkeypatch.setattr(tracks_module, "fetch_synced_lyrics", _fake_fetch_synced_lyrics)
    session = await _create_session(async_client)

    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": VALID_URL, "client_id": session["client_id"]},
    )
    assert resp.status_code == 202

    track = await _wait_for_status(async_client, session["id"], {"ready", "error"})
    assert track["status"] == "ready"
    assert track["audio_path"].endswith("mixed.wav")
    assert track["lyrics_source"] == "lrclib"
    assert track["lyrics_path"]
    assert Path(track["lyrics_path"]).read_text() == canned_lrc


async def test_duplicate_submission_returns_409(async_client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    monkeypatch.setattr(tracks_module, "run_demucs_sync", _fake_run_demucs_sync_factory())
    monkeypatch.setattr(tracks_module, "fetch_synced_lyrics", _fake_fetch_synced_lyrics_none)
    session = await _create_session(async_client)
    await _join_session(async_client, session, "c2")

    first = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": VALID_URL, "client_id": session["client_id"]},
    )
    assert first.status_code == 202

    second = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": VALID_URL, "client_id": "c2"},
    )
    assert second.status_code == 409
    assert second.json()["youtube_video_id"] == "dQw4w9WgXcQ"


async def test_download_failure_marks_error_and_cleans_up_dir(
    async_client: AsyncClient, monkeypatch, tmp_path
) -> None:
    from app import config

    monkeypatch.setattr(config.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(tracks_module.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False, fail=True))
    monkeypatch.setattr(tracks_module, "run_demucs_sync", _fake_run_demucs_sync_factory())

    session = await _create_session(async_client)
    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": VALID_URL, "client_id": session["client_id"]},
    )
    assert resp.status_code == 202
    track_id = resp.json()["id"]

    track = await _wait_for_status(async_client, session["id"], {"ready", "error"})
    assert track["status"] == "error"
    assert track["error_message"]

    dest_dir = tmp_path / "tracks" / track_id
    assert not dest_dir.exists()


async def test_stemming_failure_marks_error_and_cleans_up_dir(
    async_client: AsyncClient, monkeypatch, tmp_path
) -> None:
    from app import config

    monkeypatch.setattr(config.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(tracks_module.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    monkeypatch.setattr(
        tracks_module, "run_demucs_sync", _fake_run_demucs_sync_factory(fail=True)
    )
    monkeypatch.setattr(tracks_module, "fetch_synced_lyrics", _fake_fetch_synced_lyrics_none)

    session = await _create_session(async_client)
    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": VALID_URL, "client_id": session["client_id"]},
    )
    assert resp.status_code == 202
    track_id = resp.json()["id"]

    track = await _wait_for_status(async_client, session["id"], {"ready", "error"})
    assert track["status"] == "error"
    assert track["error_message"]

    dest_dir = tmp_path / "tracks" / track_id
    assert not dest_dir.exists()


async def test_get_tracks_for_nonexistent_session_returns_404(async_client: AsyncClient) -> None:
    resp = await async_client.get("/sessions/nonexistent/tracks")
    assert resp.status_code == 404


def test_websocket_broadcasts_track_added_and_updated(client: WsTestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    monkeypatch.setattr(tracks_module, "run_demucs_sync", _fake_run_demucs_sync_factory())
    monkeypatch.setattr(tracks_module, "fetch_synced_lyrics", _fake_fetch_synced_lyrics_none)

    session_resp = client.post("/sessions", json={"name": "ws-tracks", "display_name": "Host"})
    assert session_resp.status_code == 201
    session = session_resp.json()
    session_id, client_id = session["id"], session["client_id"]

    with client.websocket_connect(f"/ws/{session_id}?client_id={client_id}") as ws:
        # drain this connection's own member_joined event
        ws.receive_text()

        resp = client.post(
            f"/sessions/{session_id}/tracks",
            json={"url": VALID_URL, "client_id": client_id},
        )
        assert resp.status_code == 202

        added = json.loads(ws.receive_text())
        assert added["type"] == "track_added"
        assert added["data"]["status"] == "pending"
        assert added["data"]["youtube_video_id"] == "dQw4w9WgXcQ"

        seen_statuses = []
        # Read updates until we see the terminal status, guarding against an
        # infinite loop if something regresses.
        for _ in range(10):
            msg = json.loads(ws.receive_text())
            assert msg["type"] == "track_updated"
            seen_statuses.append(msg["data"]["status"])
            if msg["data"]["status"] in ("ready", "error"):
                break

        assert "downloading" in seen_statuses
        assert "fetching_lyrics" in seen_statuses
        assert "stemming" in seen_statuses
        assert seen_statuses[-1] == "ready"
