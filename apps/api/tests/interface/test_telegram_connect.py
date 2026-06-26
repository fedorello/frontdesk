"""Telegram connect — both transports: polling (deleteWebhook) and webhook (setWebhook)."""

import json
from collections.abc import Callable

import httpx
from fastapi import FastAPI

from frontdesk.core.settings import Settings, TelegramMode
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId
from frontdesk.domain.models import Business
from frontdesk.infrastructure.memory import (
    InMemoryBusinessRepository,
    InMemoryChannelBindingRepository,
    InMemoryTelegramBotRepository,
)
from frontdesk.interface.telegram_connect import build_telegram_connect_router


def _handler(
    calls: dict[str, list[str]],
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "getMe" in url:
            token = url.split("/bot")[1].split("/")[0]
            if "BAD" in token:
                return httpx.Response(200, json={"ok": False})
            return httpx.Response(
                200, json={"ok": True, "result": {"id": 1, "username": "ana_bot"}}
            )
        if "setWebhook" in url:
            calls.setdefault("setWebhook", []).append(json.loads(request.content)["url"])
            return httpx.Response(200, json={"ok": True})
        if "deleteWebhook" in url:
            calls.setdefault("deleteWebhook", []).append(url)
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    return handler


def _app(
    settings: Settings, calls: dict[str, list[str]]
) -> tuple[FastAPI, InMemoryTelegramBotRepository, InMemoryBusinessRepository]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler(calls)))
    business_repo = InMemoryBusinessRepository([Business(BusinessId("ana"), "Ana", "UTC")], {})
    bots = InMemoryTelegramBotRepository()
    app = FastAPI()
    app.include_router(
        build_telegram_connect_router(
            bots, InMemoryChannelBindingRepository(business_repo), settings, client
        )
    )
    return app, bots, business_repo


async def test_connect_polling_deletes_webhook_and_connects() -> None:
    calls: dict[str, list[str]] = {}
    app, bots, business_repo = _app(Settings(), calls)  # default mode == polling
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as web:
        ok = await web.post("/api/businesses/ana/telegram/connect", json={"bot_token": "111:GOOD"})
        assert ok.status_code == 200
        assert ok.json() == {"connected": True, "username": "ana_bot"}  # connected once stored

        bad = await web.post("/api/businesses/ana/telegram/connect", json={"bot_token": "222:BAD"})
        assert bad.status_code == 422  # invalid token rejected

        st = (await web.get("/api/businesses/ana/telegram")).json()
        assert st == {"connected": True, "username": "ana_bot"}

        health = (await web.get("/api/businesses/ana/telegram/health")).json()
        assert health == {"connected": True, "alive": True, "username": "ana_bot"}

        disc = await web.post("/api/businesses/ana/telegram/disconnect")
        assert disc.json() == {"disconnected": True}

    assert "setWebhook" not in calls  # polling never registers a webhook
    assert calls.get("deleteWebhook")  # it clears any existing webhook so getUpdates works
    stored = await bots.get(BusinessId("ana"))
    assert stored is not None
    assert stored.bot_token == "111:GOOD"  # write-only, stored decrypted back
    assert await business_repo.for_channel(Channel.TELEGRAM, "ana_bot") is None  # after disconnect


async def test_connect_webhook_registers_the_webhook() -> None:
    calls: dict[str, list[str]] = {}
    settings = Settings(public_url="https://example.com", telegram_mode=TelegramMode.WEBHOOK)
    app, _bots, _business_repo = _app(settings, calls)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as web:
        ok = await web.post("/api/businesses/ana/telegram/connect", json={"bot_token": "111:GOOD"})
        assert ok.json() == {"connected": True, "username": "ana_bot"}

    assert calls["setWebhook"] == ["https://example.com/webhooks/telegram/ana"]  # public path
