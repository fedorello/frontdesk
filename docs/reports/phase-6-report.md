# Phase 6 — Channels & webhooks — report

**Status:** Done (2026-06-25)

## What was built

- `infrastructure/channels/whatsapp.py` / `telegram.py` — the outbound
  `MessagingPort` adapters over httpx (WhatsApp Cloud API with interactive reply
  buttons; Telegram Bot API with a reply keyboard), plus inbound payload parsers
  that normalize each provider's webhook body to `InboundMessage` (returning
  `None` for non-message events).
- `application/ports.py` — an `Idempotency` port; `infrastructure/memory.py` — an
  in-memory fake.
- `interface/webhooks.py` — the FastAPI webhook layer: the WhatsApp verification
  handshake (`GET`), and `POST` routes that **verify the signature/secret**
  (WhatsApp `X-Hub-Signature-256` HMAC; Telegram secret-token header), drop
  duplicates by `provider_message_id`, normalize, and dispatch to the assistant.

## Verification

- **The gate** (`make check`): ruff clean, import-linter 3/3, mypy `--strict`
  green over 52 files, pytest **89 passed, 97.5 %**.
- **Recorded-response tests** (httpx `MockTransport`): the send adapters build the
  correct request (URL, auth, body, buttons); the parsers normalize real webhook
  payloads.
- **Webhook tests** (real ASGI via httpx `ASGITransport`): the verification
  handshake, a **valid signature dispatches and a reply is sent**, a **bad
  signature is rejected (403)**, **idempotency** processes a repeat exactly once,
  and the Telegram secret token is enforced.
- **Real run** (`logs/phase-6/webhook-run.log`): a **signed WhatsApp webhook**
  carrying "Can I get a haircut at 3pm?" drove the whole stack — verify → parse →
  the assistant tool loop (`find_availability` → `book`) → a real appointment
  (ap-1, 15:00 UTC) → the reply — over the real FastAPI/ASGI HTTP cycle.

## Definition of Done

- [x] WhatsApp + Telegram adapters and webhooks (signature verify, idempotency, normalize).
- [x] Tenant resolution from the channel binding (the assistant resolves the business).
- [x] Inbound → reply runs end-to-end; signature and idempotency tested; messaging adapters tested.
