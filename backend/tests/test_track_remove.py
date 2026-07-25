import asyncio
import json
import threading
from pathlib import Path
from uuid import uuid4

from httpx import AsyncClient

import app.tracks as tracks_module
from app.config import settings
from app.database import get_db
from tests.conftest import WsTestClient
from tests.test_tracks import (
    VALID_URL,
    _create_session,
    _fake_fetch_synced_lyrics_none,
    _fake_run_demucs_sync_factory,
)


async def _add_track(async_client: AsyncClient, session: dict, client_id: str, url: str = VALID_URL) -> dict:
    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": url, "client_id": client_id},
    )
    assert resp.status_code == 202
    return resp.json()


def _patch_pipeline(monkeypatch) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    monkeypatch.setattr(tracks_module, "run_demucs_sync", _fake_run_demucs_sync_factory())
    monkeypatch.setattr(tracks_module, "fetch_synced_lyrics", _fake_fetch_synced_lyrics_none)


async def test_remove_deletes_row_and_reorders_remaining(
    async_client: AsyncClient, monkeypatch
) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)

    urls = [
        "https://www.youtube.com/watch?v=aaaaaaaaaaa",
        "https://www.youtube.com/watch?v=bbbbbbbbbbb",
        "https://www.youtube.com/watch?v=ccccccccccc",
    ]
    created_ids = []
    for url in urls:
        track = await _add_track(async_client, session, session["client_id"], url)
        created_ids.append(track["id"])

    resp = await async_client.delete(
        f"/sessions/{session['id']}/tracks/{created_ids[1]}",
        params={"client_id": session["client_id"]},
    )
    assert resp.status_code == 200
    remaining_ids = [t["id"] for t in resp.json()["tracks"]]
    assert remaining_ids == [created_ids[0], created_ids[2]]

    get_resp = await async_client.get(f"/sessions/{session['id']}/tracks")
    assert [t["id"] for t in get_resp.json()["tracks"]] == [created_ids[0], created_ids[2]]


async def test_remove_rejects_non_active_member(async_client: AsyncClient, monkeypatch) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)
    track = await _add_track(async_client, session, session["client_id"])

    resp = await async_client.delete(
        f"/sessions/{session['id']}/tracks/{track['id']}",
        params={"client_id": "not-a-member"},
    )
    assert resp.status_code == 403

    get_resp = await async_client.get(f"/sessions/{session['id']}/tracks")
    assert [t["id"] for t in get_resp.json()["tracks"]] == [track["id"]]


async def test_remove_nonexistent_track_returns_404(async_client: AsyncClient, monkeypatch) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)

    resp = await async_client.delete(
        f"/sessions/{session['id']}/tracks/nonexistent-track",
        params={"client_id": session["client_id"]},
    )
    assert resp.status_code == 404


async def test_remove_against_nonexistent_session_returns_404(async_client: AsyncClient) -> None:
    resp = await async_client.delete(
        "/sessions/nonexistent/tracks/some-track",
        params={"client_id": "c1"},
    )
    assert resp.status_code == 404


async def test_remove_deletes_storage_directory(async_client: AsyncClient, monkeypatch) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)
    track = await _add_track(async_client, session, session["client_id"])

    track_dir = Path(settings.storage_dir) / "tracks" / track["id"]
    track_dir.mkdir(parents=True, exist_ok=True)
    (track_dir / "audio.m4a").write_bytes(b"fake audio")
    assert track_dir.exists()

    resp = await async_client.delete(
        f"/sessions/{session['id']}/tracks/{track['id']}",
        params={"client_id": session["client_id"]},
    )
    assert resp.status_code == 200
    assert not track_dir.exists()


async def _insert_pending_track(session_id: str, client_id: str, url: str) -> str:
    """Insert a `pending` track row directly, bypassing the create-track
    endpoint, so the caller can drive `process_track_download` itself with
    full control over timing."""
    db = await get_db()
    track_id = str(uuid4())
    await db.execute(
        "INSERT INTO tracks (id, session_id, source_url, youtube_video_id, "
        "status, requested_by_client_id, position) "
        "VALUES (?, ?, ?, 'testvid', 'pending', ?, 0)",
        (track_id, session_id, url, client_id),
    )
    await db.commit()
    return track_id


async def test_remove_mid_flight_download_leaves_no_orphaned_files(
    async_client: AsyncClient, monkeypatch, tmp_path
) -> None:
    """Reproduces the storage-leak race: the track is removed while its
    background download pipeline is still in the middle of the (blocking)
    download step. Once the pipeline resumes and tries to advance past that
    step, it must notice its DB row is gone and clean up whatever it wrote,
    rather than leaving an orphaned directory nothing references."""
    from app import config

    monkeypatch.setattr(config.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(tracks_module.settings, "storage_dir", str(tmp_path))

    resume = threading.Event()
    reached_downloading = threading.Event()

    def _blocking_download(url, dest_dir, cookies_file=None):
        from app.youtube import DownloadResult

        reached_downloading.set()
        assert resume.wait(timeout=5), "test never signaled resume"
        dest_dir.mkdir(parents=True, exist_ok=True)
        audio_path = dest_dir / "audio.m4a"
        audio_path.write_bytes(b"fake audio")
        return DownloadResult(
            audio_path=audio_path, title="T", duration_seconds=1.0, vtt_path=None
        )

    monkeypatch.setattr(tracks_module, "run_yt_dlp_sync", _blocking_download)
    monkeypatch.setattr(tracks_module, "run_demucs_sync", _fake_run_demucs_sync_factory())
    monkeypatch.setattr(tracks_module, "fetch_synced_lyrics", _fake_fetch_synced_lyrics_none)

    session = await _create_session(async_client)
    track_id = await _insert_pending_track(session["id"], session["client_id"], VALID_URL)

    task = asyncio.create_task(
        tracks_module.process_track_download(
            track_id, session["id"], VALID_URL, str(tmp_path)
        )
    )
    try:
        # Wait until the pipeline is blocked inside the "download" step,
        # i.e. its "downloading" DB update has already landed.
        await asyncio.to_thread(reached_downloading.wait, 5)

        resp = await async_client.delete(
            f"/sessions/{session['id']}/tracks/{track_id}",
            params={"client_id": session["client_id"]},
        )
        assert resp.status_code == 200

        resume.set()
        await asyncio.wait_for(task, timeout=5)
    finally:
        if not task.done():
            task.cancel()

    track_dir = tmp_path / "tracks" / track_id
    assert not track_dir.exists()


def test_websocket_broadcasts_track_removed(client: WsTestClient, monkeypatch) -> None:
    _patch_pipeline(monkeypatch)

    session_resp = client.post("/sessions", json={"display_name": "Host"})
    assert session_resp.status_code == 201
    session = session_resp.json()
    session_id, client_id = session["id"], session["client_id"]

    join_resp = client.post(
        "/sessions/join",
        json={"code": session["code"], "display_name": "Guest", "client_id": "guest-1"},
    )
    assert join_resp.status_code == 200

    first = client.post(
        f"/sessions/{session_id}/tracks",
        json={"url": "https://www.youtube.com/watch?v=aaaaaaaaaaa", "client_id": client_id},
    )
    assert first.status_code == 202
    second = client.post(
        f"/sessions/{session_id}/tracks",
        json={"url": "https://www.youtube.com/watch?v=bbbbbbbbbbb", "client_id": client_id},
    )
    assert second.status_code == 202
    ids = [first.json()["id"], second.json()["id"]]

    with client.websocket_connect(f"/ws/{session_id}?client_id=guest-1") as ws:
        # drain this connection's own member_joined event
        ws.receive_text()

        resp = client.delete(
            f"/sessions/{session_id}/tracks/{ids[0]}",
            params={"client_id": client_id},
        )
        assert resp.status_code == 200

        msg = json.loads(ws.receive_text())
        assert msg["type"] == "track_removed"
        assert msg["data"]["track_id"] == ids[0]
        assert [t["id"] for t in msg["data"]["tracks"]] == [ids[1]]
