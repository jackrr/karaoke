"""Pure, testable helpers for vocal/instrumental separation and remixing.

Deliberately has no FastAPI or DB imports — tracks.py wires this into the
web app and background-task machinery. The seam for tests is
run_demucs_sync: tests monkeypatch it directly so no real model inference
ever runs in the test suite.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf


@dataclass
class SeparationResult:
    vocals_path: Path
    no_vocals_path: Path


def run_demucs_sync(audio_path: Path, dest_dir: Path, model: str) -> SeparationResult:
    """Blocking two-stem separation of audio_path into vocals/no_vocals.

    Must be called off the event loop (e.g. via asyncio.to_thread).
    """
    import demucs.separate

    demucs.separate.main(
        ["--two-stems", "vocals", "-n", model, "-o", str(dest_dir), str(audio_path)]
    )

    stem_dir = dest_dir / model / audio_path.stem
    vocals_path = stem_dir / "vocals.wav"
    no_vocals_path = stem_dir / "no_vocals.wav"

    if not vocals_path.exists() or not no_vocals_path.exists():
        raise FileNotFoundError(
            f"demucs did not produce expected output files in {stem_dir}"
        )

    return SeparationResult(vocals_path=vocals_path, no_vocals_path=no_vocals_path)


def mix_with_attenuated_vocals(
    vocals_path: Path, no_vocals_path: Path, output_path: Path, vocal_volume_fraction: float
) -> Path:
    """Sum no_vocals + (vocals * vocal_volume_fraction), write to output_path as WAV.

    Simple gain multiply (no loudness normalization). If input lengths differ
    slightly, truncate to the shorter. After summing, if peak abs sample > 1.0,
    scale the whole mix down by peak so it doesn't clip. Output is 16-bit PCM WAV.
    """
    vocals, vocals_rate = sf.read(str(vocals_path), dtype="float32", always_2d=True)
    no_vocals, no_vocals_rate = sf.read(str(no_vocals_path), dtype="float32", always_2d=True)

    min_len = min(len(vocals), len(no_vocals))
    vocals = vocals[:min_len]
    no_vocals = no_vocals[:min_len]

    mixed = no_vocals + (vocals * vocal_volume_fraction)

    peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
    if peak > 1.0:
        mixed = mixed / peak

    sf.write(str(output_path), mixed, no_vocals_rate, subtype="PCM_16")
    return output_path
