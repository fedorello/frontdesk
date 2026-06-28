"""The whole onboarding backend flow: sign up -> configure -> connect Telegram.

This exercises the real routers + owner guard end to end (Telegram mocked at the
network boundary). It runs with an EMPTY telegram_api_base — the exact misconfig that
crashed connect with a 500 — to prove the flow now completes.
"""

import httpx
from fastapi import FastAPI

from frontdesk.core.settings import Settings
from frontdesk.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryBusinessRepository,
    InMemoryChannelBindingRepository,
    InMemoryLlmConfigRepository,
    InMemoryResourceRepository,
    InMemoryServiceRepository,
    InMemoryTelegramBotRepository,
)
from frontdesk.infrastructure.system import SequentialIdGenerator
from frontdesk.interface.auth import build_auth_router, make_owner_guard
from frontdesk.interface.business_config import build_llm_config_router
from frontdesk.interface.config_api import build_config_router
from frontdesk.interface.telegram_connect import build_telegram_connect_router

SETTINGS = Settings(secret_key="test-secret", telegram_api_base="")  # empty == the bug
WORKING_HOURS = [{"weekday": 0, "opens": "09:00:00", "closes": "17:00:00"}]


def _telegram_mock() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getMe" in request.url.path:
            return httpx.Response(
                200, json={"ok": True, "result": {"id": 1, "username": "demo_bot"}}
            )
        return httpx.Response(200, json={"ok": True})  # setWebhook / deleteWebhook

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _app(client: httpx.AsyncClient) -> FastAPI:
    accounts = InMemoryAccountRepository()
    businesses = InMemoryBusinessRepository([], {})
    guard = make_owner_guard(accounts, SETTINGS.secret_key)
    app = FastAPI()
    app.include_router(
        build_auth_router(accounts, businesses, SequentialIdGenerator("id"), SETTINGS)
    )
    app.include_router(
        build_config_router(
            businesses, InMemoryServiceRepository([]), InMemoryResourceRepository(), guard
        )
    )
    app.include_router(build_llm_config_router(InMemoryLlmConfigRepository(), guard))
    app.include_router(
        build_telegram_connect_router(
            InMemoryTelegramBotRepository(),
            InMemoryChannelBindingRepository(businesses),
            SETTINGS,
            client,
            guard,
        )
    )
    return app


async def test_full_onboarding_completes() -> None:
    transport = httpx.ASGITransport(app=_app(_telegram_mock()))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as web:
        signup = await web.post(
            "/api/signup",
            json={
                "email": "owner@x.com",
                "password": "test-pw-123",
                "business_name": "Bloom Studio",
            },
        )
        assert signup.status_code == 200
        token = signup.json()["token"]
        business_id = signup.json()["business_id"]
        auth = {"authorization": f"Bearer {token}"}

        resource = await web.put(
            f"/api/businesses/{business_id}/resources/main",
            headers=auth,
            json={"name": "Main", "working_hours": WORKING_HOURS},
        )
        service = await web.put(
            f"/api/businesses/{business_id}/services/svc1",
            headers=auth,
            json={"name": "Haircut", "duration_minutes": 60, "resource_ids": ["main"]},
        )
        ai = await web.put(
            f"/api/businesses/{business_id}/llm", headers=auth, json={"mode": "default"}
        )
        assert (resource.status_code, service.status_code, ai.status_code) == (200, 200, 200)

        # The step that crashed before — now completes (no 500), bot validated.
        connect = await web.post(
            f"/api/businesses/{business_id}/telegram/connect",
            headers=auth,
            json={"bot_token": "123:REAL-LOOKING-TOKEN"},
        )
        assert connect.status_code == 200
        assert connect.json() == {"connected": True, "username": "demo_bot"}


async def test_get_me_survives_a_transport_error() -> None:
    from frontdesk.infrastructure.channels.telegram import telegram_get_me

    # An empty base yields a protocol-less URL; getMe must return None, not raise.
    async with httpx.AsyncClient() as client:
        assert await telegram_get_me("123:TOK", client, base="") is None
