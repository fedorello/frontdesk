"""Telegram connect validates the token, registers the webhook, binds, disconnects."""

import json

import httpx
from fastapi import FastAPI

from frontdesk.core.settings import Settings
from frontdesk.domain.enums import Channel
from frontdesk.domain.ids import BusinessId
from frontdesk.domain.models import Business
from frontdesk.infrastructure.memory import (
    InMemoryBusinessRepository,
    InMemoryChannelBindingRepository,
    InMemoryTelegramBotRepository,
)
from frontdesk.interface.telegram_connect import build_telegram_connect_router

SETTINGS = Settings(public_url="https://example.com")


async def test_connect_flow() -> None:
    webhook_urls: list[str] = []

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
            webhook_urls.append(json.loads(request.content)["url"])
            return httpx.Response(200, json={"ok": True})
        if "deleteWebhook" in url:
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    business_repo = InMemoryBusinessRepository([Business(BusinessId("ana"), "Ana", "UTC")], {})
    bindings = InMemoryChannelBindingRepository(business_repo)
    bots = InMemoryTelegramBotRepository()

    app = FastAPI()
    app.include_router(build_telegram_connect_router(bots, bindings, SETTINGS, client))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as web:
        ok = await web.post("/api/businesses/ana/telegram/connect", json={"bot_token": "111:GOOD"})
        assert ok.status_code == 200
        assert ok.json() == {"connected": True, "username": "ana_bot"}

        bad = await web.post("/api/businesses/ana/telegram/connect", json={"bot_token": "222:BAD"})
        assert bad.status_code == 422  # invalid token rejected

        st = (await web.get("/api/businesses/ana/telegram")).json()
        assert st == {"connected": True, "username": "ana_bot"}

        health = (await web.get("/api/businesses/ana/telegram/health")).json()
        assert health == {"connected": True, "alive": True, "username": "ana_bot"}  # getMe live

        disc = await web.post("/api/businesses/ana/telegram/disconnect")
        assert disc.json() == {"disconnected": True}

    # the webhook was registered at the per-business path
    assert webhook_urls == ["https://example.com/webhooks/telegram/ana"]
    # the bot is stored (token write-only) and the inbound binding resolves the business
    stored = await bots.get(BusinessId("ana"))
    assert stored is not None
    assert stored.bot_token == "111:GOOD"
    # after disconnect the binding is gone
    assert await business_repo.for_channel(Channel.TELEGRAM, "ana_bot") is None
