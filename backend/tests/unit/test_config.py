"""Tests for app.config – settings loading, defaults, env var overrides."""
import os

import pytest
from pydantic_settings import SettingsConfigDict

from app.config import Settings, settings


class TestSettingsDefaults:
    """Test that Settings loads with documented defaults."""

    def test_app_name(self):
        assert settings.app_name == "Karaoke"

    def test_debug_is_false(self):
        assert settings.debug is False

    def test_db_path_exists(self):
        assert settings.db_path.exists() or "/karaoke.db" in str(settings.db_path)

    def test_storage_root_exists(self):
        assert settings.storage_root.exists()

    def test_storage_dir_returns_root(self):
        assert settings.storage_dir == settings.storage_root

    def test_demucs_device_default(self):
        assert settings.demucs_device == "auto"

    def test_max_concurrent_jobs(self):
        assert settings.max_concurrent_jobs == 2

    def test_cors_origins_default(self):
        assert "http://localhost:5173" in settings.cors_origins
        assert "http://127.0.0.1:5173" in settings.cors_origins

    def test_session_expiry_secs(self):
        assert settings.session_expiry_secs == 24 * 3600

    def test_heartbeat_interval(self):
        assert settings.heartbeat_interval == 15


class TestSettingsEnvOverrides:
    """Test that env vars override defaults."""

    def test_env_prefix(self):
        """Verify the model config uses KARAOKE_ prefix."""
        assert Settings.model_config.get("env_prefix") == "KARAOKE_"

    @pytest.mark.parametrize("env_var,default_val,expected", [
        ("KARAOKE_APP_NAME", "Karaoke", "MyKaraoke"),
        ("KARAOKE_DEBUG", "false", "true"),
        ("KARAOKE_DEBUG", "True", "true"),
        ("KARAOKE_DEMUCS_DEVICE", "auto", "cuda"),
        ("KARAOKE_MAX_CONCURRENT_JOBS", "2", "4"),
        ("KARAOKE_SESSION_EXPIRY_SECS", "900", "3600"),
        ("KARAOKE_HEARTBEAT_INTERVAL", "15", "30"),
    ])
    def test_env_var_override(self, monkeypatch, env_var, default_val, expected):
        monkeypatch.setenv(env_var, expected)
        # Force reload of settings by creating a fresh instance
        s = Settings()
        if env_var == "KARAOKE_APP_NAME":
            assert s.app_name == expected
        elif env_var == "KARAOKE_DEBUG":
            assert s.debug is True
        elif env_var == "KARAOKE_DEMUCS_DEVICE":
            assert s.demucs_device == expected
        elif env_var == "KARAOKE_MAX_CONCURRENT_JOBS":
            assert s.max_concurrent_jobs == int(expected)
        elif env_var == "KARAOKE_SESSION_EXPIRY_SECS":
            assert s.session_expiry_secs == int(expected)
        elif env_var == "KARAOKE_HEARTBEAT_INTERVAL":
            assert s.heartbeat_interval == int(expected)


class TestSettingsClass:
    """Test the Settings model class itself."""

    def test_model_dump(self):
        s = Settings()
        dumped = s.model_dump()
        assert "app_name" in dumped
        assert "debug" in dumped
        assert "db_path" in dumped
        assert "storage_root" in dumped
        assert "demucs_device" in dumped
        assert "cors_origins" in dumped

    def test_model_dump_json(self):
        s = Settings()
        json_str = s.model_dump_json()
        assert '"app_name"' in json_str

    def test_all_fields_defined(self):
        model_fields = Settings.model_fields
        expected = {
            "app_name", "debug", "db_path", "storage_root",
            "demucs_device", "max_concurrent_jobs", "cors_origins",
            "session_expiry_secs", "heartbeat_interval",
        }
        assert expected.issubset(set(model_fields.keys()))


class TestSettingsStorageDir:
    """Test storage_dir property."""

    def test_storage_dir_is_path(self):
        assert hasattr(settings.storage_dir, '__fspath__') or isinstance(settings.storage_dir, os.PathLike)

    def test_storage_dir_matches_root(self):
        assert settings.storage_dir == settings.storage_root
