"""Typed application configuration, read once from the environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration in one place — no scattered ``os.environ`` reads.

    Values come from ``FRONTDESK_*`` environment variables (or a ``.env`` file),
    falling back to the local-development defaults below.
    """

    model_config = SettingsConfigDict(
        env_prefix="FRONTDESK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://frontdesk:frontdesk@localhost:5432/frontdesk"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
