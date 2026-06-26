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
- **Full live round-trip** (`logs/m3/live-mock-run.log`): with
  `FRONTDESK_TELEGRAM_API_BASE` pointed at a **local Telegram stand-in**, the whole
  pipeline ran through the Docker stack: sign up → configure → **connect** (real
  `getMe` + `setWebhook`, secret captured) → **bot-health** alive → a customer Telegram
  update hits the secret-verified webhook → the assistant **books** → **the reply is
  delivered to the bot** (`sendMessage`: “You're all set! 🎉 Haircut, 09:00 UTC,
  Reference …”) → the booking is in Postgres. This proves **outbound delivery**, which
  the fake-token run couldn't (it 500'd on send).

## What the literal "real bot" needs (honest)

The only difference between the live round-trip above and a production bot is the
Telegram **server**: swap the local stand-in for `api.telegram.org` by leaving
`FRONTDESK_TELEGRAM_API_BASE` at its default, and supply a **real BotFather token** +
a **public URL** (Telegram must POST to the webhook — `localhost` won't do). **No code
changes** — the entire pipeline is already exercised end to end.

## Reproduce the live round-trip

1. `python apps/api/scripts/mock_telegram.py 8081 /tmp/mock-telegram.log` (host).
2. Set `FRONTDESK_TELEGRAM_API_BASE=http://host.docker.internal:8081` and bring up the
   stack.
3. Sign up, configure a service, `POST …/telegram/connect`, read the `setWebhook`
   secret from the mock log, then `POST /webhooks/telegram/{id}` with that secret.
4. The mock log shows the delivered `sendMessage`; `GET …/appointments` shows the
   booking.

## Definition of Done

- [x] Connect validates a token, stores it encrypted, binds the bot, and registers
      the webhook; disconnect reverses it. (Tested; validation proven against real
      Telegram.)
- [x] The bot **answers and books end to end** — connect → inbound → book → **reply
      delivered** — proven live through the stack against a Telegram stand-in.
- [ ] The same run against **real** `api.telegram.org` (needs a BotFather token +
      public URL) — an infra/credential step, no code change.
