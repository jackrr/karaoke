"""Tests for app.track_service – track service orchestration."""
import pytest
import asyncio
from app.track_service import TrackService, track_service


class TestCreateTrack:
    async def test_creates_track(self):
        track = track_service
        assert isinstance(track, TrackService)
        assert track.db is None
        assert track.jellyfin_client is None


class TestTrackService:
    async def test_track_service_is_instance_of_class(self):
        assert isinstance(track_service, TrackService)

    async def test_get_streams_method_exists(self):
        assert hasattr(track_service, "get_streams")
        assert asyncio.iscoroutinefunction(track_service.get_streams)

    async def test_update_track_status_method_exists(self):
        assert hasattr(track_service, "update_track_status")
        assert asyncio.iscoroutinefunction(track_service.update_track_status)

    async def test_get_stream_method_exists(self):
        assert hasattr(track_service, "get_stream")
        assert asyncio.iscoroutinefunction(track_service.get_stream)


class TestTrackServiceAsync:
    def test_track_service_exists(self):
        assert isinstance(track_service, TrackService)
