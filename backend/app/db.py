"""Async SQLite layer with aiomonitor integration."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

logger = logging.getLogger(__name__)

# ── Schema Version ──

SCHEMA_VERSION = 1

# ── SQL DDL ──

SCHEMA_SQL = """
-- Sessions --------------------------------------------------------

CREATE TABLE IF NOT EXISTS sessions (
    id            TEXT PRIMARY KEY,
    passcode      TEXT UNIQUE NOT NULL,
    host_id       TEXT,
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at    INTEGER DEFAULT (strftime('%s', 'now')),
    expires_at    INTEGER
);

-- Clients ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS clients (
    client_id   TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    client_type TEXT NOT NULL DEFAULT 'guest',
    joined_at   INTEGER DEFAULT (strftime('%s', 'now')),
    connected   INTEGER DEFAULT 1,
    last_seen   INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Queue entries ---------------------------------------------------

CREATE TABLE IF NOT EXISTS queue_entries (
    id             TEXT PRIMARY KEY,
    session_id     TEXT NOT NULL REFERENCES sessions(id),
    track_id       TEXT,
    position       INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
    added_by       TEXT NOT NULL,
    source         TEXT NOT NULL DEFAULT 'youtube',
    metadata       TEXT,
    added_at       INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);

-- Tracks ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS tracks (
    id             TEXT PRIMARY KEY,
    hash           TEXT,
    title          TEXT NOT NULL,
    artist         TEXT,
    duration       REAL,
    storage_path   TEXT,
    stem_files     TEXT,
    lyrics_format  TEXT DEFAULT 'none',
    lyrics_source  TEXT,
    lyric_lines    TEXT,
    fallback_text  TEXT,
    status         TEXT NOT NULL DEFAULT 'processing',
    created_at     INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(hash, title)
);

-- Processing jobs -------------------------------------------------

CREATE TABLE IF NOT EXISTS processing_jobs (
    id                TEXT PRIMARY KEY,
    queue_entry_id    TEXT,
    stage             TEXT NOT NULL DEFAULT 'downloading',
    progress          REAL DEFAULT 0.0,
    started_at        INTEGER,
    finished_at       INTEGER,
    error             TEXT,
    device            TEXT,
    FOREIGN KEY (queue_entry_id) REFERENCES queue_entries(id)
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_queue_entries_session ON queue_entries(session_id, position);
CREATE INDEX IF NOT EXISTS idx_tracks_hash ON tracks(hash);
CREATE INDEX IF NOT EXISTS idx_clients_session ON clients(session_id);
CREATE INDEX IF NOT EXISTS idx_processing_queue ON processing_jobs(queue_entry_id);
"""


class Database:
    """Thin wrapper over aiosqlite with connection pooling."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    # ── Connection management ──

    async def connect(self) -> None:
        """Open the database and run migrations."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._run_migration()

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Reusable connection (caller must keep it alive)."""
        if not self._connection:
            await self.connect()
        yield self._connection

    # ── CRUD helpers ──

    async def query_one(self, sql: str, params=()) -> dict | None:
        async with self.connection() as conn:
            async with conn.execute(sql, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def query_all(self, sql: str, params=()) -> list[dict]:
        async with self.connection() as conn:
            async with conn.execute(sql, params) as cursor:
                return [dict(r) for r in await cursor.fetchall()]

    async def execute(self, sql: str, params=()) -> int:
        async with self.connection() as conn:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor.lastrowid

    async def execute_many(self, sql: str, params_list=()) -> None:
        async with self.connection() as conn:
            await conn.executemany(sql, params_list)
            await conn.commit()

    async def raw_sql(self, sql: str) -> None:
        """Execute arbitrary SQL (admin / migration)."""
        async with self.connection() as conn:
            await conn.execute(sql)
            await conn.commit()

    # ── Migration ──

    async def _run_migration(self) -> None:
        """Ensure schema is up-to-date with the latest version."""
        result = await self.query_one(
            "SELECT value FROM pragma_table_info('sessions'); "
            "SELECT count(*) FROM sqlite_master "
            "WHERE type='table' AND name='sessions'"
        )
        if result.get("count(*)") == 0:
            logger.info("Running initial schema migration (v%d)", SCHEMA_VERSION)
            # Use execute_script which handles semicolons properly.
            async with self.connection() as conn:
                await conn.executescript(SCHEMA_SQL)
                await conn.executescript(INDEX_SQL)
            await self._ensure_version_table()
        else:
            version = await self._get_version()
            if version < SCHEMA_VERSION:
                await self._migrate_to(version)

    async def _get_version(self) -> int:
        row = await self.query_one(
            "SELECT value FROM schema_info WHERE key='version'"
        )
        if row is None:
            return 0
        return int(row["value"])

    @property
    def db_path(self) -> Path:
        return self._db_path


# Module-level convenience ---------------------------------------------------

_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        from app.config import settings
        _db = Database(settings.db_path)
    return _db


async def init_db() -> Database:
    return get_db()


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
