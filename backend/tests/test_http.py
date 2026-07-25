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
    assert resp.json()["count"] == 0


async def test_create_session(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/sessions", json={"display_name": "Host"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert re.fullmatch(r"\d{6}", data["code"])
    assert data["host_client_id"]
    assert data["client_id"] == data["host_client_id"]

    # verify the count reflects the new session
    resp2 = await async_client.get("/sessions")
    assert resp2.status_code == 200
    assert resp2.json()["count"] == 1


async def test_list_sessions_returns_count_not_details(async_client: AsyncClient) -> None:
    await async_client.post("/sessions", json={"display_name": "Host"})
    resp = await async_client.get("/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"count": 1}


async def test_create_session_clears_manager() -> None:
    """Confirm the WebSocket manager is empty before/after tests."""
    assert len(manager.active) == 0
