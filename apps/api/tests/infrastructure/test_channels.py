"""The channel adapters: outbound send (request shape) and inbound parsing."""

import json
from collections.abc import Callable

import httpx

from frontdesk.application.ports import MessagingPort, OutboundMessage
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.domain.models import Customer
from frontdesk.infrastructure.channels.telegram import TelegramMessaging, parse_telegram_inbound
from frontdesk.infrastructure.channels.whatsapp import WhatsAppMessaging, parse_whatsapp_inbound

Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _customer(address: str) -> Customer:
    return Customer(CustomerId("c"), BusinessId("b"), Channel.WHATSAPP, address)


async def test_whatsapp_sends_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/v21.0/PNID/messages"
        assert request.headers["authorization"] == "Bearer T"
        assert body["to"] == "+100"
        assert body["type"] == "text"
        assert body["text"]["body"] == "hi"
        return httpx.Response(200, json={"messages": [{"id": "wamid.1"}]})

    messaging: MessagingPort = WhatsAppMessaging(
        token="T", phone_number_id="PNID", client=_client(handler)
    )
    await messaging.send(_customer("+100"), OutboundMessage("hi"))


async def test_whatsapp_sends_interactive_buttons() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["type"] == "interactive"
        titles = [b["reply"]["title"] for b in body["interactive"]["action"]["buttons"]]
        assert titles == ["Confirm", "Reschedule"]
        return httpx.Response(200, json={})

    messaging = WhatsAppMessaging(token="T", phone_number_id="PNID", client=_client(handler))
    await messaging.send(
        _customer("+100"), OutboundMessage("ok", buttons=("Confirm", "Reschedule"))
    )


def test_whatsapp_inbound_parsing() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"display_phone_number": "+BIZ"},
                            "messages": [
                                {
                                    "from": "+100",
                                    "id": "wamid.X",
                                    "timestamp": "1782000000",
                                    "text": {"body": "hello"},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }
    inbound = parse_whatsapp_inbound(payload)
    assert inbound is not None
    assert (inbound.from_address, inbound.to_address, inbound.text) == ("+100", "+BIZ", "hello")
    assert inbound.provider_message_id == "wamid.X"
    assert parse_whatsapp_inbound({"entry": []}) is None  # a status event, not a message


async def test_telegram_sends_with_keyboard() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/botTKN/sendMessage"
        assert body["chat_id"] == "123"
        assert body["reply_markup"]["keyboard"][0][0]["text"] == "Confirm"
        return httpx.Response(200, json={"ok": True})

    messaging = TelegramMessaging(token="TKN", bot_address="+BOT", client=_client(handler))
    await messaging.send(_customer("123"), OutboundMessage("ok", buttons=("Confirm",)))


def test_telegram_inbound_parsing() -> None:
    payload = {"message": {"message_id": 5, "date": 1782000000, "chat": {"id": 123}, "text": "hi"}}
    inbound = parse_telegram_inbound(payload, bot_address="+BOT")
    assert inbound is not None
    assert (inbound.channel, inbound.from_address, inbound.text) == (Channel.TELEGRAM, "123", "hi")
    assert inbound.provider_message_id == "123:5"
    assert parse_telegram_inbound({"edited_message": {}}, bot_address="+BOT") is None
