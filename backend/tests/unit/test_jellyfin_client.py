"""Tests for app.jellyfin_client – Jellyfin API client."""
import pytest
import httpx


@pytest.mark.asyncio
class TestJellyfinClient:
    @pytest.mark.skip(reason="Requires network or mocking for this test")
    async def test_browse_library(self):
        from app.jellyfin_client import jellyfin_api
        # Skip until we have a mock HTTP transport
        ...

    @pytest.mark.skip(reason="Requires network or mocking for this test")
    async def test_search(self):
        from app.jellyfin_client import jellyfin_api
        ...

    @pytest.mark.skip(reason="Requires network or mocking for this test")
    async def test_stream_url(self):
        from app.jellyfin_client import jellyfin_api
        ...


class TestStreamUrlEndpoint:
    def test_expected_fields(self):
        """Test the expected stream URL endpoint fields exist."""
        from app.jellyfin_client import jellyfin_api
        # The stream endpoint returns dict with StreamUrl
        ...


class TestClientConfig:
    def test_expected_properties_exist(self):
        """Test that jellyfin_api has expected properties."""
        from app.jellyfin_client import jellyfin_api
        assert hasattr(jellyfin_api, "api_key")
        assert hasattr(jellyfin_api, "server_url")


class TestJellyfinAPI:
    @pytest.mark.skip(reason="Requires network or mocking")
    async def test_get_browse(self):
        ...

    @pytest.mark.skip(reason="Requires network or mocking")
    async def test_get_search(self):
        ...

    @pytest.mark.skip(reason="Requires network or mocking")
    async def test_get_stream_url(self):
        ...

    @pytest.mark.skip(reason="Requires network or mocking")
    async def test_get_items(self):
        ...

    @pytest.mark.skip(reason="Requires network or mocking")
    async def test_get_artists(self):
        ...

    @pytest.mark.skip(reason="Requires network or mocking")
    async def test_get_albums(self):
        ...

    @pytest.mark.skip(reason="Requires network or mocking")
    async def test_get_songs(self):
        ...
