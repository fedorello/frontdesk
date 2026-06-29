"""The owner Telegram API: status, confirm (with error mapping), toggle, unlink, and the guard."""

from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI, HTTPException

from frontdesk.application.owner_linking import OwnerLinking
from frontdesk.domain.ids import BusinessId, LinkCode
from frontdesk.domain.models import Business
from frontdesk.domain.notifications import TelegramLinkCode
from frontdesk.infrastructure.memory import (
    InMemoryBusinessRepository,
    InMemoryOwnerNotificationSender,
    InMemoryOwnerTelegramLinkRepository,
    InMemoryTelegramLinkCodeStore,
)
from frontdesk.infrastructure.system import FixedClock, SequentialIdGenerator
from frontdesk.interface.owner_telegram import Guard, build_owner_telegram_router

NOW = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
BIZ = "biz"
_URL = f"/api/businesses/{BIZ}/telegram-owner"


class _World:
    def __init__(self) -> None:
        self.codes = InMemoryTelegramLinkCodeStore()
        self.links = InMemoryOwnerTelegramLinkRepository()
        self.linking = OwnerLinking(
            self.codes,
            self.links,
            InMemoryBusinessRepository([Business(BusinessId(BIZ), "S", "UTC")], {}),
            InMemoryOwnerNotificationSender(),
            SequentialIdGenerator("code"),
            FixedClock(NOW),
            "http://app",
        )

    def client(self, guard: Guard = None) -> httpx.AsyncClient:
        app = FastAPI()
        app.include_router(build_owner_telegram_router(self.links, self.linking, guard))
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_status_reports_unlinked_then_linked() -> None:
    world = _World()
    await world.linking.start(BusinessId(BIZ), "chat-1", "Owner")  # issues code-1
    async with world.client() as client:
        assert (await client.get(_URL)).json() == {
            "linked": False,
            "telegram_name": None,
            "notifications_enabled": False,
        }
        confirmed = await client.post(f"{_URL}/confirm", json={"code": "code-1"})
        assert confirmed.status_code == 200
        assert confirmed.json()["telegram_name"] == "Owner"
        assert (await client.get(_URL)).json()["linked"] is True


async def test_confirm_maps_problems_to_status_codes() -> None:
    world = _World()
    await world.codes.issue(
        TelegramLinkCode(LinkCode("old"), BusinessId(BIZ), "c", "O", NOW - timedelta(minutes=1))
    )
    async with world.client() as client:
        unknown = await client.post(f"{_URL}/confirm", json={"code": "nope"})
        expired = await client.post(f"{_URL}/confirm", json={"code": "old"})
    assert unknown.status_code == 404  # not_found
    assert expired.status_code == 410  # expired (gone)


async def test_toggle_notifications_and_unlink() -> None:
    world = _World()
    await world.linking.start(BusinessId(BIZ), "chat-1", "Owner")
    async with world.client() as client:
        await client.post(f"{_URL}/confirm", json={"code": "code-1"})
        off = await client.put(f"{_URL}/notifications", json={"enabled": False})
        assert off.json()["notifications_enabled"] is False
        await client.delete(_URL)
        assert (await client.get(_URL)).json()["linked"] is False


async def test_toggle_when_unlinked_is_404() -> None:
    async with _World().client() as client:
        assert (
            await client.put(f"{_URL}/notifications", json={"enabled": True})
        ).status_code == 404


async def test_guard_rejects_unauthorized_callers() -> None:
    async def reject(business_id: str = "") -> None:
        raise HTTPException(403, "not your business")

    async with _World().client(guard=reject) as client:
        assert (await client.get(_URL)).status_code == 403
