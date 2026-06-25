"""Smoke test: the Settings object loads with sane defaults and reads env."""

import pytest

from frontdesk.core.settings import Settings


def test_settings_load_defaults() -> None:
    settings = Settings()

    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.redis_url.startswith("redis://")
    assert settings.log_level == "INFO"


def test_settings_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTDESK_LOG_LEVEL", "DEBUG")

    assert Settings().log_level == "DEBUG"
