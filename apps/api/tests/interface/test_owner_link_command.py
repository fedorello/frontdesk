"""The /connect command is recognized and routed to linking, bypassing the assistant."""

from datetime import UTC, datetime

import httpx
import pytest

from frontdesk.application.owner_linking import OwnerLinking
from frontdesk.application.ports import InboundMessage, TelegramBotConfig
from frontdesk.core.settings import Settings
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId, LinkCode
from frontdesk.domain.models import Business
from frontdesk.infrastructure.memory import (
    InMemoryBusinessRepository,
    InMemoryLlmConfigRepository,
    InMemoryOwnerNotificationSender,
    InMemoryOwnerTelegramLinkRepository,
    InMemoryTelegramLinkCodeStore,
    InMemoryUsageStore,
    ScriptedLlmProvider,
)
from frontdesk.infrastructure.system import FixedClock, FixedRandom, SequentialIdGenerator
from frontdesk.interface.telegram_inbound import TelegramInbound, is_owner_link_command
from tests.assistant_deps import build_assistant_deps

NOW = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
SETTINGS = Settings(secret_key="test-secret")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/connect", True),
        ("  /connect  ", True),
        ("/connect@my_bot", True),
        ("/CONNECT", True),
        ("/connect now please", True),
        ("connect", False),
        ("hello", False),
        ("", False),
    ],
)
def test_is_owner_link_command(text: str, expected: bool) -> None:
    assert is_owner_link_command(text) is expected


def _msg(text: str) -> InboundMessage:
    return InboundMessage(
        Channel.TELEGRAM, "owner-chat", "bot", text, NOW, "pm-1", sender_name="Owner"
    )


async def test_connect_command_starts_linking_and_skips_the_assistant() -> None:
    businesses = InMemoryBusinessRepository(
        [Business(BusinessId("biz"), "Studio", "UTC")],
        {(Channel.TELEGRAM, "bot"): BusinessId("biz")},
    )
    sender = InMemoryOwnerNotificationSender()
    codes = InMemoryTelegramLinkCodeStore()
    linking = OwnerLinking(
        codes,
        InMemoryOwnerTelegramLinkRepository(),
        businesses,
        sender,
        SequentialIdGenerator("code"),
        FixedClock(NOW),
        "http://app",
    )
    deps = build_assistant_deps(businesses)
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"ok": True}))
    )
    inbound = TelegramInbound(
        deps,
        InMemoryLlmConfigRepository(),
        InMemoryUsageStore(),
        SETTINGS,
        client,
        FixedRandom(),
        linking,
    )
    bot = TelegramBotConfig(BusinessId("biz"), "TOK", "sec", "bot", webhook_set=True)

    await inbound.handle(bot, _msg("/connect"))

    assert len(sender.sent) == 1  # the link was sent to the owner's chat
    assert sender.sent[0][1] == "owner-chat"
    assert await codes.get(LinkCode("code-1")) is not None  # a code was issued
    assert isinstance(deps.llm, ScriptedLlmProvider)
    assert deps.llm.calls == 0  # the assistant never ran for the command
