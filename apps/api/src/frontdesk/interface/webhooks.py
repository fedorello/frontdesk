"""FastAPI webhook layer: verify, normalize, dedupe, dispatch to the assistant."""

import hashlib
import hmac
import json
from dataclasses import dataclass

from fastapi import FastAPI, Query, Request, Response

from frontdesk.application.assistant import Assistant
from frontdesk.application.ports import Idempotency
from frontdesk.infrastructure.channels.telegram import parse_telegram_inbound
from frontdesk.infrastructure.channels.whatsapp import parse_whatsapp_inbound


@dataclass(frozen=True, slots=True)
class WebhookConfig:
    whatsapp_app_secret: str
    whatsapp_verify_token: str
    telegram_secret: str
    telegram_bot_address: str


def _valid_whatsapp_signature(secret: str, body: bytes, header: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


def create_app(*, assistant: Assistant, idempotency: Idempotency, config: WebhookConfig) -> FastAPI:
    app = FastAPI()

    @app.get("/webhooks/whatsapp")
    async def verify_whatsapp(
        mode: str = Query("", alias="hub.mode"),
        token: str = Query("", alias="hub.verify_token"),
        challenge: str = Query("", alias="hub.challenge"),
    ) -> Response:
        if mode == "subscribe" and token == config.whatsapp_verify_token:
            return Response(challenge)
        return Response(status_code=403)

    @app.post("/webhooks/whatsapp")
    async def whatsapp(request: Request) -> Response:
        body = await request.body()
        signature = request.headers.get("x-hub-signature-256", "")
        if not _valid_whatsapp_signature(config.whatsapp_app_secret, body, signature):
            return Response(status_code=403)
        inbound = parse_whatsapp_inbound(json.loads(body))
        if inbound is not None and not await idempotency.seen(inbound.provider_message_id):
            await assistant.handle(inbound)
        return Response(status_code=200)

    @app.post("/webhooks/telegram")
    async def telegram(request: Request) -> Response:
        if request.headers.get("x-telegram-bot-api-secret-token") != config.telegram_secret:
            return Response(status_code=403)
        inbound = parse_telegram_inbound(
            json.loads(await request.body()), bot_address=config.telegram_bot_address
        )
        if inbound is not None and not await idempotency.seen(inbound.provider_message_id):
            await assistant.handle(inbound)
        return Response(status_code=200)

    return app
