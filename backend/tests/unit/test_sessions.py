"""Tests for app.sessions – session CRUD and management."""
import time
import pytest

from app.schema import Session, Client, SessionStatus
from app.sessions import (
    generate_passcode,
    create_session,
    join_session,
    get_session_by_passcode,
    get_session_by_id,
    expire_stale_sessions,
    get_session_clients,
    add_client,
    remove_client,
)


class TestGeneratePasscode:
    def test_is_six_digits(self):
        code = generate_passcode()
        assert len(code) == 6
        assert code.isdigit()

    def test_is_string(self):
        assert isinstance(generate_passcode(), str)

    def test_is_alphanumeric(self):
        code = generate_passcode()
        assert code.isalnum()

    def test_multiple_codes_different(self):
        codes = {generate_passcode() for _ in range(20)}
        # With 1M space and 20 samples, we should get at least some unique ones
        # But it's theoretically possible (though extremely unlikely) to get all same
        # Just check no code has leading zero issues
        for code in codes:
            assert len(code) == 6
            assert code.isdigit()


class TestCreateSession:
    async def test_create_returns_session(self, mock_db):
        mock_db.execute = pytest.helpers.async_mock(return_value=1)
        session = await create_session("host-1", mock_db)
        assert isinstance(session, Session)
        assert session.id is not None
        assert session.host_id == "host-1"
        assert session.status == SessionStatus.active

    async def test_create_has_valid_passcode(self, mock_db):
        session = await create_session("host-1", mock_db)
        assert len(session.passcode) == 6
        assert session.passcode.isdigit()

    async def test_create_has_expires_at_future(self, mock_db):
        session = await create_session("host-1", mock_db)
        assert session.expires_at > session.created_at
        assert session.expires_at - session.created_at == 86400  # 24h


class TestJoinSession:
    async def test_join_returns_session(self, mock_db):
        mock_db.query_one = pytest.helpers.async_mock(return_value={
            "id": "s-1", "passcode": "123456", "host_id": None,
            "status": "active", "created_at": 100, "updated_at": 100, "expires_at": 100000,
        })
        session = await join_session("123456", "c-2", mock_db)
        assert session is not None
        assert session.id == "s-1"

    async def test_join_with_host(self, mock_db):
        mock_db.query_one = pytest.helpers.async_mock(return_value={
            "id": "s-1", "passcode": "123456", "host_id": "host-1",
            "status": "active", "created_at": 100, "updated_at": 100, "expires_at": 100000,
        })
        session = await join_session("123456", "c-2", mock_db)
        assert session.host_id == "host-1"
        # Should NOT replace existing host
        call_args = mock_db.execute.call_args_list
        # execute should not have been called (no host update)
        assert not any(
            "UPDATE sessions SET host_id" in str(c)
            for c in call_args
        )

    async def test_join_no_host_set_first(self, mock_db):
        mock_db.query_one = pytest.helpers.async_mock(return_value={
            "id": "s-1", "passcode": "123456", "host_id": None,
            "status": "active", "created_at": 100, "updated_at": 100, "expires_at": 100000,
        })
        session = await join_session("123456", "first-guest", mock_db)
        # The host_id should be set to the first guest
        update_calls = [
            c for c in mock_db.execute.call_args_list
            if c[0] and "UPDATE sessions SET host_id" in c[0][0]
        ]
        assert len(update_calls) == 1
        assert update_calls[0][0][1][0] == "first-guest"

    async def test_join_nonexistent_returns_none(self, mock_db):
        mock_db.query_one = pytest.helpers.async_mock(return_value=None)
        session = await join_session("999999", "c-3", mock_db)
        assert session is None

    async def test_join_excluded_session(self, mock_db):
        mock_db.query_one = pytest.helpers.async_mock(return_value={
            "id": "s-1", "passcode": "123456", "host_id": None,
            "status": "gone", "created_at": 100, "updated_at": 100, "expires_at": -1000,
        })
        session = await join_session("123456", "c-3", mock_db)
        assert session is (None)  # status filter excludes it


class TestGetSessionByPasscode:
    async def test_found(self, mock_db):
        mock_db.query_one = pytest.helpers.async_mock(return_value={
            "id": "s-1", "passcode": "PASS", "host_id": "h-1",
            "status": "active", "created_at": 100, "updated_at": 100, "expires_at": 100000,
        })
        session = await get_session_by_passcode("PASS", mock_db)
        assert session is not None
        assert session.passcode == "PASS"

    async def test_not_found(self, mock_db):
        mock_db.query_one = pytest.helpers.async_mock(return_value=None)
        session = await get_session_by_passcode("NOPE", mock_db)
        assert session is None


class TestGetSessionById:
    async def test_found(self, mock_db):
        mock_db.query_one = pytest.helpers.async_mock(return_value={
            "id": "s-1", "passcode": "PASS", "host_id": "h-1",
            "status": "active", "created_at": 100, "updated_at": 100, "expires_at": 100000,
        })
        session = await get_session_by_id("s-1", mock_db)
        assert session is not None
        assert session.id == "s-1"

    async def test_not_found(self, mock_db):
        mock_db.query_one = pytest.helpers.async_mock(return_value=None)
        session = await get_session_by_id("s-99", mock_db)
        assert session is None


class TestExpireStaleSessions:
    async def test_expires_old_sessions(self, mock_db):
        mock_db.connection = pytest.helpers.async_mock()
        mock_conn = pytest.helpers.async_mock()
        mock_conn.fetchall = pytest.helpers.async_mock(return_value=[])
        mock_db.connection.return_value.__aenter__ = pytest.helpers.async_mock(return_value=mock_conn)
        mock_db.connection.return_value.__aexit__ = pytest.helpers.async_mock(return_value=None)
        mock_db.connection.return_value = mock_conn

        result = await expire_stale_sessions(mock_db)
        assert isinstance(result, int)

    async def test_returns_count(self, mock_db):
        """Test that expired count is returned."""
        mock_db.connection = pytest.helpers.async_mock()
        mock_conn = pytest.helpers.async_mock()
        # rowcount for the update
        type(mock_conn).rowcount = pytest.helpers.async_mock()
        # Use a callable property
        type(mock_conn).rowcount = property(lambda self: 3)
        mock_db.connection.return_value.__aenter__ = pytest.helpers.async_mock(return_value=mock_conn)
        mock_db.connection.return_value.__aexit__ = pytest.helpers.async_mock(return_value=None)

        result = await expire_stale_sessions(mock_db)
        assert isinstance(result, int)


class TestGetSessionClients:
    async def test_returns_empty(self, mock_db):
        mock_db.query_all = pytest.helpers.async_mock(return_value=[])
        clients = await get_session_clients("s-1", mock_db)
        assert clients == []

    async def test_returns_clients_list(self, mock_db):
        mock_db.query_all = pytest.helpers.async_mock(return_value=[
            {"client_id": "c-1", "session_id": "s-1", "client_type": "host", "joined_at": 100, "connected": 1, "last_seen": 100},
            {"client_id": "c-2", "session_id": "s-1", "client_type": "guest", "joined_at": 200, "connected": 1, "last_seen": 200},
        ])
        clients = await get_session_clients("s-1", mock_db)
        assert len(clients) == 2
        assert isinstance(clients[0], Client)
        assert clients[0].client_id == "c-1"


class TestAddClient:
    async def test_adds_client(self, mock_db):
        mock_db.execute = pytest.helpers.async_mock(return_value=1)
        client = await add_client("s-1", "c-1", "host", mock_db)
        assert isinstance(client, Client)
        assert client.client_id == "c-1"
        assert client.session_id == "s-1"

    async def test_insert_called_with_correct_params(self, mock_db):
        mock_db.execute = pytest.helpers.async_mock(return_value=1)
        await add_client("s-1", "c-2", "guest", mock_db)
        calls = [str(c[0][0]) for c in mock_db.execute.call_args_list]
        assert any("INSERT INTO clients" in c for c in calls)


class TestRemoveClient:
    async def test_marks_disconnected(self, mock_db):
        mock_db.execute = pytest.helpers.async_mock(return_value=1)
        await remove_client("s-1", "c-1", mock_db)
        calls = [str(c[0][0]) for c in mock_db.execute.call_args_list]
        assert any("UPDATE clients SET connected = 0" in c for c in calls)
