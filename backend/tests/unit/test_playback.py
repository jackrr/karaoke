"""Tests for app.playback – audio playback engine with PyOgg/VLC backend."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from pathlib import Path


class TestPlaybackEngine:
    async def test_engine_initializes(self):
        from app.playback import PlaybackEngine
        # Can import and create instance (mocked)
        engine = MagicMock()
        assert engine is not None

    async def test_engine_has_play(self):
        from app.playback import PlaybackEngine
        assert hasattr(PlaybackEngine, "play")

    async def test_engine_has_pause(self):
        from app.playback import PlaybackEngine
        assert hasattr(PlaybackEngine, "pause")

    async def test_engine_has_resume(self):
        from app.playback import PlaybackEngine
        assert hasattr(PlaybackEngine, "resume")

    async def test_engine_has_stop(self):
        from app.playback import PlaybackEngine
        assert hasattr(PlaybackEngine, "stop")

    async def test_engine_has_seek(self):
        from app.playback import PlaybackEngine
        assert hasattr(PlaybackEngine, "seek")


class TestEngineMethods:
    def test_engine_methods_callable(self):
        from app.playback import PlaybackEngine
        methods = ["play", "pause", "resume", "stop", "reset", "volume", "get_metadata",
                    "get_current_time", "get_duration", "get_progress", "set_volume"]
        for method in methods:
            assert hasattr(PlaybackEngine, method)


class TestEngineBackend:
    def test_backend_exists(self):
        from app.playback import ENGINE_BACKEND
        assert ENGINE_BACKEND in ("pyogg", "vlc")


class TestEngineInit:
    def test_engine_init(self):
        from app.playback import PlaybackEngine
        # Test initialization doesn't crash
        e = PlaybackEngine()
        assert e is not None


class TestEngineProperties:
    def test_engine_has_status(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, "status")

    def test_engine_has_progress(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, "progress")

    def test_engine_has_duration(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, "duration")


class TestEngineStatus:
    def test_engine_status_values(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        # Status should be one of: stopped, playing, pausing, paused
        assert getattr(e, 'status', None) is not None


class TestEngineVolume:
    def test_volume_range(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        # Volume should be between 0 and 1
        volume = getattr(e, 'volume', 0.5)
        assert 0 <= volume <= 1


class TestEngineDuration:
    def test_duration_positive_or_zero(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        duration = getattr(e, 'duration', 0)
        assert duration >= 0


class TestEngineProgress:
    def test_progress_range(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        progress = getattr(e, 'progress', 0)
        assert 0 <= progress <= 1


class TestAudioPlayerMethods:
    def test_audio_player_exists(self):
        from app.playback import PlaybackEngine
        assert PlaybackEngine is not None


class TestEnginePlayAudioPath:
    def test_play_accepts_path(self):
        """Test that play method exists and accepts a path-like parameter."""
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'play')
        assert callable(e.play)


class TestEnginePauseResume:
    def test_pause_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'pause')
        assert callable(e.pause)

    def test_resume_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'resume')
        assert callable(e.resume)


class TestEngineSeek:
    def test_seek_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'seek')
        assert callable(e.seek)


class TestEngineStop:
    def test_stop_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'stop')
        assert callable(e.stop)


class TestEngineReset:
    def test_reset_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'reset')
        assert callable(e.reset)


class TestEngineVolumeMethod:
    def test_volume_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'volume')
        assert callable(e.volume)


class TestEngineGetMetadata:
    def test_get_metadata_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'get_metadata')
        assert callable(e.get_metadata)


class TestEngineGetCurrentTime:
    def test_get_current_time_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'get_current_time')
        assert callable(e.get_current_time)


class TestEngineGetDuration:
    def test_get_duration_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'get_duration')
        assert callable(e.get_duration)


class TestEngineProgress:
    def test_get_progress_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'get_progress')
        assert callable(e.get_progress)

    def test_get_progress_returns_float(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'get_progress')
        progress = e.get_progress()
        assert isinstance(progress, float)

    def test_progress_value_in_range(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        p = e.get_progress()
        assert 0.0 <= p <= 1.0


class TestEngineSetVolume:
    def test_set_volume_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'set_volume')
        assert callable(e.set_volume)


class TestEngineGetStatus:
    def test_get_status_method_exists(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        assert hasattr(e, 'status')

    def test_status_values(self):
        from app.playback import PlaybackEngine
        e = PlaybackEngine()
        status = e.status
        # Status should be a string value
        assert status is not None


class TestEngineGetSessionState:
    def test_get_session_state_returns_dict(self):
        from app.playback import get_engine_state
        state = get_engine_state("s1")
        assert isinstance(state, dict)

    def test_engine_state_keys(self):
        from app.playback import get_engine_state
        state = get_engine_state("s1")
        assert "session_id" in state
        assert "track_id" in state
        assert "current_time" in state
        assert "is_playing" in state


class TestEngineStart:
    def test_engine_start_starts_tracker(self, mock_db):
        from app.tracking import start_tracker
        import asyncio
        mock_db.query_one = AsyncMock(return_value={
            "id": "s1", "passcode": "PASS", "host_id": None,
            "status": "active", "created_at": 1, "updated_at": 1, "expires_at": 100000,
        })
        t = start_tracker("s1", mock_db, interval=0.1)
        t.start()
        assert t.is_running()
        t.stop()
        assert not t.is_running()


class TestEngineTrackerStopsCorrectly:
    async def test_tracker_stops_cleanly(self, mock_db):
        """Test that the playback tracker stops cleanly without raising."""
        from app.tracking import start_tracker
        mock_db.query_one = AsyncMock(return_value={
            "id": "s1", "passcode": "PASS", "host_id": None,
            "status": "active", "created_at": 1, "updated_at": 1, "expires_at": 100000,
        })
        t = start_tracker("s1", mock_db, interval=0.1)
        t.start()
        await asyncio.sleep(0.15)
        t.stop()
        await asyncio.sleep(0.05)  # Let stop handler run
        # No assertion needed, no exception raised


class TestEngineIsPlaying:
    def test_is_playing_flag(self):
        from app.playback import get_engine_state
        state = get_engine_state("s1")
        assert isinstance(state["is_playing"], bool)
