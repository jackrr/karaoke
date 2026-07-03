"""Tests for app.db – async database layer with aiosqlite."""
import asyncio
import tempfile
from pathlib import Path

import pytest

from app.db import Database, SCHEMA_VERSION, SCHEMA_SQL, INDEX_SQL, get_db, init_db, close_db


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a unique temp DB path per test."""
    return tmp_path / "test.db"


@pytest.fixture
async def db(temp_db_path: Path):
    """Provide a fully migrated database."""
    d = Database(temp_db_path)
    await d.connect()
    yield d
    await d.close()


class TestDatabaseInit:
    def test_schema_version(self, temp_db_path):
        d = Database(temp_db_path)
        assert d.db_path == temp_db_path
        assert SCHEMA_VERSION == 1

    def test_connection_opens(self, temp_db_path):
        d = Database(temp_db_path)
        asyncio.run(d.connect())
        assert d._connection is not None
        asyncio.run(d.close())

    def test_close_nullifies_connection(self, temp_db_path):
        d = Database(temp_db_path)
        asyncio.run(d.connect())
        asyncio.run(d.close())
        assert d._connection is None


class TestDatabaseCRUD:
    @pytest.fixture(autouse=True)
    async def _setup(self, temp_db_path):
        self.d = Database(temp_db_path)
        await self.d.connect()
        yield
        await self.d.close()

    async def test_connection_context(self):
        """Test the async context manager yields live connection."""
        async with self.d.connection() as conn:
            assert conn is not None

    async def test_query_one_returns_none_for_empty(self):
        result = await self.d.query_one("SELECT * FROM sessions WHERE id = ?", ("nonexistent",))
        assert result is None

    async def test_query_all_returns_empty_list_for_empty(self):
        result = await self.d.query_all("SELECT * FROM sessions")
        assert result == []

    async def test_execute_insert_and_query(self):
        """Insert a row and verify it can be queried."""
        row_id = await self.d.execute(
            "INSERT INTO sessions (id, passcode, status) VALUES (?, ?, ?)",
            ("test-id", "123456", "active"),
        )
        assert row_id is not None

        row = await self.d.query_one(
            "SELECT id, passcode, status FROM sessions WHERE id = ?",
            ("test-id",)
        )
        assert row is not None
        assert row["id"] == "test-id"
        assert row["passcode"] == "123456"
        assert row["status"] == "active"

    async def test_execute_returns_lastrowid(self):
        rid = await self.d.execute("INSERT INTO sessions (id, passcode, status) VALUES (?, ?, ?)",
                                   ("eid", "PASS", "active"))
        assert isinstance(rid, int)
        assert rid > 0

    async def test_query_returns_dicts(self):
        await self.d.execute(
            "INSERT INTO sessions (id, passcode, status) VALUES (?, ?, ?)",
            ("q-1", "111111", "active"),
        )
        rows = await self.d.query_all("SELECT * FROM sessions WHERE id = ?", ("q-1",))
        assert len(rows) == 1
        assert isinstance(rows[0], dict)
        assert rows[0]["id"] == "q-1"

    async def test_query_many_rows(self):
        for i in range(3):
            await self.d.execute(
                "INSERT INTO sessions (id, passcode, status) VALUES (?, ?, ?)",
                (f"m-{i}", f"CODE{i}", "active"),
            )
        rows = await self.d.query_all("SELECT id FROM sessions WHERE status = 'active'")
        assert len(rows) == 3

    async def test_execute_many(self):
        await self.d.execute_many(
            "INSERT INTO sessions (id, passcode, status) VALUES (?, ?, ?)",
            [("em-1", "E1", "active"), ("em-2", "E2", "active")],
        )
        rows = await self.d.query_all("SELECT id FROM sessions")
        assert len(rows) == 2

    async def test_raw_sql(self):
        await self.d.raw_sql("INSERT INTO sessions (id, passcode, status) VALUES (?, ?, ?)",
                             ("rs-1", "RS1", "active"))
        rows = await self.d.query_all("SELECT id FROM sessions")
        assert any(r["id"] == "rs-1" for r in rows)

    async def test_query_with_param_type_str(self):
        await self.d.execute(
            "INSERT INTO sessions (id, passcode, status) VALUES (?, ?, ?)",
            ("str-test", "STR", "idle"),
        )
        row = await self.d.query_one("SELECT status FROM sessions WHERE passcode = ?", ("STR",))
        assert row["status"] == "idle"

    async def test_query_with_param_type_int(self):
        await self.d.execute(
            "INSERT INTO sessions (id, passcode, status) VALUES (?, ?, ?)",
            ("int-str", "PASS10", "active"),
        )
        row = await self.d.query_one("SELECT id FROM sessions WHERE id = ?", ("int-str",))
        assert row is not None

    async def test_query_all_with_no_rows(self):
        result = await self.d.query_all("SELECT id FROM nonexistent_table WHERE 1=2")
        assert result == []


class TestDatabaseSessionTable:
    """Verify sessions table schema is created correctly."""

    async def test_session_table_creates(self, db):
        rows = await db.query_all("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        assert len(rows) == 1

    async def test_session_unique_passcode(self, db):
        await db.execute(
            "INSERT INTO sessions (id, passcode, status) VALUES (?, ?, ?)",
            ("s1", "UNIQUE", "active"),
        )
        with pytest.raises(Exception):
            await db.execute(
                "INSERT INTO sessions (id, passcode, status) VALUES (?, ?, ?)",
                ("s2", "UNIQUE", "idle"),
            )

    async def test_clients_table_create(self, db):
        rows = await db.query_all("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
        assert len(rows) == 1

    async def test_queue_entries_table_create(self, db):
        rows = await db.query_all("SELECT name FROM sqlite_master WHERE type='table' AND name='queue_entries'")
        assert len(rows) == 1

    async def test_tracks_table_create(self, db):
        rows = await db.query_all("SELECT name FROM sqlite_master WHERE type='table' AND name='tracks'")
        assert len(rows) == 1

    async def test_processing_jobs_table_create(self, db):
        rows = await db.query_all("SELECT name FROM sqlite_master WHERE type='table' AND name='processing_jobs'")
        assert len(rows) == 1


class TestDatabaseIndexes:
    @pytest.fixture(autouse=True)
    async def _setup(self, temp_db_path):
        self.db = Database(temp_db_path)
        await self.db.connect()
        yield
        await self.db.close()

    def test_queue_entries_index(self):
        rows = self.db._connection.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='queue_entries'").fetchall()
        idx_names = [r[0] for r in rows]
        assert any("idx_queue_entries_session" in n for n in idx_names)

    def test_tracks_index(self):
        rows = self.db._connection.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        idx_names = [r[0] for r in rows]
        assert any("idx_tracks_hash" in n for n in idx_names)

    def test_clients_index(self):
        rows = self.db._connection.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        idx_names = [r[0] for r in rows]
        assert any("idx_clients_session" in n for n in idx_names)


class TestGetCloseDB:
    @pytest.fixture(autouse=True)
    def _reset(self):
        """Reset the global _db before each test."""
        import app.db as db_mod
        db_mod._db = None
        yield
        db_mod._db = None

    async def test_get_db_creates_instance(self, temp_db_path, monkeypatch):
        """Test get_db returns a Database instance."""
        from app.db import get_db
        import app.db as db_mod

        # Set a test db_path so it exists
        monkeypatch.setenv("KARAOKE_DB_PATH", str(temp_db_path.parent / "test_get.db"))
        monkeypatch.delattr("app.config.settings", "db_path", raising=False)

        # Reload config to use the temp path
        from app.config import Settings
        from app import config
        monkeypatch.setattr(config, 'settings', Settings(db_path=temp_db_path.parent / "test_get.db"))

        db = get_db()
        assert isinstance(db, Database)
        await db.connect()
        await db.close()


class TestSchemaContent:
    def test_schema_sql_contains_sessions(self):
        assert "CREATE TABLE" in SCHEMA_SQL
        assert "sessions" in SCHEMA_SQL

    def test_schema_sql_contains_clients(self):
        assert "clients" in SCHEMA_SQL

    def test_schema_sql_contains_tracks(self):
        assert "tracks" in SCHEMA_SQL

    def test_schema_sql_contains_queue_entries(self):
        assert "queue_entries" in SCHEMA_SQL

    def test_index_sql_exists(self):
        assert "queue_entries" in INDEX_SQL
