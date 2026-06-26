# HTTP API

The API is a FastAPI app served by `uvicorn frontdesk.interface.app:create_production_app`
(see `make serve` / the `api` container). It exposes three surfaces: the **web
chat**, the **approvals inbox**, and the **channel webhooks**. Base URL in the local
stack is `http://localhost:8000`.

---

## Web chat

### `POST /api/chat`

Talk to the assistant synchronously (the dashboard's Chat page uses this). One
customer is created per `session`, so conversation history persists across turns.

Request:

```json
{ "text": "Can I book the earliest haircut today?", "session": "browser-uuid" }
```

Response — the reply plus the agent's reasoning/tool trace:

```json
{
  "reply": "The earliest haircut is at 09:00 UTC. Want me to book it?",
  "trace": [
    { "kind": "thought", "text": "Let me check availability." },
    { "kind": "tool", "tool": "find_availability",
      "args": { "service": "Haircut" },
      "result": "Free slots: 09:00 UTC (start=2026-06-26T09:00:00+00:00); …" }
  ]
}
```

`trace` items are either `{kind:"thought", text}` or
`{kind:"tool", tool, args, result}`.

```bash
curl -s localhost:8000/api/chat -H 'content-type: application/json' \
  -d '{"text":"What services do you have?","session":"demo"}'
```

---

## Approvals inbox

Sensitive actions the assistant flagged are held by the airlock gate and queued here
(see [ADR-0005](adr/0005-human-in-the-loop-via-airlock.md)).

### `GET /api/approvals`

```json
[
  {
    "id": "c5eaf207bc6848e4a72ae9a4757cc772",
    "summary": "Refund for web:demo (ap-1)",
    "tool": "issue_refund",
    "args": { "appointment_id": "ap-1", "amount": 25 },
    "risk": "sensitive"
  }
]
```

### `POST /api/approvals/{id}`

```json
{ "approved": true }
```

→ `{ "status": "approved" }` (or `"rejected"` when `approved` is `false`).
Returns `404` if the id isn't a pending request.

```bash
curl -s -X POST localhost:8000/api/approvals/<id> \
  -H 'content-type: application/json' -d '{"approved":true}'
```

---

## Channel webhooks

### WhatsApp — `GET /webhooks/whatsapp`

Meta's verification handshake. With `hub.mode=subscribe` and a matching
`hub.verify_token`, it echoes `hub.challenge` (HTTP 200); otherwise 403.

### WhatsApp — `POST /webhooks/whatsapp`

A Cloud API message event. The body is verified against `X-Hub-Signature-256`
(HMAC-SHA256 with `FRONTDESK_WHATSAPP_APP_SECRET`); a bad signature is **403**.
The message is normalized, de-duplicated by provider message id, and dispatched to
the assistant. Always returns **200** for accepted events.

### Telegram — `POST /webhooks/telegram`

A Bot API update. The `X-Telegram-Bot-Api-Secret-Token` header must equal
`FRONTDESK_TELEGRAM_SECRET` (else **403**); then the update is parsed and dispatched.

> Tenant resolution: the business is found from the channel + the address the
> message was sent **to** (`channel_binding`), so one deployment serves many
> businesses ([ADR-0003](adr/0003-multi-tenant-by-business.md)).

The outbound reply is sent back through the same channel's adapter — or, when no
provider token is configured, logged (so local runs work end to end without Meta /
Telegram credentials).
