"""Typed application configuration, read once from the environment."""

from enum import StrEnum

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramMode(StrEnum):
    """How the bot receives Telegram updates. See ADR-0010."""

    POLLING = "polling"  # the poller long-polls getUpdates; no public URL needed
    WEBHOOK = "webhook"  # Telegram pushes to the public URL


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
    # Public base URL of this server — where Telegram bots' webhooks are registered.
    public_url: str = "http://localhost:8000"
    # Telegram Bot API base — override for a self-hosted Bot API server or a local mock.
    telegram_api_base: str = DEFAULT_TELEGRAM_API_BASE
    # How the bot receives updates (ADR-0010): polling needs no public URL (self-host/dev).
    telegram_mode: TelegramMode = TelegramMode.POLLING
    telegram_poll_timeout_seconds: int = 25  # getUpdates long-poll hold time
    telegram_idle_poll_seconds: int = 5  # sleep when no bots are connected
    # Daily message cap per business on the managed-default LLM (0 = unlimited). Own-key
    # businesses are never capped. Cost control for the platform-paid default (ADR-0009).
    managed_default_daily_limit: int = 0
    # Owner session-token lifetime in seconds (0 = never expires). Default 7 days.
    token_max_age_seconds: int = 604800
    # Rate limits (per client IP) on abuse-prone auth endpoints. 0 disables the limit.
    login_rate_limit: int = 10  # attempts per window
    login_rate_window_seconds: int = 300  # 5 minutes
    signup_rate_limit: int = 5
    signup_rate_window_seconds: int = 3600  # 1 hour
    # If set, the real data-flow logs (events, messaging, agent, webhook) also go here.
    log_file: str = ""

    # The business the web chat demo talks to (matches the seeded channel binding).
    demo_to_address: str = "+BIZ"
    # Comma-separated allowed origins for credentialed CORS; empty falls back to dashboard_url.
    cors_allow_origins: str = ""
    # Where the OAuth callback sends the owner back (the dashboard origin).
    dashboard_url: str = "http://localhost:3000"
    # Sign in with Google (OAuth 2.0). An empty client id disables the feature.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""  # e.g. https://api.tovayo.com/api/auth/google/callback
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

    @field_validator("telegram_api_base")
    @classmethod
    def _telegram_base_or_default(cls, value: str) -> str:
        # An empty env var (FRONTDESK_TELEGRAM_API_BASE=) must not blank the base —
        # otherwise outbound URLs lose their protocol and every Telegram call crashes.
        return value.strip() or DEFAULT_TELEGRAM_API_BASE
