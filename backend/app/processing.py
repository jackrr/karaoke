"""DMUCS pipeline — audio processing, stem extraction, and karaoke creation."""
from dataclasses import dataclass
from pathlib import Path
import asyncio
import os
import shutil

from .db import get_db
from .utils.downloader import download_audio_from_yt
from .utils.acoustid import AcoustIDFingerprinter
from .utils.lrclib import LRCLIBClient
from .utils.demucs import DemucsStemSplitter

class AudioProcessingPipeline:
    """Full DMUCS pipeline: Download → Identify → Lyrics → Demucs → Vocal Track."""

    async def process(self, track_id: str) -> str:
        """Run full DMUCS pipeline for a track. Returns path to karaoke audio."""
        from .queue import get_queue  # avoid circular import
        
        # 1. Download audio
        audio_temp = await download_audio_from_yt(track_id)

        # 2. Identify ACROSTID
        acoustid = AcoustIDFingerprinter()
        metadata = acoustid.identify(audio_temp)

        # 3. Fetch lyrics (LRCLIB)
        lrclib = LRCLIBClient()
        lyrics = await lrclib.search_lyrics(metadata.get("title", ""), metadata.get("artist", ""))

        # 4. Demucs stem extraction
        demucs = DemucsStemSplitter()
        stems = await demucs.split_stems(audio_temp, str(Path(audio_temp).parent / "stems"))

        # 5. Create karaoke audio (no vocals)
        out_path = Path(audio_temp).with_name(Path(audio_temp).stem + "_karaoke.wav")
        shutil.copy2(audio_temp, out_path)  # placeholder — real would mix stems

        return str(out_path)
