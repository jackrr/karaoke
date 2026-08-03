import json
import time
from uuid import uuid4

from httpx import AsyncClient

import app.tracks as tracks_module
from app.database import get_db
from tests.conftest import WsTestClient
from tests.test_tracks import (
    _create_session,
    _fake_fetch_synced_lyrics_none,
    _fake_run_demucs_sync_factory,
    _wait_for_status,
)
from tests.test_track_remove import _add_track


async def _insert_pending_track(session_id: str, client_id: str) -> str:
    """Insert a `pending` track row directly, bypassing the background
    download pipeline entirely, so it's guaranteed to stay non-`ready`."""
    db = await get_db()
    track_id = str(uuid4())
    await db.execute(
        "INSERT INTO tracks (id, session_id, source_url, youtube_video_id, "
        "status, requested_by_client_id, position) "
        "VALUES (?, ?, 'https://example.com', 'testvid', 'pending', ?, 0)",
        (track_id, session_id, client_id),
    )
    await db.commit()
    return track_id


def _patch_pipeline(monkeypatch) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    monkeypatch.setattr(tracks_module, "run_demucs_sync", _fake_run_demucs_sync_factory())
    monkeypatch.setattr(tracks_module, "fetch_synced_lyrics", _fake_fetch_synced_lyrics_none)


async def _ready_track(async_client: AsyncClient, session: dict) -> dict:
    await _add_track(async_client, session, session["client_id"])
    return await _wait_for_status(async_client, session["id"], {"ready"})


async def test_host_updates_playback_state(async_client: AsyncClient, monkeypatch) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)
    track = await _ready_track(async_client, session)

    resp = await async_client.post(
        f"/sessions/{session['id']}/playback",
        json={"client_id": session["client_id"], "track_id": track["id"], "is_playing": True},
    )
    assert resp.status_code == 200
    assert resp.json() == {"track_id": track["id"], "is_playing": True}

    get_resp = await async_client.get(f"/sessions/{session['id']}")
    data = get_resp.json()
    assert data["now_playing_track_id"] == track["id"]
    assert data["is_playing"] is True


async def test_non_host_playback_update_is_forbidden(async_client: AsyncClient, monkeypatch) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)
    track = await _ready_track(async_client, session)

    guest_resp = await async_client.post(
        "/sessions/join",
        json={"code": session["code"], "display_name": "Guest"},
    )
    guest_client_id = guest_resp.json()["client_id"]

    resp = await async_client.post(
        f"/sessions/{session['id']}/playback",
        json={"client_id": guest_client_id, "track_id": track["id"], "is_playing": True},
    )
    assert resp.status_code == 403

    get_resp = await async_client.get(f"/sessions/{session['id']}")
    assert get_resp.json()["now_playing_track_id"] is None


async def test_playback_update_unknown_track_404(async_client: AsyncClient) -> None:
    session = await _create_session(async_client)

    resp = await async_client.post(
        f"/sessions/{session['id']}/playback",
        json={"client_id": session["client_id"], "track_id": "nonexistent", "is_playing": True},
    )
    assert resp.status_code == 404


async def test_playback_update_non_ready_track_409(async_client: AsyncClient) -> None:
    session = await _create_session(async_client)
    track_id = await _insert_pending_track(session["id"], session["client_id"])

    resp = await async_client.post(
        f"/sessions/{session['id']}/playback",
        json={"client_id": session["client_id"], "track_id": track_id, "is_playing": True},
    )
    assert resp.status_code == 409


async def test_playback_update_unknown_session_404(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/sessions/nonexistent/playback",
        json={"client_id": "c1", "track_id": "t1", "is_playing": True},
    )
    assert resp.status_code == 404


async def test_playback_request_from_non_host_broadcasts_without_db_write(
    async_client: AsyncClient, monkeypatch
) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)
    track = await _ready_track(async_client, session)

    guest_resp = await async_client.post(
        "/sessions/join",
        json={"code": session["code"], "display_name": "Guest"},
    )
    guest_client_id = guest_resp.json()["client_id"]

    resp = await async_client.post(
        f"/sessions/{session['id']}/playback/request",
        json={"client_id": guest_client_id, "track_id": track["id"]},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "track_id": track["id"],
        "requested_by_client_id": guest_client_id,
    }

    get_resp = await async_client.get(f"/sessions/{session['id']}")
    data = get_resp.json()
    assert data["now_playing_track_id"] is None
    assert data["is_playing"] is False


async def test_playback_request_from_non_member_rejected(
    async_client: AsyncClient, monkeypatch
) -> None:
    _patch_pipeline(monkeypatch)
    session = await _create_session(async_client)
    track = await _ready_track(async_client, session)

    resp = await async_client.post(
        f"/sessions/{session['id']}/playback/request",
        json={"client_id": "not-a-member", "track_id": track["id"]},
    )
    assert resp.status_code == 403


async def test_playback_request_unknown_track_404(async_client: AsyncClient) -> None:
    session = await _create_session(async_client)

    resp = await async_client.post(
        f"/sessions/{session['id']}/playback/request",
        json={"client_id": session["client_id"], "track_id": "nonexistent"},
    )
    assert resp.status_code == 404


def _wait_for_ready_sync(client: WsTestClient, session_id: str, timeout: float = 2.0) -> str:
    """Poll GET tracks (sync client) until the single track reaches 'ready',
    returning its id."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"/sessions/{session_id}/tracks")
        tracks = resp.json()["tracks"]
        if tracks and tracks[0]["status"] == "ready":
            return tracks[0]["id"]
        time.sleep(0.01)
    raise AssertionError("track never reached ready")


def test_websocket_broadcasts_playback_state_changed(client: WsTestClient, monkeypatch) -> None:
    _patch_pipeline(monkeypatch)

    session_resp = client.post("/sessions", json={"display_name": "Host"})
    session = session_resp.json()
    session_id, host_client_id = session["id"], session["client_id"]

    join_resp = client.post(
        "/sessions/join",
        json={"code": session["code"], "display_name": "Guest", "client_id": "guest-1"},
    )
    assert join_resp.status_code == 200

    client.post(
        f"/sessions/{session_id}/tracks",
        json={"url": "https://www.youtube.com/watch?v=aaaaaaaaaaa", "client_id": host_client_id},
    )
    track_id = _wait_for_ready_sync(client, session_id)

    with client.websocket_connect(f"/ws/{session_id}?client_id=guest-1") as ws:
        ws.receive_text()  # drain member_joined

        resp = client.post(
            f"/sessions/{session_id}/playback",
            json={"client_id": host_client_id, "track_id": track_id, "is_playing": True},
        )
        assert resp.status_code == 200

        msg = json.loads(ws.receive_text())
        assert msg["type"] == "playback_state_changed"
        assert msg["data"] == {"track_id": track_id, "is_playing": True}


def test_websocket_broadcasts_play_requested(client: WsTestClient, monkeypatch) -> None:
    _patch_pipeline(monkeypatch)

    session_resp = client.post("/sessions", json={"display_name": "Host"})
    session = session_resp.json()
    session_id, host_client_id = session["id"], session["client_id"]

    join_resp = client.post(
        "/sessions/join",
        json={"code": session["code"], "display_name": "Guest", "client_id": "guest-1"},
    )
    assert join_resp.status_code == 200

    track_resp = client.post(
        f"/sessions/{session_id}/tracks",
        json={"url": "https://www.youtube.com/watch?v=aaaaaaaaaaa", "client_id": host_client_id},
    )
    track_id = track_resp.json()["id"]

    with client.websocket_connect(f"/ws/{session_id}?client_id={host_client_id}") as host_ws:
        host_ws.receive_text()  # drain host's own member_joined

        with client.websocket_connect(f"/ws/{session_id}?client_id=guest-1") as guest_ws:
            guest_ws.receive_text()  # drain guest's own member_joined
            host_ws.receive_text()  # drain host seeing guest's member_joined

            resp = client.post(
                f"/sessions/{session_id}/playback/request",
                json={"client_id": "guest-1", "track_id": track_id},
            )
            assert resp.status_code == 200

            msg = json.loads(host_ws.receive_text())
            assert msg["type"] == "play_requested"
            assert msg["data"] == {"track_id": track_id, "requested_by_client_id": "guest-1"}
