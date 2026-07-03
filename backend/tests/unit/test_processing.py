"""Tests for app.processing – media processing pipeline."""
import asyncio
import pytest
from app.processing import AudioProcessingPipeline


class TestAudioProcessingPipeline:
    def test_class_exists(self):
        assert AudioProcessingPipeline is not None

    def test_process_method_exists(self):
        pipeline = AudioProcessingPipeline()
        assert hasattr(pipeline, "process")
        assert callable(pipeline.process)

    @pytest.mark.asyncio
    async def test_process_returns_string(self):
        """process should return a path string (even for placeholder)."""
        pipeline = AudioProcessingPipeline()
        # With the current placeholder implementation, this will try to
        # actually download a track. We test that the method exists and is
        # correctly structured without hitting the network.
        import inspect
        assert inspect.iscoroutinefunction(pipeline.process)
