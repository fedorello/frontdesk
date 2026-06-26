"""The assistant system prompt grounds on the business + service descriptions."""

from frontdesk.application.assistant import _system_prompt
from frontdesk.domain.ids import BusinessId, ServiceId
from frontdesk.domain.models import Business, KnowledgeItem, Service


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

    prompt = _system_prompt(business, services)

    assert "About Ana Studio:\nA cosy two-chair salon downtown." in prompt
    assert "- Haircut (60 min) — Wash and cut." in prompt
    assert "Q: hours\nA: 9-5" in prompt


def test_prompt_omits_empty_descriptions() -> None:
    business = Business(BusinessId("b"), "Ana", "UTC")
    services = [Service(ServiceId("s"), BusinessId("b"), "Cut", 30)]

    prompt = _system_prompt(business, services)

    assert "About" not in prompt  # no empty "About" block
    assert "- Cut (30 min)" in prompt  # no trailing " — "
