import json

import pytest
from starlette.websockets import WebSocketDisconnect

from tests.conftest import WsTestClient
from app.websocket_manager import manager


def _create_session(client: WsTestClient, name: str) -> dict:
    resp = client.post("/sessions", json={"name": name, "display_name": "Host"})
    assert resp.status_code == 201
    return resp.json()


def _join_session(client: WsTestClient, session_id: str, passcode: str, display_name: str) -> str:
    resp = client.post(
        f"/sessions/{session_id}/join",
        json={"passcode": passcode, "display_name": display_name},
    )
    assert resp.status_code == 200
    return resp.json()["client_id"]


def _next_chat_message(ws) -> str:
    """Read messages off the socket, skipping membership events, until a plain
    chat passthrough message (non-JSON, or JSON without a membership type) arrives."""
    while True:
        msg = ws.receive_text()
        try:
            parsed = json.loads(msg)
        except (json.JSONDecodeError, TypeError):
            return msg
        if not isinstance(parsed, dict) or parsed.get("type") not in (
            "member_joined",
            "member_left",
        ):
            return msg


def test_websocket_connects(client: WsTestClient) -> None:
    session = _create_session(client, "test-session")
    session_id, client_id = session["id"], session["client_id"]

    with client.websocket_connect(f"/ws/{session_id}?client_id={client_id}") as ws:
        ws.send_text("hello")
        response = _next_chat_message(ws)
        assert response == "hello"


def test_websocket_broadcast(client: WsTestClient) -> None:
    session = _create_session(client, "shared-session")
    session_id, client1 = session["id"], session["client_id"]
    client2 = _join_session(client, session_id, session["passcode"], "Guest")

    with client.websocket_connect(f"/ws/{session_id}?client_id={client1}") as ws1:
        with client.websocket_connect(f"/ws/{session_id}?client_id={client2}") as ws2:
            ws1.send_text("hello from ws1")
            # ws1 also receives its own broadcast
            resp1 = _next_chat_message(ws1)
            assert resp1 == "hello from ws1"
            resp2 = _next_chat_message(ws2)
            assert resp2 == "hello from ws1"


def test_websocket_discards_on_disconnect(client: WsTestClient) -> None:
    session = _create_session(client, "disconnect-test")
    session_id, client_id = session["id"], session["client_id"]

    with client.websocket_connect(f"/ws/{session_id}?client_id={client_id}"):
        assert session_id in manager.active, f"Session {session_id} should be active"
        assert len(manager.active[session_id]) == 1

    # after leaving the context, it should be discarded
    assert session_id not in manager.active, (
        f"Session {session_id} should be discarded after disconnect"
    )


def test_two_connections_same_client_id_both_stay_live(client: WsTestClient) -> None:
    """Two tabs sharing the same persisted client_id should both remain
    connected — the second connecting must not silently evict the first,
    and each should be independently disconnectable."""
    session = _create_session(client, "multi-tab-session")
    session_id, client_id = session["id"], session["client_id"]

    with client.websocket_connect(f"/ws/{session_id}?client_id={client_id}") as ws1:
        # drain exactly ws1's own member_joined event (there's nothing else
        # queued yet, so using `_next_chat_message` here would block forever
        # waiting for a non-membership message that never arrives).
        ws1.receive_text()

        with client.websocket_connect(f"/ws/{session_id}?client_id={client_id}") as ws2:
            assert len(manager.active[session_id][client_id]) == 2
            # drain ws1's and ws2's own member_joined broadcast for ws2's connect
            ws1.receive_text()
            ws2.receive_text()

            # A message sent on ws2 should be broadcast to both tabs (and to
            # itself), proving both sockets are live and receiving.
            ws2.send_text("hi from tab 2")
            assert ws1.receive_text() == "hi from tab 2"
            assert ws2.receive_text() == "hi from tab 2"

        # ws2 closed — ws1's connection must still be live.
        assert session_id in manager.active
        assert len(manager.active[session_id][client_id]) == 1

        ws1.send_text("still alive")
        assert ws1.receive_text() == "still alive"

    # both closed now
    assert session_id not in manager.active


def test_websocket_rejects_non_member(client: WsTestClient) -> None:
    session = _create_session(client, "reject-session")
    session_id = session["id"]

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/{session_id}?client_id=not-a-member"):
            pass


def test_websocket_requires_client_id_query_param(client: WsTestClient) -> None:
    session = _create_session(client, "missing-client-id")
    session_id = session["id"]

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/{session_id}"):
            pass


def test_websocket_disconnect_marks_member_left_in_db(client: WsTestClient) -> None:
    """A dropped websocket (no explicit /leave call) should still mark the
    member as left in the DB, so a subsequent GET no longer lists them."""
    session = _create_session(client, "disconnect-db-session")
    session_id, host_id = session["id"], session["client_id"]
    guest_id = _join_session(client, session_id, session["passcode"], "Guest")

    with client.websocket_connect(f"/ws/{session_id}?client_id={guest_id}"):
        resp = client.get(f"/sessions/{session_id}")
        participants = resp.json()["participants"]
        assert any(p["client_id"] == guest_id for p in participants)

    # After the socket closes, the guest should no longer show as an active participant.
    resp = client.get(f"/sessions/{session_id}")
    participants = resp.json()["participants"]
    assert all(p["client_id"] != guest_id for p in participants)
    assert any(p["client_id"] == host_id for p in participants)


def test_websocket_broadcasts_member_joined_and_left(client: WsTestClient) -> None:
    session = _create_session(client, "events-session")
    session_id, host_id = session["id"], session["client_id"]
    guest_id = _join_session(client, session_id, session["passcode"], "Guest1")

    with client.websocket_connect(f"/ws/{session_id}?client_id={host_id}") as host_ws:
        # drain the host's own member_joined event
        joined_self = json.loads(host_ws.receive_text())
        assert joined_self["type"] == "member_joined"
        assert joined_self["data"]["client_id"] == host_id

        with client.websocket_connect(f"/ws/{session_id}?client_id={guest_id}"):
            joined_guest = json.loads(host_ws.receive_text())
            assert joined_guest["type"] == "member_joined"
            assert joined_guest["data"]["client_id"] == guest_id

        left_guest = json.loads(host_ws.receive_text())
        assert left_guest["type"] == "member_left"
        assert left_guest["data"]["client_id"] == guest_id
