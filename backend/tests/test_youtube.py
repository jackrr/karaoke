from pathlib import Path

import pytest

from app.youtube import DownloadResult, extract_video_id, run_yt_dlp_sync, vtt_to_lrc

SAMPLE_VTT = """WEBVTT

00:00:01.000 --> 00:00:04.000
Hello world

00:00:05.500 --> 00:00:07.000
Second line
of lyrics
"""


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=abc123", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?t=10", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("http://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ],
)
def test_extract_video_id_valid_urls(url: str, expected: str) -> None:
    assert extract_video_id(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://vimeo.com/12345",
        "not a url",
        "",
        "https://youtube.com/watch?x=dQw4w9WgXcQ",
    ],
)
def test_extract_video_id_invalid_urls(url: str) -> None:
    assert extract_video_id(url) is None


def test_vtt_to_lrc_converts_captions_to_lrc_lines() -> None:
    lrc = vtt_to_lrc(SAMPLE_VTT)
    lines = lrc.splitlines()
    assert lines == [
        "[00:01.00]Hello world",
        "[00:05.50]Second line of lyrics",
    ]


def test_vtt_to_lrc_empty_captions_yields_empty_string() -> None:
    empty_vtt = "WEBVTT\n"
    assert vtt_to_lrc(empty_vtt) == ""


class _FakeYoutubeDL:
    """Stands in for `yt_dlp.YoutubeDL` in tests: writes canned files to
    dest_dir instead of touching the network, mirroring the interface
    `run_yt_dlp_sync` relies on (context manager + `extract_info`)."""

    last_opts: dict | None = None
    dest_dir: Path | None = None
    write_vtt: bool = True

    def __init__(self, opts: dict) -> None:
        _FakeYoutubeDL.last_opts = opts

    def __enter__(self) -> "_FakeYoutubeDL":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def extract_info(self, url: str, download: bool = True) -> dict:
        assert _FakeYoutubeDL.dest_dir is not None
        audio_file = _FakeYoutubeDL.dest_dir / "audio.m4a"
        audio_file.write_bytes(b"fake audio bytes")
        if _FakeYoutubeDL.write_vtt:
            vtt_file = _FakeYoutubeDL.dest_dir / "video.en.vtt"
            vtt_file.write_text(SAMPLE_VTT)
        return {"title": "Fake Title", "duration": 123.4}


def test_run_yt_dlp_sync_with_captions(tmp_path, monkeypatch) -> None:
    dest_dir = tmp_path / "track-1"
    _FakeYoutubeDL.dest_dir = dest_dir
    _FakeYoutubeDL.write_vtt = True
    monkeypatch.setattr("app.youtube.yt_dlp.YoutubeDL", _FakeYoutubeDL)

    result = run_yt_dlp_sync("https://www.youtube.com/watch?v=dQw4w9WgXcQ", dest_dir)

    assert isinstance(result, DownloadResult)
    assert result.audio_path == dest_dir / "audio.m4a"
    assert result.audio_path.exists()
    assert result.title == "Fake Title"
    assert result.duration_seconds == 123.4
    assert result.vtt_path is not None
    assert result.vtt_path.exists()


def test_run_yt_dlp_sync_without_captions(tmp_path, monkeypatch) -> None:
    dest_dir = tmp_path / "track-2"
    _FakeYoutubeDL.dest_dir = dest_dir
    _FakeYoutubeDL.write_vtt = False
    monkeypatch.setattr("app.youtube.yt_dlp.YoutubeDL", _FakeYoutubeDL)

    result = run_yt_dlp_sync("https://www.youtube.com/watch?v=dQw4w9WgXcQ", dest_dir)

    assert result.vtt_path is None
