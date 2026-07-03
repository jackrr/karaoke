"""Tests for app.tracking – playback tracking logic."""
import time
import pytest
from app.tracking import get_session_state, get_position, list_positions


class TestTrackingFunctionsExist:
    def test_get_session_state_exists(self):
        assert callable(get_session_state)

    def test_get_position_exists(self):
        assert callable(get_position)

    def test_list_positions_exists(self):
        assert callable(list_positions)


class TestGetSessionState:
    async def test_returns_all_keys(self):
        state = get_session_state("s-1")
        assert isinstance(state, dict)
        assert "session" in state
        assert "queue" in state
        assert "track" in state
        assert "clients" in state

    async def test_session_in_state(self):
        state = get_session_state("s-1")
        assert state["session"] is not None

    async def test_queue_in_state(self):
        state = get_session_state("s-1")
        assert state["queue"] is not None
        assert isinstance(state["queue"], list)

    async def test_clients_in_state(self):
        state = get_session_state("s-1")
        assert state["clients"] is not None
        assert isinstance(state["clients"], list)


class TestGetPosition:
    def test_get_position_exists(self):
        assert callable(get_position)


class TestListPositions:
    def test_list_positions_exists(self):
        assert callable(list_positions)
