# M3 — Telegram self-serve connect — report

**Status:** Code-complete + verified (2026-06-26) · [SaaS plan, Phase C](../plans/saas-telegram-plan.md)

An owner connects their own bot in one step: paste a BotFather token → the bot goes
live.

## What was built

- **Telegram admin** (`channels/telegram.py`): `telegram_get_me` (validate a token),
  `telegram_set_webhook` (register with a secret), `telegram_delete_webhook`.
- **`ChannelBindingRepository`** (port, fake, SQL): write the `(channel, address) →
  business` binding so inbound messages resolve to the right business.
- **Connect API** (`telegram_connect.py`):
  - `POST …/telegram/connect` — validates the token (`getMe`), generates a webhook
    secret, **binds** the bot to the business, stores the token **encrypted**, and
    registers the webhook (`setWebhook` at `/{public_url}/webhooks/telegram/{id}`).
  - `POST …/telegram/disconnect` — `deleteWebhook` + unbind.
  - `GET …/telegram` — connection status (the token is never returned).

## Verification

- **Gate** (`make check`): ruff, mypy `--strict`, import-linter 3/3, **133 unit
  tests**, 97.7 %.
- **Flow test** (`test_telegram_connect`, mocked Telegram): a valid token connects
  (200, registers the webhook at the per-business path, binds the bot so
  `for_channel` resolves it); an invalid token → 422; status reports connected;
  disconnect removes the binding.
- **Real Telegram** (`logs/m3/real-validate.log`): `getMe` with a fake token hits the
  live `api.telegram.org` and is **correctly rejected** (returns `None`) — the
  validation path is real, not mocked.

## What the full end-to-end needs (honest)

The DoD's “a real bot answers and books” requires two things only the deployment can
supply: a **real BotFather token** and a **publicly reachable URL** (Telegram must be
able to POST to the webhook — `localhost` won't do; a tunnel or a deployed instance
is needed). The connect code, the webhook routing (M1), and the assistant are all in
place and tested; wiring a real bot is a deploy step, not new code.

## Definition of Done

- [x] Connect validates a token, stores it encrypted, binds the bot, and registers
      the webhook; disconnect reverses it. (Tested; validation proven against real
      Telegram.)
- [ ] A real BotFather token + public URL make the bot answer and book live — a
      deployment step (token + tunnel) pending.
