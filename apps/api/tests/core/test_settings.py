"""Settings hardening: an empty Telegram base must not blank the URL (caused 500s)."""

from frontdesk.core.settings import DEFAULT_TELEGRAM_API_BASE, Settings


def test_empty_telegram_api_base_falls_back_to_default() -> None:
    assert Settings(telegram_api_base="").telegram_api_base == DEFAULT_TELEGRAM_API_BASE
    assert Settings(telegram_api_base="   ").telegram_api_base == DEFAULT_TELEGRAM_API_BASE


def test_explicit_telegram_api_base_is_kept() -> None:
    assert Settings(telegram_api_base="http://mock:8081").telegram_api_base == "http://mock:8081"
