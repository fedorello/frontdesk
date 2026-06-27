"""The Telegram polling transport: long-poll each connected bot, dispatch updates.

Used when telegram_mode == "polling" — the bot pulls updates from Telegram, so no
public URL is needed (ideal for self-hosting and local development). See ADR-0010.
"""

import asyncio
import logging
from typing import Any

import httpx

from frontdesk.application.ports import TelegramBotConfig, TelegramBotRepository
from frontdesk.core.settings import Settings
from frontdesk.infrastructure.channels.telegram import parse_telegram_inbound, telegram_get_updates
from frontdesk.interface.telegram_inbound import TelegramInbound

_logger = logging.getLogger("frontdesk.telegram_poller")


class TelegramPoller:
    """Long-polls every connected bot's getUpdates and runs each message through the assistant."""

    def __init__(
        self,
        bots: TelegramBotRepository,
        inbound: TelegramInbound,
        client: httpx.AsyncClient,
        settings: Settings,
    ) -> None:
        self._bots = bots
        self._inbound = inbound
        self._client = client
        self._base = settings.telegram_api_base
        self._poll_timeout = settings.telegram_poll_timeout_seconds
        self._idle_seconds = settings.telegram_idle_poll_seconds

    async def run(self, stop: asyncio.Event) -> None:
        """Poll all connected bots until `stop` is set, surviving transient failures."""
        _logger.info("telegram poller started")
        while not stop.is_set():
            try:
                await self._poll_round()
            except Exception as exc:
                # Broad on purpose: a DB/network blip (e.g. Postgres restarting, "in
                # recovery") must not kill the worker. Log, back off, and retry.
                _logger.warning("telegram poll round failed, backing off: %s", exc)
                await asyncio.sleep(self._idle_seconds)
        _logger.info("telegram poller stopped")

    async def _poll_round(self) -> None:
        bots = await self._bots.list_connected()
        if not bots:
            await asyncio.sleep(self._idle_seconds)  # nothing to poll yet
            return
        await asyncio.gather(*(self._poll_bot(bot) for bot in bots))

    async def _poll_bot(self, bot: TelegramBotConfig) -> None:
        updates = await telegram_get_updates(
            bot.bot_token,
            self._client,
            offset=bot.last_update_id + 1,
            timeout=self._poll_timeout,
            base=self._base,
        )
        for update in updates:
            await self._handle_update(bot, update)

    async def _handle_update(self, bot: TelegramBotConfig, update: dict[str, Any]) -> None:
        message = parse_telegram_inbound(update, bot_address=bot.username)
        try:
            if message is not None:
                await self._inbound.handle(bot, message)
        except Exception as exc:
            _logger.warning("telegram update failed business=%s: %s", bot.business_id, exc)
        # Advance the cursor regardless, so a poison update is skipped, not retried forever.
        await self._bots.set_offset(bot.business_id, int(update["update_id"]))
