"""Customer-facing datetimes render in the business's language, with an explicit UTC offset."""

from datetime import UTC, datetime

from frontdesk.application.datetime_format import format_when
from frontdesk.domain.ids import BusinessId
from frontdesk.domain.models import Business

# Tue 30 Jun 2026, 14:00 UTC = 11:00 in Montevideo (UTC-3).
_MOMENT = datetime(2026, 6, 30, 14, 0, tzinfo=UTC)


def _business(locale: str, timezone: str = "America/Montevideo") -> Business:
    return Business(BusinessId("b"), "Teo", timezone, locale=locale)


def test_format_when_localizes_weekday_and_month() -> None:
    assert format_when(_MOMENT, _business("ru")) == "вт 30 июн 11:00 (UTC-3)"
    assert format_when(_MOMENT, _business("en")) == "Tue 30 Jun 11:00 (UTC-3)"
    assert format_when(_MOMENT, _business("es")) == "mar 30 jun 11:00 (UTC-3)"


def test_format_when_uses_month_first_layout_for_chinese() -> None:
    assert format_when(_MOMENT, _business("zh")) == "周二 6月30日 11:00 (UTC-3)"


def test_format_when_falls_back_to_english_for_unknown_locale() -> None:
    assert format_when(_MOMENT, _business("xx")) == "Tue 30 Jun 11:00 (UTC-3)"


def test_format_when_shows_offset_relative_to_utc() -> None:
    # Positive whole-hour offset.
    assert format_when(_MOMENT, _business("en", "Asia/Dubai")).endswith("(UTC+4)")
    # Half-hour offset keeps the minutes.
    assert format_when(_MOMENT, _business("en", "Asia/Kolkata")).endswith("(UTC+5:30)")
    # Zero offset reads as plain UTC.
    assert format_when(_MOMENT, _business("en", "UTC")).endswith("(UTC)")
