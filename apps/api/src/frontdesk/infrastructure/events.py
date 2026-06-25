"""A simple event publisher for running the product (logs domain events).

The live dashboard stream (Redis pub/sub → SSE) plugs in behind the same port;
this keeps the server runnable without it.
"""

import logging

from frontdesk.application.ports import DomainEvent

_logger = logging.getLogger("frontdesk.events")


class LoggingEventPublisher:
    async def publish(self, event: DomainEvent) -> None:
        _logger.info("event: %s", type(event).__name__)
