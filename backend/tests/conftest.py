import asyncio
import os
from pathlib import Path

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
import pytest

from app.main import app
from app.database import get_db, start_db

# Initialize DB at import time so all fixtures can use it
_temp_dir = Path(os.environ.get("KARAOKE_TEST_DB_DIR", "/tmp/karaoke-test-db"))
_temp_dir.mkdir(parents=True, exist_ok=True)
_start_db_path = str(_temp_dir / "test.db")
start_db(_start_db_path)


class WsTestClient:
    """Test client with HTTP and WebSocket support."""

    def __init__(self) -> None:
        self._test_client = TestClient(app)
        self.app = self._test_client.app

    def __enter__(self) -> "WsTestClient":
        return self

    def __exit__(self, *args: object) -> None:
        if hasattr(self._test_client, "exit_stack"):
            self._test_client.__exit__(*args)

    def get(self, *args, **kwargs):
        return self._test_client.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self._test_client.post(*args, **kwargs)

    def websocket_connect(self, path: str):
        return self._test_client.websocket_connect(path)


@pytest.fixture
def client():
    tc = WsTestClient()
    try:
        yield tc
    finally:
        tc.__exit__(None, None, None)


@pytest.fixture
async def async_client():
    """Async HTTP client for non-WS tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
async def _setup_and_teardown_db():
    """Ensure tables exist before each test and clean up after."""
    conn = await get_db()
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS sessions ("
        "id TEXT PRIMARY KEY, "
        "name TEXT NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ")"
    )
    await conn.commit()
    yield
    # Clean up data - remove all tables to ensure isolation
    await conn.execute("DROP TABLE IF EXISTS sessions")
    await conn.commit()


@pytest.fixture(autouse=True, scope="session")
def _close_db_on_exit():
    """Guarantee the cached database connection is closed so the process exits after tests."""
    from app.database import close_db

    yield
    asyncio.run(close_db())



