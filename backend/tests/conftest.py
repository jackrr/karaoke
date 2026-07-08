import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.main import app


class WsTestClient:
    """Test client wrapper providing both HTTP requests and websocket support."""

    def __init__(self) -> None:
        self._test_client = TestClient(app)
        self.app = self._test_client.app

    def __enter__(self) -> "WsTestClient":
        return self

    def __exit__(self, *args: object) -> None:
        self._test_client.__exit__(*args)

    @property
    def http_client(self):
        return self._test_client

    def websocket_connect(self, path: str):
        return self._test_client.websocket_connect(path)


@pytest.fixture
def client() -> "WsTestClient":
    return WsTestClient()


@pytest.fixture
async def async_client() -> AsyncClient:
    """Async client for non-WS tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
