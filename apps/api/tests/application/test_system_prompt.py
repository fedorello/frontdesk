"""The assistant system prompt grounds on the business + service descriptions."""

from datetime import UTC, datetime

from frontdesk.application.assistant import (
    _known_customer_block,
    _system_prompt,
    _voice_system_prompt,
)
from frontdesk.domain.customer_memory import CustomerFact, CustomerProfile
from frontdesk.domain.ids import BusinessId, CustomerId, ServiceId
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

    prompt = _system_prompt(business, services, NOW, "")

    assert "About Ana Studio:\nA cosy two-chair salon downtown." in prompt
    assert "- Haircut (60 min) — Wash and cut." in prompt
    assert "Q: hours\nA: 9-5" in prompt


def test_prompt_omits_empty_descriptions() -> None:
    business = Business(BusinessId("b"), "Ana", "UTC")
    services = [Service(ServiceId("s"), BusinessId("b"), "Cut", 30)]

    prompt = _system_prompt(business, services, NOW, "")

    assert "About" not in prompt  # no empty "About" block
    assert "- Cut (30 min)" in prompt  # no trailing " — "


def test_prompt_states_the_physical_address() -> None:
    business = Business(BusinessId("b"), "Ana", "UTC", address="12 Rivera St")
    prompt = _system_prompt(business, [], NOW, "")
    assert "Location: 12 Rivera St" in prompt


def test_prompt_states_online_and_ignores_address() -> None:
    business = Business(BusinessId("b"), "Ana", "UTC", address="ignored", online=True)
    prompt = _system_prompt(business, [], NOW, "")
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
    assert "America/Montevideo" in _system_prompt(business, [], NOW, "")


def test_prompt_allows_light_markdown() -> None:
    prompt = _system_prompt(Business(BusinessId("b"), "Ana", "UTC"), [], NOW, "")
    assert "Markdown" in prompt
    assert "prefer short bullet lists over tables" in prompt


def test_known_customer_block_shows_facts_and_still_needed() -> None:
    profile = CustomerProfile(
        CustomerId("c"), BusinessId("b"), (CustomerFact("Birth date", "21 December 1984", NOW),)
    )

    block = _known_customer_block(profile, ["Birth date", "Birth time"])

    assert "- Birth date: 21 December 1984" in block  # a known fact to use, not ask
    assert "Still needed: Birth time" in block  # the one field left to collect


def test_known_customer_block_is_empty_when_nothing_known_or_needed() -> None:
    empty = CustomerProfile(CustomerId("c"), BusinessId("b"), ())

    assert _known_customer_block(empty, []) == ""


def test_voice_prompt_is_speech_tuned_yet_still_grounded() -> None:
    business = Business(
        BusinessId("b"),
        "Ana Studio",
        "America/Montevideo",
        knowledge=(KnowledgeItem("hours", "9-5"),),
        description="A cosy salon.",
    )
    services = [Service(ServiceId("s"), BusinessId("b"), "Haircut", 60)]

    voice = _voice_system_prompt(business, services, NOW, "APPOINTMENTS-BLOCK")
    text = _system_prompt(business, services, NOW, "APPOINTMENTS-BLOCK")

    # The voice prompt drops the text channel's messenger formatting guidance (it speaks, not types)
    assert "prefer short bullet lists over tables" in text
    assert "prefer short bullet lists over tables" not in voice
    assert "PHONE CALL" in voice  # speech-tuned
    assert "as BRIEF as possible" in voice  # keep spoken replies short
    assert "ONE at a time" in voice  # flow fix: collect intake one field at a time
    assert "no Markdown" in voice  # plain spoken words, not a messenger
    assert "FEMININE" in voice  # persona: a young woman — never the masculine 'понял'
    assert "поняла" in voice
    assert "never as digits" in voice  # numbers spoken as words, not robotic digits
    assert "- Haircut (60 min)" in voice  # still grounded on the real menu
    assert "Q: hours\nA: 9-5" in voice  # ...the knowledge base
    assert "APPOINTMENTS-BLOCK" in voice  # ...and the customer's appointments


def test_escalation_fallback_follows_business_locale() -> None:
    from frontdesk.application.assistant import ESCALATION_FALLBACK, _escalation

    ru = Business(BusinessId("b"), "Ana", "UTC", locale="ru")
    assert _escalation(ru) == ESCALATION_FALLBACK["ru"]
    assert _escalation(Business(BusinessId("b"), "Ana", "UTC")) == ESCALATION_FALLBACK["en"]


def test_prompt_states_the_current_date_and_offset() -> None:
    # NOW is Sat 27 Jun 2026 17:00 UTC = 14:00 Montevideo (UTC-3).
    business = Business(BusinessId("b"), "Ana", "America/Montevideo")
    prompt = _system_prompt(business, [], NOW, "")
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


def test_prompt_names_the_owner_and_explains_owner_turns() -> None:
    business = Business(BusinessId("b"), "Ana", "America/Montevideo", owner_name="Alex")
    prompt = _system_prompt(business, [], NOW, "")
    assert "Alex" in prompt  # the model knows the owner's name
    assert "[owner Alex]" in prompt  # ...and how their turns are tagged in the history
    assert "human owner" in prompt


def test_owner_tag_uses_the_name_when_set() -> None:
    from frontdesk.application.assistant import _owner_tag

    named = Business(BusinessId("b"), "A", "UTC", owner_name="Alex")
    assert _owner_tag(named) == "[owner Alex] "
    assert _owner_tag(Business(BusinessId("b"), "A", "UTC")) == "[owner] "
