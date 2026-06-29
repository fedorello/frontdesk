"""The Telegram polling worker process: long-poll the fallback bots and dispatch updates.

Polls only bots without a registered webhook (`list_polling`); webhook bots are delivered
by the API. So this process is the polling fallback and is safe to run alongside webhooks —
the two never handle the same bot. See ADR-0010.
"""

import asyncio
import signal

import httpx

from frontdesk.core.settings import Settings
from frontdesk.infrastructure.airlock_gate import AirlockApprovalGate
from frontdesk.infrastructure.db import create_engine, make_session_factory
from frontdesk.infrastructure.logging_setup import configure_logging
from frontdesk.infrastructure.postgres.adapters import (
    SqlApprovalStore,
    SqlLlmConfigRepository,
    SqlTelegramBotRepository,
    SqlUsageStore,
)
from frontdesk.infrastructure.system import SystemRandom, UuidIdGenerator
from frontdesk.interface.app import (
    build_assistant_deps,
    build_cipher,
    build_clock,
    build_owner_linking,
)
from frontdesk.interface.telegram_inbound import TelegramInbound
from frontdesk.interface.telegram_poller import TelegramPoller

# The HTTP client timeout must comfortably exceed Telegram's long-poll hold time.
_POLL_CLIENT_BUFFER_SECONDS = 10


async def run() -> None:
    settings = Settings()
    configure_logging(settings.log_level, settings.log_file)
    engine = create_engine(settings.database_url)
    sessions = make_session_factory(engine)
    cipher = build_cipher(settings)
    client = httpx.AsyncClient(
        timeout=settings.telegram_poll_timeout_seconds + _POLL_CLIENT_BUFFER_SECONDS
    )
    ids = UuidIdGenerator()
    clock = build_clock(settings)
    deps = build_assistant_deps(
        settings,
        sessions,
        ids,
        clock,
        client,
        AirlockApprovalGate(SqlApprovalStore(sessions)),  # shared DB queue (visible in the API)
    )
    inbound = TelegramInbound(
        deps,
        SqlLlmConfigRepository(sessions, cipher),
        SqlUsageStore(sessions),
        settings,
        client,
        SystemRandom(),
        build_owner_linking(settings, sessions, ids, clock, client),
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
