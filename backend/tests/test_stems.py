import numpy as np
import soundfile as sf

from app.stems import mix_with_attenuated_vocals


def _write_wav(path, samples: np.ndarray, sample_rate: int = 44100) -> None:
    sf.write(str(path), samples, sample_rate, subtype="FLOAT")


def test_mix_attenuates_and_sums(tmp_path) -> None:
    vocals = np.array([[0.4, 0.4], [0.2, 0.2]], dtype=np.float32)
    no_vocals = np.array([[0.1, 0.1], [0.1, 0.1]], dtype=np.float32)
    vocals_path = tmp_path / "vocals.wav"
    no_vocals_path = tmp_path / "no_vocals.wav"
    output_path = tmp_path / "mixed.wav"
    _write_wav(vocals_path, vocals)
    _write_wav(no_vocals_path, no_vocals)

    mix_with_attenuated_vocals(vocals_path, no_vocals_path, output_path, 0.5)

    result, _ = sf.read(str(output_path), dtype="float32", always_2d=True)
    expected = no_vocals + vocals * 0.5
    assert result.shape == expected.shape
    assert np.allclose(result, expected, atol=1e-3)


def test_mix_default_fraction_sanity(tmp_path) -> None:
    vocals = np.array([[1.0, 1.0]], dtype=np.float32)
    no_vocals = np.array([[0.0, 0.0]], dtype=np.float32)
    vocals_path = tmp_path / "vocals.wav"
    no_vocals_path = tmp_path / "no_vocals.wav"
    output_path = tmp_path / "mixed.wav"
    _write_wav(vocals_path, vocals)
    _write_wav(no_vocals_path, no_vocals)

    mix_with_attenuated_vocals(vocals_path, no_vocals_path, output_path, 0.20)

    result, _ = sf.read(str(output_path), dtype="float32", always_2d=True)
    assert np.allclose(result, 0.20, atol=1e-3)


def test_mix_clipping_guard_scales_without_distortion(tmp_path) -> None:
    vocals = np.array([[0.9, 0.9]], dtype=np.float32)
    no_vocals = np.array([[0.9, 0.9]], dtype=np.float32)
    vocals_path = tmp_path / "vocals.wav"
    no_vocals_path = tmp_path / "no_vocals.wav"
    output_path = tmp_path / "mixed.wav"
    _write_wav(vocals_path, vocals)
    _write_wav(no_vocals_path, no_vocals)

    mix_with_attenuated_vocals(vocals_path, no_vocals_path, output_path, 1.0)

    result, _ = sf.read(str(output_path), dtype="float32", always_2d=True)
    peak = np.max(np.abs(result))
    assert peak <= 1.0 + 1e-3

    naive_sum = no_vocals + vocals * 1.0  # all samples equal, so shape preserved
    naive_peak = np.max(np.abs(naive_sum))
    expected_scaled = naive_sum / naive_peak
    assert np.allclose(result, expected_scaled, atol=1e-3)


def test_mix_length_mismatch_truncates_to_min(tmp_path) -> None:
    vocals = np.array([[0.1, 0.1]] * 10, dtype=np.float32)
    no_vocals = np.array([[0.1, 0.1]] * 7, dtype=np.float32)
    vocals_path = tmp_path / "vocals.wav"
    no_vocals_path = tmp_path / "no_vocals.wav"
    output_path = tmp_path / "mixed.wav"
    _write_wav(vocals_path, vocals)
    _write_wav(no_vocals_path, no_vocals)

    mix_with_attenuated_vocals(vocals_path, no_vocals_path, output_path, 0.5)

    result, _ = sf.read(str(output_path), dtype="float32", always_2d=True)
    assert len(result) == 7


def test_run_demucs_omits_device_flag_when_auto(tmp_path, monkeypatch) -> None:
    captured = _capture_demucs_args(tmp_path, monkeypatch, device="auto")
    assert "-d" not in captured


def test_run_demucs_passes_device_flag_when_set(tmp_path, monkeypatch) -> None:
    captured = _capture_demucs_args(tmp_path, monkeypatch, device="cuda")
    assert captured[captured.index("-d") + 1] == "cuda"


def _capture_demucs_args(tmp_path, monkeypatch, device: str) -> list[str]:
    import demucs.separate

    from app.stems import run_demucs_sync

    audio_path = tmp_path / "song.wav"
    _write_wav(audio_path, np.zeros((4, 2), dtype=np.float32))
    dest_dir = tmp_path / "out"
    stem_dir = dest_dir / "htdemucs" / "song"
    stem_dir.mkdir(parents=True)
    captured: list[str] = []

    def fake_main(args):
        captured.extend(args)
        _write_wav(stem_dir / "vocals.wav", np.zeros((4, 2), dtype=np.float32))
        _write_wav(stem_dir / "no_vocals.wav", np.zeros((4, 2), dtype=np.float32))

    monkeypatch.setattr(demucs.separate, "main", fake_main)
    run_demucs_sync(audio_path, dest_dir, "htdemucs", device)
    return captured
