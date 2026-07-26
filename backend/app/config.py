from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Karaoke Backend"
    database_path: str = ":memory:"
    debug: bool = False
    skip_track_download: bool = False
    storage_dir: str = "storage"
    vocal_volume_fraction: float = 0.20
    demucs_model: str = "htdemucs"
    youtube_cookies_file: str | None = None
    session_ttl_seconds: float = 6 * 60 * 60
    reaper_interval_seconds: float = 15 * 60

    model_config = {"env_file": ".env"}


settings = Settings()
