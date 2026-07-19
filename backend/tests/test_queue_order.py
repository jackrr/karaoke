import asyncio
import json

from httpx import AsyncClient

import app.tracks as tracks_module
from tests.conftest import WsTestClient
from tests.test_tracks import VALID_URL, _create_session, _join_session


async def _add_track(async_client: AsyncClient, session: dict, client_id: str, url: str = VALID_URL) -> dict:
    resp = await async_client.post(
        f"/sessions/{session['id']}/tracks",
        json={"url": url, "client_id": client_id},
    )
    assert resp.status_code == 202
    return resp.json()


async def test_tracks_listed_in_position_order(async_client: AsyncClient, monkeypatch) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
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

    resp = await async_client.get(f"/sessions/{session['id']}/tracks")
    assert resp.status_code == 200
    tracks = resp.json()["tracks"]
    assert [t["id"] for t in tracks] == created_ids
    assert [t["position"] for t in tracks] == [0, 1, 2]


async def test_concurrent_track_creation_assigns_unique_sequential_positions(
    async_client: AsyncClient, monkeypatch
) -> None:
    """Regression test for the create_track position race (Issue 2): folding
    the MAX(position) lookup into the INSERT as a single atomic statement
    means concurrent creates for the same session must still end up with
    distinct, sequential positions rather than duplicates."""
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    session = await _create_session(async_client)

    urls = [
        "https://www.youtube.com/watch?v=aaaaaaaaaaa",
        "https://www.youtube.com/watch?v=bbbbbbbbbbb",
        "https://www.youtube.com/watch?v=ccccccccccc",
        "https://www.youtube.com/watch?v=ddddddddddd",
        "https://www.youtube.com/watch?v=eeeeeeeeeee",
    ]
    results = await asyncio.gather(
        *(_add_track(async_client, session, session["client_id"], url) for url in urls)
    )

    resp = await async_client.get(f"/sessions/{session['id']}/tracks")
    assert resp.status_code == 200
    tracks = resp.json()["tracks"]
    positions = [t["position"] for t in tracks]

    assert len(results) == len(urls)
    assert sorted(positions) == list(range(len(urls)))
    assert len(set(positions)) == len(urls)


async def test_requested_by_display_name_resolves_for_active_member(
    async_client: AsyncClient, monkeypatch
) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    session = await _create_session(async_client)
    track = await _add_track(async_client, session, session["client_id"])
    assert track["requested_by_display_name"] == "Host"

    resp = await async_client.get(f"/sessions/{session['id']}/tracks")
    fetched = resp.json()["tracks"][0]
    assert fetched["requested_by_display_name"] == "Host"


async def test_requested_by_display_name_resolves_for_departed_member(
    async_client: AsyncClient, monkeypatch
) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    session = await _create_session(async_client)
    guest = await _join_session(async_client, session, "guest-1", display_name="Guest One")
    await _add_track(async_client, session, "guest-1")

    leave_resp = await async_client.post(
        f"/sessions/{session['id']}/leave", json={"client_id": "guest-1"}
    )
    assert leave_resp.status_code in (200, 204)

    resp = await async_client.get(f"/sessions/{session['id']}/tracks")
    fetched = resp.json()["tracks"][0]
    assert fetched["requested_by_display_name"] == "Guest One"
    assert guest["client_id"] == "guest-1"


async def test_reorder_updates_position_and_persists(async_client: AsyncClient, monkeypatch) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
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

    new_order = [created_ids[2], created_ids[0], created_ids[1]]
    resp = await async_client.put(
        f"/sessions/{session['id']}/tracks/order",
        json={"client_id": session["client_id"], "track_ids": new_order},
    )
    assert resp.status_code == 200
    assert [t["id"] for t in resp.json()["tracks"]] == new_order

    get_resp = await async_client.get(f"/sessions/{session['id']}/tracks")
    assert [t["id"] for t in get_resp.json()["tracks"]] == new_order


async def test_reorder_rejects_non_active_member(async_client: AsyncClient, monkeypatch) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    session = await _create_session(async_client)
    track = await _add_track(async_client, session, session["client_id"])

    resp = await async_client.put(
        f"/sessions/{session['id']}/tracks/order",
        json={"client_id": "not-a-member", "track_ids": [track["id"]]},
    )
    assert resp.status_code == 403


async def test_reorder_rejects_missing_track_id(async_client: AsyncClient, monkeypatch) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    session = await _create_session(async_client)
    await _add_track(async_client, session, session["client_id"], "https://www.youtube.com/watch?v=aaaaaaaaaaa")
    await _add_track(async_client, session, session["client_id"], "https://www.youtube.com/watch?v=bbbbbbbbbbb")

    resp = await async_client.get(f"/sessions/{session['id']}/tracks")
    ids = [t["id"] for t in resp.json()["tracks"]]

    order_resp = await async_client.put(
        f"/sessions/{session['id']}/tracks/order",
        json={"client_id": session["client_id"], "track_ids": [ids[0]]},
    )
    assert order_resp.status_code == 400


async def test_reorder_rejects_extra_foreign_track_id(async_client: AsyncClient, monkeypatch) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    session = await _create_session(async_client)
    track = await _add_track(async_client, session, session["client_id"])

    resp = await async_client.put(
        f"/sessions/{session['id']}/tracks/order",
        json={"client_id": session["client_id"], "track_ids": [track["id"], "nonexistent-track"]},
    )
    assert resp.status_code == 400


async def test_reorder_rejects_duplicate_track_id(async_client: AsyncClient, monkeypatch) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )
    session = await _create_session(async_client)
    track = await _add_track(async_client, session, session["client_id"])

    resp = await async_client.put(
        f"/sessions/{session['id']}/tracks/order",
        json={"client_id": session["client_id"], "track_ids": [track["id"], track["id"]]},
    )
    assert resp.status_code == 400


async def test_reorder_against_nonexistent_session_returns_404(async_client: AsyncClient) -> None:
    resp = await async_client.put(
        "/sessions/nonexistent/tracks/order",
        json={"client_id": "c1", "track_ids": []},
    )
    assert resp.status_code == 404


def test_websocket_broadcasts_queue_reordered(client: WsTestClient, monkeypatch) -> None:
    from tests.test_tracks import _fake_download_factory

    monkeypatch.setattr(
        tracks_module, "run_yt_dlp_sync", _fake_download_factory(with_captions=False)
    )

    session_resp = client.post("/sessions", json={"name": "ws-order", "display_name": "Host"})
    assert session_resp.status_code == 201
    session = session_resp.json()
    session_id, client_id = session["id"], session["client_id"]

    join_resp = client.post(
        f"/sessions/{session_id}/join",
        json={"passcode": session["passcode"], "display_name": "Guest", "client_id": "guest-1"},
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

        new_order = [ids[1], ids[0]]
        resp = client.put(
            f"/sessions/{session_id}/tracks/order",
            json={"client_id": client_id, "track_ids": new_order},
        )
        assert resp.status_code == 200

        msg = json.loads(ws.receive_text())
        assert msg["type"] == "queue_reordered"
        assert [t["id"] for t in msg["data"]["tracks"]] == new_order
