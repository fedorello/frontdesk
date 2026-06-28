# ADR-0010 — Telegram update transport: webhook primary, polling fallback

## Status

Accepted (2026-06-26). Revised (2026-06-28): webhook and polling now run together, chosen
per bot by `webhook_set`, so polling is a live fallback for webhook (see Decision).

## Context

A Telegram bot receives updates one of two ways:

- **Webhook** — Telegram POSTs each update to a public HTTPS URL.
- **Long polling** — the bot calls `getUpdates` and waits.

Webhooks need a publicly reachable URL. That is impossible on `localhost` and a real
friction point for self-hosters (the failure we hit: a bot "connected" but never
received messages because `setWebhook` pointed at `localhost`, which Telegram rejects).

tovayo is open-source and meant to run on any machine — "works right after
`docker compose up`" is a requirement, not a nice-to-have. A temporary tunnel
(ngrok/cloudflared) is a workaround, not a product.

## Decision

Support **both** transports behind `FRONTDESK_TELEGRAM_MODE` (a `TelegramMode` enum,
no magic strings):

- **`polling`** (default) — a dedicated poller process (`run_telegram_poller`)
  long-polls each connected bot's `getUpdates` and dispatches to the assistant. **No
  public URL needed.** Connect runs `deleteWebhook` so `getUpdates` is allowed.
- **`webhook`** — Telegram pushes to `FRONTDESK_PUBLIC_URL`; the API's
  `/webhooks/telegram/{business}` handles it. Connect runs `setWebhook`. For production
  deployments that have a domain.

Both transports share one dispatcher, `TelegramInbound` (resolve bot + parse update →
managed-default quota → tenant-wired assistant), so the two paths can never diverge.
The poller persists its `getUpdates` offset per bot (`telegram_bot.last_update_id`,
migration 0005) so a restart never replays updates, and it advances the offset even
when an update fails to keep one poison message from wedging the loop.

**Webhook primary, polling fallback (revision).** The two transports are no longer
mutually exclusive at the process level — they are chosen **per bot** by the single
`telegram_bot.webhook_set` flag:

- In `webhook` mode, connect calls `setWebhook`. On success the bot is `webhook_set =
  true` and the API's endpoint delivers it. If `setWebhook` fails (e.g. a transient
  Telegram error), the bot stays `webhook_set = false`.
- The poller polls only `webhook_set = false` bots (`list_polling`). So any bot without
  a working webhook — a failed registration, or any bot in `polling` mode — is still
  served by the poller. **Polling is the live fallback for webhook**, not an
  either/or. A bot is never handled by both (the flag partitions them).

## Consequences

- Self-host and local dev work with **zero networking setup** (polling default) — no
  tunnel, no public URL.
- Webhook avoids polling overhead and scales better for production — opt in by setting
  the mode and a public URL.
- Polling and webhook must not both be active for the **same** bot (Telegram rejects
  `getUpdates` while a webhook is set). `webhook_set` partitions them: the poller skips
  webhook bots (`list_polling`), and connect deletes the webhook in polling mode — so
  the two can't collide on one bot, yet both processes run so polling can cover any bot
  whose webhook isn't (or isn't yet) set.

## Known follow-up

Sensitive-action approvals (airlock) are held in an **in-memory** queue per process. A
refund flagged in a Telegram conversation handled by the poller process lands in the
poller's queue, not the API's `/approvals`. Making the approval queue **DB-backed** (a
shared store, behind an `ApprovalStore` port) is tracked so the dashboard sees
approvals raised by every process. Until then, the dashboard reflects the API process's
queue; the gating itself is correct in every process (nothing sensitive auto-executes).
