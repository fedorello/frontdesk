"""TelegramMessaging sends Markdown as HTML, and falls back to plain text on a parse error."""

import json

import httpx
import pytest

from frontdesk.application.ports import MessageNotDelivered, OutboundMessage
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


def _refusing(status: int, description: str) -> TelegramMessaging:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"ok": False, "description": description})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TelegramMessaging(token="111:SECRET", bot_address="bot", client=client)


@pytest.mark.parametrize(
    ("status", "permanent"),
    [(400, True), (403, True), (401, False), (404, False), (429, False), (502, False)],
)
async def test_a_refusal_raises_not_delivered_without_the_token(
    status: int, permanent: bool
) -> None:
    messaging = _refusing(status, "Bad Request: chat not found")

    with pytest.raises(MessageNotDelivered) as refused:
        await messaging.send(CUSTOMER, OutboundMessage("hi"))

    assert refused.value.permanent is permanent
    assert refused.value.reason == f"telegram {status}: Bad Request: chat not found"
    assert "SECRET" not in str(refused.value)


async def test_a_refusal_without_a_json_body_uses_the_status_phrase() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="<html>bad gateway</html>")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    messaging = TelegramMessaging(token="111:SECRET", bot_address="bot", client=client)

    with pytest.raises(MessageNotDelivered, match="telegram 502: Bad Gateway"):
        await messaging.send(CUSTOMER, OutboundMessage("hi"))


async def test_an_unreachable_telegram_is_temporary_and_hides_the_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url}", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    messaging = TelegramMessaging(token="111:SECRET", bot_address="bot", client=client)

    with pytest.raises(MessageNotDelivered) as refused:
        await messaging.send(CUSTOMER, OutboundMessage("hi"))

    assert refused.value.permanent is False
    assert refused.value.reason == "telegram unreachable: ConnectError"
    assert refused.value.__cause__ is None  # the URL-bearing httpx error is not chained
