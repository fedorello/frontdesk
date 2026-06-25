"""The webhook layer: verification, signature, idempotency, and dispatch."""

import hashlib
import hmac
import json
from typing import Any

import httpx
from fastapi import FastAPI

from frontdesk.application.ports import Completion
from frontdesk.infrastructure.memory import InMemoryIdempotency
from frontdesk.interface.webhooks import WebhookConfig, create_app
from tests.application.world import BIZ_ADDR, World, build_world

CONFIG = WebhookConfig(
    whatsapp_app_secret="APP_SECRET",
    whatsapp_verify_token="VERIFY",
    telegram_secret="TG_SECRET",
    telegram_bot_address="+BOT",
)


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(b"APP_SECRET", body, hashlib.sha256).hexdigest()


def _whatsapp_payload() -> dict[str, Any]:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"display_phone_number": BIZ_ADDR},
                            "messages": [
                                {
                                    "from": "+CUST",
                                    "id": "wamid.1",
                                    "timestamp": "1782000000",
                                    "text": {"body": "hi"},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }


def _app(world: World, idempotency: InMemoryIdempotency | None = None) -> FastAPI:
    return create_app(
        assistant=world.assistant,
        idempotency=idempotency or InMemoryIdempotency(),
        config=CONFIG,
    )


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_whatsapp_verification_handshake() -> None:
    async with _client(_app(build_world([]))) as client:
        ok = await client.get(
            "/webhooks/whatsapp",
            params={"hub.mode": "subscribe", "hub.verify_token": "VERIFY", "hub.challenge": "42"},
        )
        bad = await client.get(
            "/webhooks/whatsapp",
            params={"hub.mode": "subscribe", "hub.verify_token": "WRONG", "hub.challenge": "42"},
        )

    assert (ok.status_code, ok.text) == (200, "42")
    assert bad.status_code == 403


async def test_whatsapp_dispatches_with_valid_signature() -> None:
    world = build_world([Completion("Hi there!")])
    body = json.dumps(_whatsapp_payload()).encode()

    async with _client(_app(world)) as client:
        response = await client.post(
            "/webhooks/whatsapp", content=body, headers={"x-hub-signature-256": _sign(body)}
        )

    assert response.status_code == 200
    assert world.messaging.sent[-1][1].text == "Hi there!"


async def test_whatsapp_rejects_bad_signature() -> None:
    world = build_world([Completion("Hi")])
    body = json.dumps(_whatsapp_payload()).encode()

    async with _client(_app(world)) as client:
        response = await client.post(
            "/webhooks/whatsapp", content=body, headers={"x-hub-signature-256": "sha256=nope"}
        )

    assert response.status_code == 403
    assert world.messaging.sent == []


async def test_idempotency_processes_a_repeat_once() -> None:
    world = build_world([Completion("Hi"), Completion("Hi")])
    body = json.dumps(_whatsapp_payload()).encode()
    headers = {"x-hub-signature-256": _sign(body)}

    async with _client(_app(world, InMemoryIdempotency())) as client:
        await client.post("/webhooks/whatsapp", content=body, headers=headers)
        await client.post("/webhooks/whatsapp", content=body, headers=headers)  # same id

    assert len(world.messaging.sent) == 1  # handled exactly once


async def test_telegram_checks_the_secret_token() -> None:
    payload = {
        "message": {"message_id": 1, "date": 1782000000, "chat": {"id": "+99"}, "text": "hi"}
    }
    body = json.dumps(payload).encode()

    async with _client(_app(build_world([Completion("Hi")]))) as client:
        rejected = await client.post(
            "/webhooks/telegram", content=body, headers={"x-telegram-bot-api-secret-token": "wrong"}
        )
        accepted = await client.post(
            "/webhooks/telegram",
            content=body,
            headers={"x-telegram-bot-api-secret-token": "TG_SECRET"},
        )

    assert rejected.status_code == 403
    assert accepted.status_code == 200
