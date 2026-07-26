import asyncio
import json
import threading
from pathlib import Path
from uuid import uuid4

from httpx import AsyncClient

import app.tracks as tracks_module
from app.config import settings
from app.database import get_db, touch_session
from app.reaper import _touch_active_connections, reap_expired_sessions
from app.websocket_manager import manager
from tests.conftest import WsTestClient
from tests.test_tracks import (
    VALID_URL,
    _create_session,
    _fake_fetch_synced_lyrics_none,
    _fake_run_demucs_sync_factory,
    _join_session,
)


def _patch_pipeline(monkeypatch) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    monkeypatch.setattr(tracks_module, "run_demucs_sync", _fake_run_demucs_sync_factory())
    monkeypatch.setattr(tracks_module, "fetch_synced_lyrics", _fake_fetch_synced_lyrics_none)


async def _add_track(async_client: AsyncClient, session: dict, client_id: str, url: str = VALID_URL) -> dict:
    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": url, "client_id": client_id},
    )
    assert resp.status_code == 202
    return resp.json()


async def _backdate_session(session_id: str, seconds_ago: float) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE sessions SET last_active_at = datetime('now', ?) WHERE id = ?",
        (f"-{seconds_ago} seconds", session_id),
    )
    await db.commit()


async def _get_last_active_at(session_id: str) -> str:
    db = await get_db()
    async with db.execute(
        "SELECT last_active_at FROM sessions WHERE id = ?", (session_id,)
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    return row[0]


async def test_reap_deletes_session_tracks_and_members(
    async_client: AsyncClient, monkeypatch
) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)
    await _join_session(async_client, session, "guest-1")
    track = await _add_track(async_client, session, session["client_id"])

    await _backdate_session(session["id"], seconds_ago=1000)

    reaped = await reap_expired_sessions(settings.storage_dir, ttl_seconds=100)
    assert reaped == 1

    db = await get_db()
    async with db.execute(
        "SELECT 1 FROM sessions WHERE id = ?", (session["id"],)
    ) as cursor:
        assert await cursor.fetchone() is None
    async with db.execute(
        "SELECT 1 FROM tracks WHERE id = ?", (track["id"],)
    ) as cursor:
        assert await cursor.fetchone() is None
    async with db.execute(
        "SELECT 1 FROM session_members WHERE session_id = ?", (session["id"],)
    ) as cursor:
        assert await cursor.fetchone() is None


async def test_reap_deletes_track_storage_directory(
    async_client: AsyncClient, monkeypatch
) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)
    track = await _add_track(async_client, session, session["client_id"])

    track_dir = Path(settings.storage_dir) / "tracks" / track["id"]
    track_dir.mkdir(parents=True, exist_ok=True)
    (track_dir / "audio.m4a").write_bytes(b"fake audio")
    assert track_dir.exists()

    await _backdate_session(session["id"], seconds_ago=1000)
    reaped = await reap_expired_sessions(settings.storage_dir, ttl_seconds=100)
    assert reaped == 1
    assert not track_dir.exists()


async def test_recent_session_not_reaped(async_client: AsyncClient, monkeypatch) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)

    reaped = await reap_expired_sessions(settings.storage_dir, ttl_seconds=100)
    assert reaped == 0

    db = await get_db()
    async with db.execute(
        "SELECT 1 FROM sessions WHERE id = ?", (session["id"],)
    ) as cursor:
        assert await cursor.fetchone() is not None


async def test_touch_active_connections_refreshes_connected_sessions(
    async_client: AsyncClient,
) -> None:
    session = await _create_session(async_client)
    await _backdate_session(session["id"], seconds_ago=1000)
    before = await _get_last_active_at(session["id"])

    # Simulate a live websocket connection for this session without actually
    # opening a socket, by registering directly in the connection manager's
    # bookkeeping — the sweep-touch step only consults `manager.active`.
    manager.active.setdefault(session["id"], {}).setdefault(session["client_id"], set()).add(
        object()  # ty: ignore[invalid-argument-type] — stand-in socket, only .keys() is read
    )
    try:
        db = await get_db()
        await _touch_active_connections(db)
    finally:
        manager.active.pop(session["id"], None)

    after = await _get_last_active_at(session["id"])
    assert after > before


def test_websocket_connect_touches_session(client: WsTestClient) -> None:
    session_resp = client.post("/sessions", json={"display_name": "Host"})
    assert session_resp.status_code == 201
    session = session_resp.json()

    import asyncio

    asyncio.run(_backdate_session(session["id"], seconds_ago=1000))
    before = asyncio.run(_get_last_active_at(session["id"]))

    with client.websocket_connect(f"/ws/{session['id']}?client_id={session['client_id']}") as ws:
        ws.receive_text()  # drain member_joined

    after = asyncio.run(_get_last_active_at(session["id"]))
    assert after > before


async def test_touch_session_advances_last_active_at(async_client: AsyncClient) -> None:
    session = await _create_session(async_client)
    await _backdate_session(session["id"], seconds_ago=1000)
    before = await _get_last_active_at(session["id"])

    db = await get_db()
    await touch_session(db, session["id"])
    await db.commit()

    after = await _get_last_active_at(session["id"])
    assert after > before


async def test_track_add_reorder_remove_touch_session(
    async_client: AsyncClient, monkeypatch
) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)

    await _backdate_session(session["id"], seconds_ago=1000)
    before_add = await _get_last_active_at(session["id"])
    track1 = await _add_track(
        async_client, session, session["client_id"], "https://www.youtube.com/watch?v=aaaaaaaaaaa"
    )
    after_add = await _get_last_active_at(session["id"])
    assert after_add > before_add

    track2 = await _add_track(
        async_client, session, session["client_id"], "https://www.youtube.com/watch?v=bbbbbbbbbbb"
    )

    await _backdate_session(session["id"], seconds_ago=1000)
    before_reorder = await _get_last_active_at(session["id"])
    resp = await async_client.put(
        f"/sessions/{session['id']}/tracks/order",
        json={"client_id": session["client_id"], "track_ids": [track2["id"], track1["id"]]},
    )
    assert resp.status_code == 200
    after_reorder = await _get_last_active_at(session["id"])
    assert after_reorder > before_reorder

    await _backdate_session(session["id"], seconds_ago=1000)
    before_remove = await _get_last_active_at(session["id"])
    resp = await async_client.delete(
        f"/sessions/{session['id']}/tracks/{track1['id']}",
        params={"client_id": session["client_id"]},
    )
    assert resp.status_code == 200
    after_remove = await _get_last_active_at(session["id"])
    assert after_remove > before_remove


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


async def test_reap_mid_flight_download_leaves_no_orphaned_files(
    async_client: AsyncClient, monkeypatch, tmp_path
) -> None:
    """Reproduces the storage-leak race from the session-reaper side: the
    owning session gets reaped while a track's background download pipeline
    is still blocked mid-download. Once the pipeline resumes, it must notice
    its DB row is gone (deleted along with the reaped session) and clean up
    whatever it wrote, instead of leaking an orphaned directory."""
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
        await asyncio.to_thread(reached_downloading.wait, 5)

        await _backdate_session(session["id"], seconds_ago=1000)
        reaped = await reap_expired_sessions(str(tmp_path), ttl_seconds=100)
        assert reaped == 1

        resume.set()
        await asyncio.wait_for(task, timeout=5)
    finally:
        if not task.done():
            task.cancel()

    track_dir = tmp_path / "tracks" / track_id
    assert not track_dir.exists()


def test_reap_sends_session_ended_and_closes_connection(client: WsTestClient) -> None:
    """A session with a still-live websocket connection at reap time must
    have that connection told (via a `session_ended` broadcast) and closed
    cleanly, rather than being silently dropped once the session's rows
    disappear underneath it."""
    session_resp = client.post("/sessions", json={"display_name": "Host"})
    assert session_resp.status_code == 201
    session = session_resp.json()
    session_id, client_id = session["id"], session["client_id"]

    with client.websocket_connect(f"/ws/{session_id}?client_id={client_id}") as ws:
        ws.receive_text()  # drain this connection's own member_joined event

        asyncio.run(_backdate_session(session_id, seconds_ago=1000))
        assert session_id in manager.active

        reaped = asyncio.run(reap_expired_sessions(settings.storage_dir, ttl_seconds=100))
        assert reaped == 1

        msg = json.loads(ws.receive_text())
        assert msg["type"] == "session_ended"

        # The connection manager should have dropped all bookkeeping for the
        # reaped session ...
        assert session_id not in manager.active
        # ... and the socket itself should have actually been closed rather
        # than merely forgotten: the client-side receive should now observe
        # a close instead of hanging or yielding further application data.
        import pytest
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_reap_deletes_db_rows_before_closing_so_reconnect_is_rejected(
    client: WsTestClient, monkeypatch
) -> None:
    """Regression test for the reconnect race: `reap_expired_sessions` must
    delete the session's DB rows (session_members, tracks, sessions) and
    commit BEFORE calling `manager.close_session`, not after. Otherwise a
    reconnect that lands in the window while `close_session` is still
    broadcasting/closing sockets (an await point) could pass the
    `_is_active_member` check — since the session_members row would still
    exist — get re-added to `manager.active`, and never receive
    `session_ended`, leaving an orphaned connection with no cleanup path
    (the session_id is about to vanish from `sessions`, so no future sweep
    will find it again).

    This simulates that race directly: it patches `manager.close_session`
    to attempt a reconnect (as the same client_id, i.e. the same browser
    reconnecting) partway through the reap, and asserts the reconnect is
    rejected — which only happens if the DB deletes already landed by the
    time `close_session` runs.
    """
    from starlette.websockets import WebSocketDisconnect

    session_resp = client.post("/sessions", json={"display_name": "Host"})
    assert session_resp.status_code == 201
    session = session_resp.json()
    session_id, client_id = session["id"], session["client_id"]

    with client.websocket_connect(f"/ws/{session_id}?client_id={client_id}") as ws:
        ws.receive_text()  # drain member_joined

        asyncio.run(_backdate_session(session_id, seconds_ago=1000))

        original_close_session = manager.close_session
        outcome: dict[str, bool] = {}

        async def _close_session_racing_a_reconnect(*args, **kwargs):
            # Simulate a reconnect landing in the window between the DB
            # deletes finishing (which must have already happened, since
            # this patch stands in for close_session, called last) and the
            # graceful close actually completing.
            try:
                with client.websocket_connect(
                    f"/ws/{session_id}?client_id={client_id}"
                ):
                    outcome["reconnect_accepted"] = True
            except WebSocketDisconnect:
                outcome["reconnect_accepted"] = False
            return await original_close_session(*args, **kwargs)

        monkeypatch.setattr(manager, "close_session", _close_session_racing_a_reconnect)

        reaped = asyncio.run(reap_expired_sessions(settings.storage_dir, ttl_seconds=100))
        assert reaped == 1

        # The racing reconnect must have been rejected — proof that the
        # session_members/sessions rows were already gone by the time
        # close_session (and thus the reconnect attempt) ran.
        assert outcome["reconnect_accepted"] is False

        # And no orphaned entry should be left in manager.active for this
        # session as a result of the race.
        assert session_id not in manager.active

        msg = json.loads(ws.receive_text())
        assert msg["type"] == "session_ended"


async def test_member_join_and_leave_touch_session(async_client: AsyncClient) -> None:
    session = await _create_session(async_client)

    await _backdate_session(session["id"], seconds_ago=1000)
    before_join = await _get_last_active_at(session["id"])
    await _join_session(async_client, session, "guest-1")
    after_join = await _get_last_active_at(session["id"])
    assert after_join > before_join

    await _backdate_session(session["id"], seconds_ago=1000)
    before_leave = await _get_last_active_at(session["id"])
    resp = await async_client.post(
        f"/sessions/{session['id']}/leave", json={"client_id": "guest-1"}
    )
    assert resp.status_code in (200, 204)
    after_leave = await _get_last_active_at(session["id"])
    assert after_leave > before_leave
