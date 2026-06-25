"""RoutingMessaging dispatches each reply to the customer's channel; the logging
event publisher accepts any domain event."""

import pytest

from frontdesk.application.ports import MessageReceived, OutboundMessage
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId, CustomerId
from frontdesk.domain.models import Customer
from frontdesk.infrastructure.channels.composite import RoutingMessaging
from frontdesk.infrastructure.events import LoggingEventPublisher
from frontdesk.infrastructure.memory import InMemoryMessaging


def _customer(channel: Channel) -> Customer:
    return Customer(CustomerId("c"), BusinessId("b"), channel, "+1")


async def test_routes_to_the_customers_channel() -> None:
    whatsapp, telegram = InMemoryMessaging(), InMemoryMessaging()
    routing = RoutingMessaging(whatsapp=whatsapp, telegram=telegram)

    await routing.send(_customer(Channel.WHATSAPP), OutboundMessage("hi"))
    await routing.send(_customer(Channel.TELEGRAM), OutboundMessage("hey"))

    assert len(whatsapp.sent) == 1
    assert len(telegram.sent) == 1


async def test_raises_when_a_channel_has_no_adapter() -> None:
    routing = RoutingMessaging(whatsapp=InMemoryMessaging())

    with pytest.raises(RuntimeError, match="telegram"):
        await routing.send(_customer(Channel.TELEGRAM), OutboundMessage("hi"))


async def test_falls_back_when_a_channel_is_not_configured() -> None:
    fallback = InMemoryMessaging()
    routing = RoutingMessaging(whatsapp=InMemoryMessaging(), fallback=fallback)

    await routing.send(_customer(Channel.TELEGRAM), OutboundMessage("hi"))

    assert len(fallback.sent) == 1


async def test_logging_event_publisher_accepts_events() -> None:
    await LoggingEventPublisher().publish(MessageReceived(BusinessId("b"), CustomerId("c"), "hi"))
