"""The assistant system prompt grounds on the business + service descriptions."""

from datetime import UTC, datetime

from frontdesk.application.assistant import _system_prompt
from frontdesk.domain.ids import BusinessId, ServiceId
from frontdesk.domain.models import Business, KnowledgeItem, Service

NOW = datetime(2026, 6, 27, 17, 0, tzinfo=UTC)  # Sat 14:00 Montevideo


def test_prompt_includes_business_and_service_descriptions() -> None:
    business = Business(
        BusinessId("b"),
        "Ana Studio",
        "UTC",
        knowledge=(KnowledgeItem("hours", "9-5"),),
        description="A cosy two-chair salon downtown.",
    )
    services = [
        Service(ServiceId("s"), BusinessId("b"), "Haircut", 60, description="Wash and cut.")
    ]

    prompt = _system_prompt(business, services, NOW)

    assert "About Ana Studio:\nA cosy two-chair salon downtown." in prompt
    assert "- Haircut (60 min) — Wash and cut." in prompt
    assert "Q: hours\nA: 9-5" in prompt


def test_prompt_omits_empty_descriptions() -> None:
    business = Business(BusinessId("b"), "Ana", "UTC")
    services = [Service(ServiceId("s"), BusinessId("b"), "Cut", 30)]

    prompt = _system_prompt(business, services, NOW)

    assert "About" not in prompt  # no empty "About" block
    assert "- Cut (30 min)" in prompt  # no trailing " — "


def test_prompt_states_the_physical_address() -> None:
    business = Business(BusinessId("b"), "Ana", "UTC", address="12 Rivera St")
    prompt = _system_prompt(business, [], NOW)
    assert "Location: 12 Rivera St" in prompt


def test_prompt_states_online_and_ignores_address() -> None:
    business = Business(BusinessId("b"), "Ana", "UTC", address="ignored", online=True)
    prompt = _system_prompt(business, [], NOW)
    assert "online" in prompt
    assert "ignored" not in prompt  # online wins over a stale address


def test_slots_render_in_the_business_timezone() -> None:
    from datetime import UTC, datetime
    from zoneinfo import ZoneInfo

    from frontdesk.application.assistant import _format_slots
    from frontdesk.domain.models import TimeSlot

    tz = ZoneInfo("America/Montevideo")  # UTC-3
    slot = TimeSlot(
        datetime(2026, 6, 26, 12, 0, tzinfo=UTC), datetime(2026, 6, 26, 13, 0, tzinfo=UTC)
    )

    rendered = _format_slots([slot], tz)

    assert "09:00" in rendered  # 12:00 UTC shown as 09:00 local
    assert "UTC" not in rendered  # the misleading "UTC" suffix is gone
    assert "start=2026-06-26T12:00:00+00:00" in rendered  # exact UTC kept for booking


def test_prompt_states_the_timezone() -> None:
    business = Business(BusinessId("b"), "Ana", "America/Montevideo")
    assert "America/Montevideo" in _system_prompt(business, [], NOW)


def test_prompt_allows_light_markdown() -> None:
    prompt = _system_prompt(Business(BusinessId("b"), "Ana", "UTC"), [], NOW)
    assert "Markdown" in prompt
    assert "prefer short bullet lists over tables" in prompt


def test_escalation_fallback_follows_business_locale() -> None:
    from frontdesk.application.assistant import ESCALATION_FALLBACK, _escalation

    ru = Business(BusinessId("b"), "Ana", "UTC", locale="ru")
    assert _escalation(ru) == ESCALATION_FALLBACK["ru"]
    assert _escalation(Business(BusinessId("b"), "Ana", "UTC")) == ESCALATION_FALLBACK["en"]


def test_prompt_states_the_current_date_and_offset() -> None:
    # NOW is Sat 27 Jun 2026 17:00 UTC = 14:00 Montevideo (UTC-3).
    business = Business(BusinessId("b"), "Ana", "America/Montevideo")
    prompt = _system_prompt(business, [], NOW)
    assert "Saturday, 27 June 2026, 14:00" in prompt  # grounds relative dates like "Sunday"
    assert "UTC-3" in prompt  # explicit offset so the model has no doubt


def test_utc_offset_formatting() -> None:
    from datetime import timedelta, timezone

    from frontdesk.application.assistant import _utc_offset

    assert _utc_offset(datetime(2026, 6, 27, tzinfo=timezone(timedelta(hours=-3)))) == "UTC-3"
    assert _utc_offset(datetime(2026, 6, 27, tzinfo=UTC)) == "UTC+0"
    assert _utc_offset(datetime(2026, 6, 27, tzinfo=timezone(timedelta(hours=5, minutes=30)))) == (
        "UTC+5:30"
    )
