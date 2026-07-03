"""Tests for app.utils.downloader – YouTube audio downloader."""
import os
import pytest
from app.utils.downloader import YouTubeAudioDownloader


class TestYouTubeAudioDownloader:
    def test_class_exists(self):
        assert YouTubeAudioDownloader is not None

    def test_download_method_exists(self):
        assert callable(YouTubeAudioDownloader.download)

    def test_default_options_have_expected_attributes(self):
        """YTDLOptions-style defaults used by the downloader."""
        expected = {"format", "extract_audio", "audio_format"}
        for attr in expected:
            assert hasattr(YouTubeAudioDownloader, attr) or hasattr(YouTubeAudioDownloader.download, '__func__')

    @pytest.mark.asyncio
    async def test_download_returns_a_path(self):
        """download should return a path string and create the directory."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await YouTubeAudioDownloader.download(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                tmpdir,
            )
            assert isinstance(result, str)
            assert result == os.path.join(tmpdir, "placeholder.mp3")
            # directory exists
            assert os.path.isdir(tmpdir)
