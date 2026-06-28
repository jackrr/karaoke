"""Demucs audio stem splitting."""
import asyncio
import os
import shutil
from pathlib import Path

class DemucsStemSplitter:
    """Split audio into stems using Demucs."""
    
    def __init__(self, device: str = "auto"):
        self.device = device
        self.stems = ["vocals", "bass", "drums", "other"]
    
    async def split_stems(self, audio_path: str, output_dir: str) -> dict:
        """Split audio into stems. Returns {stem_name: path}."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        # Use Python wrapper if available
        try:
            import demucs.separate
            cmd = [
                "demucs",
                "--out", str(output_dir),
                "--name", "demucs",
                "--device", self.device,
                audio_path
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            
            stems = {}
            for stem in self.stems:
                stem_path = out_path / "demucs" / f"{stem}.{Path(audio_path).suffix}"
                if stem_path.exists():
                    stems[stem] = str(stem_path)
            return stems
        except ImportError:
            # Fallback: no demucs available
            return {}
