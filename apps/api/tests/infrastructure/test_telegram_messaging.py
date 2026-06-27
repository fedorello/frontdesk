"""TelegramMessaging sends Markdown as HTML, and falls back to plain text on a parse error."""

import json

import httpx

from frontdesk.application.ports import OutboundMessage
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.domain.models import Customer
from frontdesk.infrastructure.channels.telegram import TelegramMessaging

CUSTOMER = Customer(CustomerId("c"), BusinessId("b"), Channel.TELEGRAM, "555")


async def test_send_converts_markdown_to_html() -> None:
    calls: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    messaging = TelegramMessaging(token="111:AAA", bot_address="bot", client=client)

    await messaging.send(CUSTOMER, OutboundMessage("**hi** there"))

    assert calls[0]["text"] == "<b>hi</b> there"
    assert calls[0]["parse_mode"] == "HTML"


async def test_send_falls_back_to_plain_text_on_parse_error() -> None:
    calls: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        if body.get("parse_mode") == "HTML":
            return httpx.Response(400, json={"ok": False, "description": "can't parse entities"})
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    messaging = TelegramMessaging(token="111:AAA", bot_address="bot", client=client)

    await messaging.send(CUSTOMER, OutboundMessage("**oops"))

    assert len(calls) == 2  # HTML attempt, then plain fallback
    assert "parse_mode" not in calls[1]
    assert calls[1]["text"] == "**oops"  # the original text, unformatted, still delivered
