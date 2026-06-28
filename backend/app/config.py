from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings backed by environment variables or .env file."""

    app_name: str = "Karaoke"
    debug: bool = False

    # Database
    db_path: Path = Path(__file__).resolve().parent.parent / "karaoke.db"

    # Storage
    storage_root: Path = Path(__file__).resolve().parent.parent / "storage"

    # Audio processing
    demucs_device: str = "auto"  # "auto", "cuda", or "cpu"
    max_concurrent_jobs: int = 2

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Session expiration (seconds — 24h default)
    session_expiry_secs: int = 24 * 3600

    # WebSocket heartbeat interval (seconds)
    heartbeat_interval: int = 15

    @property
    def storage_dir(self) -> Path:
        return self.storage_root

    model_config = {"env_prefix": "KARAOKE_"}


settings = Settings()
