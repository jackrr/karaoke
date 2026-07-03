"""Tests for app.utils.lrclib – LRCLIB lyrics client."""
import inspect
import pytest
from app.utils.lrclib import LRCLIBClient


class TestLRCLIBClient:
    def test_default_base_url(self):
        client = LRCLIBClient()
        assert client.base_url == "https://lrclib.net/api"

    def test_custom_base_url(self):
        client = LRCLIBClient(base_url="https://custom.lyrics")
        assert client.base_url == "https://custom.lyrics"

    def test_constructor_accepts_base_url(self):
        client = LRCLIBClient(base_url="http://test.com")
        assert client.base_url == "http://test.com"

    def test_search_lyrics_method_exists(self):
        client = LRCLIBClient()
        assert hasattr(client, "search_lyrics")
        assert callable(client.search_lyrics)

    def test_search_lyrics_signature(self):
        sig = inspect.signature(LRCLIBClient.search_lyrics)
        params = list(sig.parameters.keys())
        assert "title" in params
        assert "artist" in params
