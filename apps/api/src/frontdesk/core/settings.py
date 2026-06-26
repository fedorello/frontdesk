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
    # Key (urlsafe base64, 32 bytes) for encrypting stored secrets at rest (ADR-0009).
    secret_key: str = ""

    # The business the web chat demo talks to (matches the seeded channel binding).
    demo_to_address: str = "+BIZ"
    cors_allow_origins: str = "*"
    # Freeze "now" (ISO 8601) for a stable demo; empty = the real system clock.
    fixed_now: str = ""

    # LLM provider (model-agnostic; any OpenAI-compatible or Anthropic endpoint).
    llm_provider: str = "openai"  # "openai" | "anthropic"
    llm_api_key: str = ""
    llm_model: str = "deepseek/deepseek-v4-flash"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_max_tokens: int = 2048  # enough for a reasoning model to think AND emit the tool call

    # WhatsApp Cloud API.
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_verify_token: str = ""

    # Telegram Bot API.
    telegram_token: str = ""
    telegram_secret: str = ""
    telegram_bot_address: str = ""
