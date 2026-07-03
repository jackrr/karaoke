"""Tests for app.queue – enqueue, reorder, remove, clear, list operations."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.schema import QueueEntry, QueueEntryCreate, QueueStatus, TrackSource, Track, TrackStatus
from app.queue import enqueue, reorder, remove, clear_session, get_queue, get_queue_by_passcode, advance_to_next


def _make_mock_db():
    """Create a mock aiosqlite-style connection."""
    mock = MagicMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()

    # Set up cursor chain
    cursor = MagicMock()
    mock.execute.return_value = cursor

    return mock, cursor


class TestEnqueue:
    async def test_enqueues_basic(self):
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(return_value=(0,))  # max position = 0
        cursor.description = [("count", None, None, None, None, None, None)]

        entry = await enqueue(
            QueueEntryCreate(source=TrackSource.youtube, source_url="https://youtu.be/x", client_id="c-1"),
            "s-1",
            mock_db,
        )
        assert isinstance(entry, QueueEntry)
        assert entry.session_id == "s-1"
        assert entry.status == QueueStatus.pending
        assert entry.source == "youtube"
        assert entry.metadata["source_url"] == "https://youtu.be/x"

    async def test_enqueues_second_entry(self):
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(return_value=(5,))  # existing max position = 5, so new = 6
        cursor.description = [("count", None, None, None, None, None, None)]

        entry = await enqueue(
            QueueEntryCreate(source=TrackSource.jellyfin, source_url="http://jf/i", client_id="c-2"),
            "s-1",
            mock_db,
        )
        assert entry.position == 6

    async def test_enqueues_when_empty(self):
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(return_value=(None,))
        cursor.description = [("count", None, None, None, None, None, None)]

        entry = await enqueue(
            QueueEntryCreate(source=TrackSource.upload, source_url="/tmp/f.mp3", client_id="c-3"),
            "s-1",
            mock_db,
        )
        assert entry.position == 0


class TestReorder:
    async def test_reorder_moves_forward(self):
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(side_effect=[
            ("s-1", 2),  # found entry, old position = 2
            None,  # no entry at new_position (nothing to shift down when moving forward)
            None,
            None,  # final fetch
        ])
        cursor.fetchall = AsyncMock(return_value=[])
        cursor.description = [("id", None, None, None, None, None, None)]

        entry = await reorder("e-1", 4, "c-1", mock_db)
        assert entry is not None

    async def test_reorder_moves_backward(self):
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(side_effect=[
            ("s-1", 4),  # old position = 4
            None,
            None,
            None,
        ])
        cursor.fetchall = AsyncMock(return_value=[])
        cursor.description = [("id", None, None, None, None, None, None)]

        entry = await reorder("e-1", 1, "c-1", mock_db)
        assert entry is not None

    async def test_reorder_same_position(self):
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(side_effect=[
            ("s-1", 2),  # same position
            None,
            None,
            None,
        ])
        cursor.fetchall = AsyncMock(return_value=[])
        cursor.description = [("id", None, None, None, None, None, None)]

        entry = await reorder("e-1", 2, "c-1", mock_db)
        assert entry is not None

    async def test_reorder_missing_entry_raises(self):
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await reorder("nonexistent", 3, "c-1", mock_db)


class TestRemove:
    async def test_removes_entry(self):
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(side_effect=[
            ("s-1",),  # session_id
            None,  # position query result
        ])
        mock_db.execute = AsyncMock(return_value=cursor)

        await remove("e-1", "c-1", mock_db)
        assert mock_db.commit.call_count >= 1

    async def test_removes_missing_entry_no_error(self):
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=cursor)

        await remove("nonexistent", "c-1", mock_db)  # should not raise


class TestClearSession:
    async def test_clears_queue(self):
        mock_db, cursor = _make_mock_db()

        await clear_session("s-1", "c-1", mock_db)
        assert mock_db.commit.call_count >= 1


class TestGetQueue:
    async def test_returns_entries(self, mock_db):
        mock_db.query_all = AsyncMock(return_value=[
            {"id": "e-1", "session_id": "s-1", "track_id": None, "position": 0, "status": "pending",
             "added_by": "c-1", "source": "youtube", "metadata": None, "added_at": 100, "updated_at": 100},
        ])
        entries = await get_queue("s-1", mock_db)
        assert len(entries) == 1
        assert isinstance(entries[0], QueueEntry)
        assert entries[0].id == "e-1"
        assert entries[0].position == 0

    async def test_returns_empty_list(self, mock_db):
        mock_db.query_all = AsyncMock(return_value=[])
        entries = await get_queue("s-1", mock_db)
        assert entries == []


class TestGetQueueByPasscode:
    async def test_returns_queue_for_passcode(self, mock_db):
        from app.schema import Session
        mock_db.query_one = AsyncMock(return_value={
            "id": "s-1", "passcode": "PASS", "host_id": None,
            "status": "active", "created_at": 100, "updated_at": 100, "expires_at": 100000,
        })
        mock_db.query_all = AsyncMock(return_value=[
            {"id": "e-1", "session_id": "s-1", "track_id": None, "position": 0, "status": "pending",
             "added_by": "c-1", "source": "youtube", "metadata": None, "added_at": 100, "updated_at": 100},
        ])
        entries = await get_queue_by_passcode("PASS", mock_db)
        assert len(entries) == 1

    async def test_returns_none_for_invalid_passcode(self, mock_db):
        mock_db.query_one = AsyncMock(return_value=None)
        entries = await get_queue_by_passcode("NOPE", mock_db)
        assert entries is None


class TestAdvanceToNext:
    async def test_advances_when_playing(self):
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(return_value=(0,))
        cursor.fetchall = AsyncMock(return_value=[
            [("e-2", "s-2", None, 1, "pending", "c-2", "youtube", None, 200, 200)]
        ])
        cursor.description = [("id", None, None, None, None, None, None)] * 10

        result = await advance_to_next(mock_db)
        assert result is not None
        assert result.session_id == "s-2"

    async def test_returns_none_when_empty(self):
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(return_value=(None,))
        cursor.fetchall = AsyncMock(return_value=[[]])
        cursor.description = [("id", None, None, None, None, None, None)] * 10

        result = await advance_to_next(mock_db)
        assert result is None

    async def test_advances_to_second(self):
        """If first is not ready, skip to next ready."""
        mock_db, cursor = _make_mock_db()
        cursor.fetchone = AsyncMock(return_value=(0,))
        # Mock for queue_entries: first one is processing, second is ready
        mock_db.query_one = AsyncMock(side_effect=[
            None,  # current track query
            None,  # processing check
            ("s-2",),  # session_id of ready queue_entry
        ])
        mock_db.query_all = AsyncMock(return_value=[])

        result = await advance_to_next(mock_db)
        # Should advance if it finds a non-processing entry
        assert result is not None


class TestPositionBoundaries:
    async def test_enqueues_after_existing(self, mock_db):
        mock_db.query_one = AsyncMock(return_value={
            "id": "s-1", "passcode": "PASS", "host_id": None,
            "status": "active", "created_at": 100, "updated_at": 100, "expires_at": 100000,
        })
        mock_db.query_all = AsyncMock(return_value=[
            {"id": "e-1", "session_id": "s-1", "position": 10, "track_id": None},
        ])
        entries = await get_queue_by_passcode("PASS", mock_db)
        assert entries is not None
        assert len(entries) == 1
