"""The reminder worker process: poll Postgres for due reminders and send them."""

import asyncio
import signal

import httpx

from frontdesk.application.worker import SendDueReminders
from frontdesk.core.settings import Settings
from frontdesk.infrastructure.db import create_engine, make_session_factory
from frontdesk.infrastructure.postgres.adapters import (
    SqlAppointmentRepository,
    SqlCustomerRepository,
    SqlReminderStore,
    SqlServiceRepository,
    SqlTelegramBotRepository,
)
from frontdesk.infrastructure.system import UuidIdGenerator
from frontdesk.interface.app import build_cipher, build_clock
from frontdesk.interface.tenancy import TenantTelegramMessaging
from frontdesk.interface.worker import ReminderWorker


async def run() -> None:
    settings = Settings()
    engine = create_engine(settings.database_url)
    sessions = make_session_factory(engine)
    ids = UuidIdGenerator()
    client = httpx.AsyncClient(timeout=30)
    telegram_bots = SqlTelegramBotRepository(sessions, build_cipher(settings))
    send = SendDueReminders(
        SqlReminderStore(sessions),
        SqlAppointmentRepository(sessions),
        SqlCustomerRepository(sessions, ids),
        SqlServiceRepository(sessions),
        TenantTelegramMessaging(telegram_bots, client),  # each reminder via its business's bot
    )
    worker = ReminderWorker(send, build_clock(settings))

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    await worker.run_until(stop)
    await client.aclose()
    await engine.dispose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
