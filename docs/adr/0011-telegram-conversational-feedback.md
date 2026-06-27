# ADR-0011 — Telegram conversational feedback: placeholder + busy lines

## Status

Accepted (2026-06-27)

## Context

An LLM reply takes a few seconds. With no feedback the chat looks frozen, and an
impatient customer fires off another message — which the bot would otherwise answer out
of order or pile up behind the first.

## Decision

- **Placeholder.** The moment a message arrives, send a short random "one moment…" line
  and remember its message_id; once the real reply is sent, delete the placeholder.
- **Busy.** Keep an in-memory set of customers currently being handled
  (`"business:chat"`). A message that arrives while that customer is still mid-answer
  gets a random "still on your previous message" line instead of being processed.
- **Concurrent dispatch.** The poller now dispatches each update as a background task and
  advances its offset immediately, so a follow-up message can actually arrive (and hit
  the busy path) while the first is still being answered.
- **Localized, injected randomness.** ~50 WAIT and ~50 BUSY phrases per locale
  (en/es/ru/zh) in `telegram_phrases.py`; the locale comes from the Telegram
  `language_code`, and a phrase is picked via an injected `Random` (a `FixedRandom`
  makes tests deterministic).

## Consequences

- The placeholder is deleted right after the reply is sent (end state: just the reply).
  Deletion is best-effort — a failure is logged, not raised.
- The busy set is **per process**. With a single poller (the default) it is
  authoritative. If pollers are ever scaled horizontally, a follow-up could land on a
  different process that doesn't see the busy state — acceptable for now; a shared
  (Redis) lock would fix it.
- Offset advances at dispatch time, so a crash mid-dispatch loses that one message
  (it won't be re-fetched). This is the cost of concurrent handling; the bot's customer
  can resend, and `restart: unless-stopped` brings the worker back.
