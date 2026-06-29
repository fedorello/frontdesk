"""Owner linking: issue a code + send the dashboard link, then confirm (redeem) it."""

from datetime import UTC, datetime, timedelta

import pytest

from frontdesk.application.owner_linking import OwnerLinking
from frontdesk.domain.errors import LinkCodeError
from frontdesk.domain.ids import BusinessId, LinkCode
from frontdesk.domain.models import Business
from frontdesk.domain.notifications import LinkCodeProblem
from frontdesk.infrastructure.memory import (
    InMemoryBusinessRepository,
    InMemoryOwnerNotificationSender,
    InMemoryOwnerTelegramLinkRepository,
    InMemoryTelegramLinkCodeStore,
)
from frontdesk.infrastructure.system import FixedClock, SequentialIdGenerator

NOW = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
BIZ = BusinessId("biz")


def _linking(
    *, now: datetime = NOW
) -> tuple[
    OwnerLinking,
    InMemoryTelegramLinkCodeStore,
    InMemoryOwnerTelegramLinkRepository,
    InMemoryOwnerNotificationSender,
]:
    codes = InMemoryTelegramLinkCodeStore()
    links = InMemoryOwnerTelegramLinkRepository()
    sender = InMemoryOwnerNotificationSender()
    businesses = InMemoryBusinessRepository([Business(BIZ, "Studio", "UTC", locale="ru")], {})
    linking = OwnerLinking(
        codes,
        links,
        businesses,
        sender,
        SequentialIdGenerator("code"),
        FixedClock(now),
        "http://app",
    )
    return linking, codes, links, sender


async def test_start_issues_a_code_and_sends_the_dashboard_link() -> None:
    linking, codes, _, sender = _linking()

    await linking.start(BIZ, "chat-1", "Owner")

    _, chat_id, message = sender.sent[0]
    assert chat_id == "chat-1"
    assert "/connect-telegram?code=code-1" in message  # localized (ru) message carries the link
    code = await codes.get(LinkCode("code-1"))
    assert code is not None
    assert code.chat_id == "chat-1"
    assert code.expires_at == NOW + timedelta(minutes=15)


async def test_confirm_binds_the_chat_and_spends_the_code() -> None:
    linking, codes, links, _ = _linking()
    await linking.start(BIZ, "chat-1", "Owner")

    link = await linking.confirm(BIZ, LinkCode("code-1"))

    assert link.chat_id == "chat-1"
    assert link.notifications_enabled is True
    stored = await links.get(BIZ)
    assert stored is not None
    assert stored.chat_id == "chat-1"
    spent = await codes.get(LinkCode("code-1"))
    assert spent is not None
    assert spent.used is True


async def test_confirm_rejects_an_unknown_code() -> None:
    linking, _, _, _ = _linking()

    with pytest.raises(LinkCodeError) as caught:
        await linking.confirm(BIZ, LinkCode("nope"))

    assert caught.value.problem is LinkCodeProblem.NOT_FOUND


async def test_confirm_rejects_a_used_code() -> None:
    linking, _, _, _ = _linking()
    await linking.start(BIZ, "chat-1", "Owner")
    await linking.confirm(BIZ, LinkCode("code-1"))

    with pytest.raises(LinkCodeError) as caught:
        await linking.confirm(BIZ, LinkCode("code-1"))

    assert caught.value.problem is LinkCodeProblem.USED


async def test_confirm_rejects_an_expired_code() -> None:
    linking, _, _, _ = _linking()
    await linking.start(BIZ, "chat-1", "Owner")
    later, _, _, _ = _linking(now=NOW + timedelta(minutes=20))  # a clock past the 15-min TTL
    later._codes = linking._codes  # reuse the issued code

    with pytest.raises(LinkCodeError) as caught:
        await later.confirm(BIZ, LinkCode("code-1"))

    assert caught.value.problem is LinkCodeProblem.EXPIRED


async def test_confirm_rejects_another_businesss_code() -> None:
    linking, _, _, _ = _linking()
    await linking.start(BIZ, "chat-1", "Owner")

    with pytest.raises(LinkCodeError) as caught:
        await linking.confirm(BusinessId("other"), LinkCode("code-1"))

    assert caught.value.problem is LinkCodeProblem.WRONG_BUSINESS
