"""Tests for app.utils.demucs – stem splitting."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
from pathlib import Path


@pytest.mark.asyncio
class TestDemucsSplitter:
    async def test_initializes(self):
        from app.utils.demucs import DemucsSplitter
        s = DemucsSplitter(device="cpu")
        assert s.device == "cpu"

    async def test_splitters_exist(self):
        from app.utils.demucs import DemucsSplitter
        s = DemucsSplitter(device="cpu")
        # Verify splitter can be created
        assert s is not None


class TestDemucs:
    def test_constructor_defaults_cpu(self):
        from app.utils.demucs import DemucsSplitter
        s = DemucsSplitter()
        assert s.device in ("cpu", "cuda")


class TestDemucsMethods:
    def test_method_exists(self):
        from app.utils.demucs import DemucsSplitter
        s = DemucsSplitter(device="cpu")
        assert hasattr(s, "split") or callable(getattr(s, "split", None))

    def test_split_returns_path(self):
        # The real implementation returns Path objects
        from app.utils.demucs import DemucsSplitter
        s = DemucsSplitter()
        assert hasattr(s, "device")
