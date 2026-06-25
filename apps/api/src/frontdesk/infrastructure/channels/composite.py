"""Messaging that routes each reply to the customer's channel.

`LoggingMessaging` is the local fallback: when a channel has no real adapter
configured (no token), the reply is logged instead of crashing — so the stack
runs end-to-end locally without Meta/Telegram credentials.
"""

import logging

from frontdesk.application.ports import MessagingPort, OutboundMessage
from frontdesk.domain.enums import Channel
from frontdesk.domain.models import Customer

_logger = logging.getLogger("frontdesk.messaging")


class LoggingMessaging:
    async def send(self, customer: Customer, message: OutboundMessage) -> None:
        _logger.info("reply → %s: %s", customer.channel_address, message.text)


class CapturingMessaging:
    """Records replies instead of sending — for the synchronous web chat."""

    def __init__(self) -> None:
        self.replies: list[str] = []

    async def send(self, customer: Customer, message: OutboundMessage) -> None:
        self.replies.append(message.text)


class RoutingMessaging:
    """Dispatches ``send`` to the WhatsApp or Telegram adapter by channel."""

    def __init__(
        self,
        *,
        whatsapp: MessagingPort | None = None,
        telegram: MessagingPort | None = None,
        fallback: MessagingPort | None = None,
    ) -> None:
        self._by_channel: dict[Channel, MessagingPort] = {}
        if whatsapp is not None:
            self._by_channel[Channel.WHATSAPP] = whatsapp
        if telegram is not None:
            self._by_channel[Channel.TELEGRAM] = telegram
        self._fallback = fallback

    async def send(self, customer: Customer, message: OutboundMessage) -> None:
        adapter = self._by_channel.get(customer.channel) or self._fallback
        if adapter is None:
            raise RuntimeError(f"No messaging adapter configured for {customer.channel.value}")
        await adapter.send(customer, message)
