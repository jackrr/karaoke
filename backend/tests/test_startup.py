from pathlib import Path

from app.config import settings
from app.main import _ensure_data_dirs


def test_ensure_data_dirs_creates_db_parent_and_storage(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "nested" / "deeper" / "karaoke.db"
    storage = tmp_path / "other" / "storage"
    monkeypatch.setattr(settings, "database_path", str(db_path))
    monkeypatch.setattr(settings, "storage_dir", str(storage))

    _ensure_data_dirs()

    assert db_path.parent.is_dir()
    assert storage.is_dir()


def test_ensure_data_dirs_tolerates_in_memory_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "database_path", ":memory:")
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))

    _ensure_data_dirs()

    assert not Path(":memory:").exists()
