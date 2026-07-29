"""Pure, testable helpers for downloading YouTube audio + captions.

Deliberately has no FastAPI or DB imports — `tracks.py` wires this into the
web app and background-task machinery. The seam for tests is `run_yt_dlp_sync`:
tests monkeypatch `yt_dlp.YoutubeDL` (the class this module instantiates) with
a fake that writes canned files into `dest_dir`, so no real network call is
ever made.
"""

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

import webvtt
import yt_dlp

logger = logging.getLogger(__name__)

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


_MAX_ROLLING_CAPTION_GAP_SECONDS = 1.0


def _merge_rolling_captions(
    entries: list[tuple[float, str]],
) -> list[tuple[float, str]]:
    """Collapse YouTube auto-caption cues that redraw one line word-by-word."""
    merged: list[tuple[float, str]] = []
    last_cue_start: float | None = None
    for start, text in entries:
        # Time gate avoids merging a coincidentally-prefix-matching repeated lyric (e.g. a later chorus).
        is_rolling_continuation = (
            merged
            and text.startswith(merged[-1][1])
            and last_cue_start is not None
            and start - last_cue_start <= _MAX_ROLLING_CAPTION_GAP_SECONDS
        )
        if is_rolling_continuation:
            merged[-1] = (merged[-1][0], text)
        else:
            merged.append((start, text))
        last_cue_start = start
    return merged


def vtt_to_lrc(vtt_content: str) -> str:
    """Convert VTT caption content to LRC-format lyrics text."""
    parsed = webvtt.WebVTT.from_string(vtt_content)
    entries = []
    for caption in parsed.captions:
        start_seconds = _parse_vtt_timestamp_seconds(caption.start)
        text = " ".join(line.strip() for line in caption.text.splitlines() if line.strip())
        if not text:
            continue
        entries.append((start_seconds, text))

    merged = _merge_rolling_captions(entries)
    return "\n".join(
        f"[{_format_lrc_timestamp(start)}]{text}" for start, text in merged
    )


class _YtDlpLogAdapter:
    """Routes yt-dlp's own diagnostic output through our logger.

    `quiet`/`no_warnings` alone leave a hanging or retrying download
    completely silent — this surfaces yt-dlp's retries, throttling, and
    extractor warnings instead of us finding out only after the fact.
    """

    def debug(self, msg: str) -> None:
        if msg.startswith("[debug] "):
            return
        logger.info("yt-dlp: %s", msg)

    def info(self, msg: str) -> None:
        logger.info("yt-dlp: %s", msg)

    def warning(self, msg: str) -> None:
        logger.warning("yt-dlp: %s", msg)

    def error(self, msg: str) -> None:
        logger.error("yt-dlp: %s", msg)


def _make_progress_hook():
    """Build a progress_hooks callback that logs at most once every 5s.

    yt-dlp fires this on every read chunk (many times a second), so an
    unthrottled log line here would flood the log instead of clarifying
    what's happening.
    """
    last_logged = 0.0

    def _hook(progress: dict) -> None:
        nonlocal last_logged
        status = progress.get("status")
        if status == "downloading":
            now = time.monotonic()
            if now - last_logged < 5:
                return
            last_logged = now
            pct = progress.get("_percent_str", "?").strip()
            speed = progress.get("_speed_str", "?").strip()
            logger.info("yt-dlp: downloading %s at %s", pct, speed)
        elif status == "finished":
            logger.info("yt-dlp: finished downloading %s", progress.get("filename"))
        elif status == "error":
            logger.warning("yt-dlp: download hook reported an error")

    return _hook


@dataclass
class DownloadResult:
    audio_path: Path
    title: str
    duration_seconds: float | None
    vtt_path: Path | None
    artist: str | None = None
    album: str | None = None


def run_yt_dlp_sync(url: str, dest_dir: Path, cookies_file: str | None = None) -> DownloadResult:
    """Blocking download of best-audio + (if available) subtitles for `url`.

    Writes audio to `dest_dir/audio.<ext>` and, if captions are available
    (auto-generated or manual, preferring English), a VTT subtitle file into
    `dest_dir`. Must be called off the event loop (e.g. via
    `asyncio.to_thread`) since `yt_dlp.YoutubeDL` is fully synchronous.

    `cookies_file`, if given, is a path to a Netscape-format cookies.txt
    exported from a logged-in browser session; it's forwarded to yt-dlp so
    age/bot-check-gated videos ("Please sign in to confirm you're not a
    bot") can still be downloaded. The `android` player client is tried
    first regardless, since it sidesteps that check for most videos without
    needing cookies at all.

    Forces single-video mode (`noplaylist`), since URLs copied from a
    "radio"/mix queue or a playlist page carry a `list=` param that yt-dlp
    would otherwise expand into downloading the entire playlist.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(dest_dir / "audio.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "noprogress": True,
        "logger": _YtDlpLogAdapter(),
        "progress_hooks": [_make_progress_hook()],
        "socket_timeout": 30,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file

    logger.info("yt-dlp: extracting video info for %s", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    audio_path = _find_audio_path(dest_dir, info)
    vtt_path = _find_vtt_path(dest_dir)

    return DownloadResult(
        audio_path=audio_path,
        title=info.get("title") or "Untitled",
        duration_seconds=info.get("duration"),
        vtt_path=vtt_path,
        artist=info.get("artist"),
        album=info.get("album"),
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
