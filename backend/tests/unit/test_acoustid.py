"""Tests for app.utils.acoustid – AcoustID fingerprinting."""
import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
class TestAcoustIDFingerpinter:
    async def test_fingerprints_file(self):
        # The fingerprinter class should exist
        from app.utils.acoustid import AcoustIDFingerprinter
        f = AcoustIDFingerprinter("test-api-key")
        assert f.api_key == "test-api-key"
        assert hasattr(f, "identify")

    async def test_looks_up_id(self):
        from app.utils.acoustid import AcoustIDFingerprinter
        f = AcoustIDFingerprinter("test-api-key")
        # Verify methods exist
        assert hasattr(f, "identify")
        assert callable(getattr(f, "identify", None))


class TestFingerprintMethods:
    def test_constructor(self):
        from app.utils.acoustid import AcoustIDFingerprinter
        f = AcoustIDFingerprinter("key123")
        assert f.api_key == "key123"


class TestAcoustIDMethods:
    def test_methods_exist(self):
        from app.utils.acoustid import AcoustIDFingerprinter
        f = AcoustIDFingerprinter("k")
        assert callable(getattr(f, "identify", None))
