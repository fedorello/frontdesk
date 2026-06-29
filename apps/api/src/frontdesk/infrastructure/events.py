"""Event publishing for running the product.

``DispatchingEventPublisher`` fans a published event out to a list of listeners (logging,
owner notifications, ...), isolating each one's failures so a side effect can never break the
action that produced the event. The live dashboard stream (Redis pub/sub → SSE) plugs in as
another listener behind the same ports.
"""

import logging
from collections.abc import Sequence

from frontdesk.application.ports import DomainEvent, EventListener

_logger = logging.getLogger("frontdesk.events")


class LoggingEventPublisher:
    async def publish(self, event: DomainEvent) -> None:
        _logger.info("event: %s", type(event).__name__)


class LoggingEventListener:
    """The default observability listener: records every event."""

    async def on_event(self, event: DomainEvent) -> None:
        _logger.info("event: %s", type(event).__name__)


class DispatchingEventPublisher:
    """Publishes by notifying each listener; one listener's failure never affects the others."""

    def __init__(self, listeners: Sequence[EventListener]) -> None:
        self._listeners = tuple(listeners)

    async def publish(self, event: DomainEvent) -> None:
        for listener in self._listeners:
            try:
                await listener.on_event(event)
            except Exception as error:
                # Isolation boundary: side effects are best-effort and run after the action has
                # already committed, so a failing listener is logged, not propagated (§8.3/§8.7).
                _logger.warning("event listener failed: %s on %s", error, type(event).__name__)
