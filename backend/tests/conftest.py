"""Shared pytest fixtures for the Karaoke backend test suite."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

# Make the app package importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# Override config's singleton before any tests run
os.environ["KARAOKE_DB_PATH"] = "/tmp/test_karaoke.db"


# ── Helper: patch asyncio.sleep to be a no-op for speed ──


@pytest.fixture(autouse=True)
def no_sleep():
    """Replace asyncio.sleep with a no-op for all async tests."""
    import asyncio
    original = asyncio.sleep
    asyncio.sleep = AsyncMock()
    yield
    asyncio.sleep = original


@pytest.fixture
def storage_root() -> Path:
    """Provide a temporary directory used as storage root for tests."""
    with tempfile.TemporaryDirectory() as td:
        os.environ["KARAOKE_STORAGE_ROOT"] = td
        yield Path(td)


@pytest.fixture
def test_db_path():
    """Return an in-memory SQLite path."""
    return "sqlite:///file::memory:?cache=shared"


@pytest.fixture
def mock_db_conn():
    """Provide a mock async database connection that mimics aiosqlite."""
    mock = MagicMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.close = AsyncMock()
    # Default fetchall / fetchone returns
    mock.fetchall = AsyncMock(return_value=[])
    mock.fetchone = AsyncMock(return_value=None)
    cursor = MagicMock()
    cursor.fetchall = AsyncMock(return_value=[])
    mock.execute.return_value = cursor
    return mock


@pytest.fixture
def mock_db(mock_db_conn):
    """Return a mock SQLAlchemy asyncengine-style DB."""
    mock_db = MagicMock()
    mock_db.connection = AsyncMock(return_value=mock_db_conn)
    mock_db.query_one = AsyncMock(return_value=None)
    mock_db.query_all = AsyncMock(return_value=[])
    return mock_db


@pytest.fixture
def mock_websocket():
    """Return a mock WebSocket with a message buffer."""
    ws = MagicMock()
    ws.send_json = AsyncMock()
    ws.accept = AsyncMock()
    ws.iter_json = MagicMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_session_service():
    """Return a mock of app.sessions functions."""
    from unittest.mock import patch
    from app.schema import Session, SessionCreate
    import time
    sess = Session(
        id="sess-1",
        passcode="TEST12",
        host_id="host-1",
        status="active",
        created_at=int(time.time()),
        updated_at=int(time.time()),
        expires_at=int(time.time()) + 3600,
    )
    fake = MagicMock()
    fake.create_session = AsyncMock(return_value=sess)
    fake.join_session = AsyncMock(return_value=sess)
    fake.get_session_by_passcode = AsyncMock(return_value=sess)
    fake.remove_client = AsyncMock()
    fake.get_session_clients = AsyncMock(return_value=[])
    return fake
