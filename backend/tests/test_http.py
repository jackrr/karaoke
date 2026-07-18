import re

from httpx import AsyncClient

from app.websocket_manager import manager


async def test_health_check(async_client: AsyncClient) -> None:
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_list_sessions_empty(async_client: AsyncClient) -> None:
    resp = await async_client.get("/sessions")
    assert resp.status_code == 200
    assert resp.json()["sessions"] == []


async def test_create_session(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/sessions", json={"name": "test-session", "display_name": "Host"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-session"
    assert "id" in data
    assert re.fullmatch(r"\d{6}", data["passcode"])
    assert data["host_client_id"]
    assert data["client_id"] == data["host_client_id"]

    # verify it appears in the list
    resp2 = await async_client.get("/sessions")
    assert resp2.status_code == 200
    names = [s["name"] for s in resp2.json()["sessions"]]
    assert "test-session" in names


async def test_list_sessions_does_not_leak_passcode(async_client: AsyncClient) -> None:
    await async_client.post("/sessions", json={"name": "secret-session", "display_name": "Host"})
    resp = await async_client.get("/sessions")
    assert resp.status_code == 200
    for session in resp.json()["sessions"]:
        assert "passcode" not in session


async def test_create_session_clears_manager() -> None:
    """Confirm the WebSocket manager is empty before/after tests."""
    assert len(manager.active) == 0
