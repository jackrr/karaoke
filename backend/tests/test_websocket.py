from tests.conftest import WsTestClient
from app.websocket_manager import manager


def test_websocket_connects(client: WsTestClient) -> None:
    # TestClient handles the lifespan, so we can use normal `with`
    with client.websocket_connect("/ws/test-session") as ws:
        ws.send_text("hello")
        response = ws.receive_text()
        assert response == "hello"


def test_websocket_broadcast(client: WsTestClient) -> None:
    with client.websocket_connect("/ws/shared-session") as ws1:
        with client.websocket_connect("/ws/shared-session") as ws2:
            ws1.send_text("hello from ws1")
            # ws1 also receives its own broadcast
            resp1 = ws1.receive_text()
            assert resp1 == "hello from ws1"
            resp2 = ws2.receive_text()
            assert resp2 == "hello from ws1"


def test_websocket_discards_on_disconnect(client: WsTestClient) -> None:
    session_id = "disconnect-test"
    with client.websocket_connect(f"/ws/{session_id}") as ws:
        assert session_id in manager.active, f"Session {session_id} should be active"
        assert len(manager.active[session_id]) == 1

    # after leaving the context, it should be discarded
    assert session_id not in manager.active, (
        f"Session {session_id} should be discarded after disconnect"
    )
