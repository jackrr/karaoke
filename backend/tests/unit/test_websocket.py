"""Tests for app.websocket.manager – WebSocket connection manager."""
import asyncio
import pytest
from unittest.mock import MagicMock
from app.websocket.manager import WebSocketManager


@pytest.fixture
def ws_manager():
    return WebSocketManager()


class TestWebSocketManagerInit:
    def test_init_default_values(self, ws_manager):
        assert len(ws_manager.active_connections) == 0
        assert len(ws_manager.session_members) == 0
        assert len(ws_manager.client_sessions) == 0
        assert len(ws_manager.client_disconnects) == 0
        assert ws_manager._heartbeat_interval == 15


class TestConnect:
    async def test_connect_registers_client(self, ws_manager):
        ws = MagicMock()
        client_id = await ws_manager.connect(ws, "s-1", "c-1")
        assert client_id in ws_manager.active_connections
        assert client_id in ws_manager.session_members.get("s-1", set())

    async def test_connect_creates_new_client_id(self, ws_manager):
        ws = MagicMock()
        client_id = await ws_manager.connect(ws, "s-1")
        assert client_id is not None

    async def test_connect_sets_session_id(self, ws_manager):
        ws = MagicMock()
        await ws_manager.connect(ws, "s-1", "c-1")
        assert ws_manager.client_sessions["c-1"] == "s-1"

    async def test_connect_session_members_set(self, ws_manager):
        ws = MagicMock()
        await ws_manager.connect(ws, "s-1", "c-2")
        assert "c-2" in ws_manager.session_members["s-1"]


class TestDisconnect:
    async def test_disconnect_removes_client(self, ws_manager):
        ws = MagicMock()
        await ws_manager.connect(ws, "s-1", "c-5")
        await ws_manager.disconnect(ws, "c-5")
        assert "c-5" not in ws_manager.active_connections

    async def test_disconnect_not_in_connections_no_error(self, ws_manager):
        ws_manager.client_sessions["c-9"] = "s-1"
        await ws_manager.disconnect(MagicMock(), "c-9")


class TestBroadcast:
    async def test_broadcasts_to_session(self, ws_manager):
        ws1 = MagicMock()
        ws2 = MagicMock()
        ws_manager.active_connections = {"c-a": ws1, "c-b": ws2}
        ws_manager.session_members["s-a"] = {"c-a", "c-b"}
        ws_manager.client_sessions = {"c-a": "s-a", "c-b": "s-a"}

        await ws_manager.broadcast("s-a", {"test": 1})
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    async def test_broadcast_to_nonexistent_session(self, ws_manager):
        await ws_manager.broadcast("nonexistent", {"test": True})


class TestWSManagerMethods:
    def test_handle_connection_exists(self):
        from app.websocket.manager import WebSocketManager
        assert hasattr(WebSocketManager, "handle_connection")
        assert callable(getattr(WebSocketManager, "handle_connection", None))

    def test_handle_connection_is_async(self):
        from app.websocket.manager import WebSocketManager
        import asyncio
        import inspect
        assert asyncio.iscoroutinefunction(getattr(WebSocketManager, "handle_connection", None))

    def test_handle_connection_signature(self):
        from app.websocket.manager import WebSocketManager
        import inspect
        sig = inspect.signature(WebSocketManager.handle_connection)
        params = list(sig.parameters.keys())
        assert "websocket" in params
        assert "session_id" in params
