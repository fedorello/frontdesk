"""The Telegram polling worker process: long-poll connected bots and dispatch updates.

Runs only when telegram_mode == "polling" (webhook mode delivers via the API, and
running both would conflict on Telegram's side). See ADR-0010.
"""

import asyncio
import logging
import signal

import httpx

from frontdesk.core.settings import Settings, TelegramMode
from frontdesk.infrastructure.airlock_gate import AirlockApprovalGate, PendingApprovals
from frontdesk.infrastructure.db import create_engine, make_session_factory
from frontdesk.infrastructure.logging_setup import configure_logging
from frontdesk.infrastructure.postgres.adapters import (
    SqlLlmConfigRepository,
    SqlTelegramBotRepository,
    SqlUsageStore,
)
from frontdesk.infrastructure.system import SystemRandom, UuidIdGenerator
from frontdesk.interface.app import build_assistant_deps, build_cipher, build_clock
from frontdesk.interface.telegram_inbound import TelegramInbound
from frontdesk.interface.telegram_poller import TelegramPoller

_logger = logging.getLogger("frontdesk.telegram_poller")
# The HTTP client timeout must comfortably exceed Telegram's long-poll hold time.
_POLL_CLIENT_BUFFER_SECONDS = 10


async def run() -> None:
    settings = Settings()
    configure_logging(settings.log_level, settings.log_file)
    if settings.telegram_mode != TelegramMode.POLLING:
        _logger.info("telegram_mode=%s — poller not needed, exiting", settings.telegram_mode.value)
        return

    engine = create_engine(settings.database_url)
    sessions = make_session_factory(engine)
    cipher = build_cipher(settings)
    client = httpx.AsyncClient(
        timeout=settings.telegram_poll_timeout_seconds + _POLL_CLIENT_BUFFER_SECONDS
    )
    deps = build_assistant_deps(
        settings,
        sessions,
        UuidIdGenerator(),
        build_clock(settings),
        client,
        AirlockApprovalGate(PendingApprovals()),
    )
    inbound = TelegramInbound(
        deps,
        SqlLlmConfigRepository(sessions, cipher),
        SqlUsageStore(sessions),
        settings,
        client,
        SystemRandom(),
    )
    poller = TelegramPoller(SqlTelegramBotRepository(sessions, cipher), inbound, client, settings)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    await poller.run(stop)
    await client.aclose()
    await engine.dispose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
