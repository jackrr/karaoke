from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Karaoke Backend"
    database_path: str = ":memory:"
    debug: bool = False
    storage_dir: str = "storage"

    model_config = {"env_file": ".env"}


settings = Settings()
