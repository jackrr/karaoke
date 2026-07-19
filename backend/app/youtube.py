"""Pure, testable helpers for downloading YouTube audio + captions.

Deliberately has no FastAPI or DB imports — `tracks.py` wires this into the
web app and background-task machinery. The seam for tests is `run_yt_dlp_sync`:
tests monkeypatch `yt_dlp.YoutubeDL` (the class this module instantiates) with
a fake that writes canned files into `dest_dir`, so no real network call is
ever made.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import webvtt
import yt_dlp

_WATCH_V_RE = re.compile(r"[?&]v=([\w-]{11})")
_YOUTU_BE_RE = re.compile(r"youtu\.be/([\w-]{11})")
_SHORTS_RE = re.compile(r"/shorts/([\w-]{11})")

_YOUTUBE_HOST_RE = re.compile(r"(^|\.)(youtube\.com|youtu\.be)$")


def extract_video_id(url: str) -> str | None:
    """Return the 11-char YouTube video id from a watch/youtu.be/shorts URL.

    Returns None for non-YouTube URLs or anything that doesn't parse.
    """
    if not url:
        return None
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
    except ValueError:
        return None

    host = (parsed.hostname or "").lower()
    if not _YOUTUBE_HOST_RE.search(host):
        return None

    for pattern in (_WATCH_V_RE, _YOUTU_BE_RE, _SHORTS_RE):
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def _format_lrc_timestamp(total_seconds: float) -> str:
    minutes = int(total_seconds // 60)
    seconds = total_seconds - minutes * 60
    return f"{minutes:02d}:{seconds:05.2f}"


def _parse_vtt_timestamp_seconds(timestamp: str) -> float:
    """Parse a VTT timestamp ("HH:MM:SS.mmm" or "MM:SS.mmm") to total seconds."""
    parts = timestamp.split(":")
    parts = [float(p) for p in parts]
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds


def vtt_to_lrc(vtt_content: str) -> str:
    """Convert VTT caption content to LRC-format lyrics text."""
    parsed = webvtt.WebVTT.from_string(vtt_content)
    lines = []
    for caption in parsed.captions:
        start_seconds = _parse_vtt_timestamp_seconds(caption.start)
        text = " ".join(line.strip() for line in caption.text.splitlines() if line.strip())
        if not text:
            continue
        lines.append(f"[{_format_lrc_timestamp(start_seconds)}]{text}")
    return "\n".join(lines)


@dataclass
class DownloadResult:
    audio_path: Path
    title: str
    duration_seconds: float | None
    vtt_path: Path | None


def run_yt_dlp_sync(url: str, dest_dir: Path) -> DownloadResult:
    """Blocking download of best-audio + (if available) subtitles for `url`.

    Writes audio to `dest_dir/audio.<ext>` and, if captions are available
    (auto-generated or manual, preferring English), a VTT subtitle file into
    `dest_dir`. Must be called off the event loop (e.g. via
    `asyncio.to_thread`) since `yt_dlp.YoutubeDL` is fully synchronous.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(dest_dir / "audio.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "socket_timeout": 30,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    audio_path = _find_audio_path(dest_dir, info)
    vtt_path = _find_vtt_path(dest_dir)

    return DownloadResult(
        audio_path=audio_path,
        title=info.get("title") or "Untitled",
        duration_seconds=info.get("duration"),
        vtt_path=vtt_path,
    )


def _find_audio_path(dest_dir: Path, info: dict) -> Path:
    candidates = sorted(dest_dir.glob("audio.*"))
    candidates = [p for p in candidates if p.suffix != ".vtt"]
    if not candidates:
        raise FileNotFoundError("yt-dlp did not produce an audio file")
    return candidates[0]


def _find_vtt_path(dest_dir: Path) -> Path | None:
    candidates = sorted(dest_dir.glob("*.vtt"))
    return candidates[0] if candidates else None
