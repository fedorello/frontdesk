"""The reminder worker: poll for due reminders on an interval until stopped."""

import asyncio
import contextlib
import logging

from frontdesk.application.ports import Clock
from frontdesk.application.worker import SendDueReminders

DEFAULT_INTERVAL_SECONDS = 60.0

_logger = logging.getLogger("frontdesk.worker")


class ReminderWorker:
    """Drives ``SendDueReminders`` on a fixed cadence."""

    def __init__(
        self,
        send: SendDueReminders,
        clock: Clock,
        *,
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    ) -> None:
        self._send = send
        self._clock = clock
        self._interval = interval_seconds

    async def tick(self) -> int:
        """One pass: send everything currently due. Returns how many were sent."""
        return await self._send(self._clock.now())

    async def run_until(self, stop: asyncio.Event) -> None:
        """Tick every ``interval_seconds`` until ``stop`` is set."""
        while not stop.is_set():
            try:
                await self.tick()
            except Exception:
                # A failed pass (database blip, a bug in one reminder) must not kill the
                # process: a crash-looping container sends nothing at all. Log it and try
                # again on the next tick.
                _logger.exception("reminder_tick_failed")
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=self._interval)
