# M4 — Accounts, auth & isolation — report

**Status:** Done (2026-06-26) · [SaaS plan, Phase D](../plans/saas-telegram-plan.md)

Owners sign up, log in, and can only ever touch their own business.

## What was built

- **`account` table** (schema + migration 0003): one account owns one business.
- **`AccountRepository`** (port, fake, SQL): `by_email` / `get` / `upsert`.
- **Security** (`security.py`, stdlib only): `hash_password` / `verify_password`
  (PBKDF2-HMAC-SHA256, 200k iters, per-password salt) and `issue_token` /
  `verify_token` (HMAC-signed, keyed by `FRONTDESK_SECRET_KEY`).
- **Auth API** (`auth.py`): `POST /api/signup` (creates the account **and** its
  business, returns a token), `POST /api/login`.
- **Owner guard** (`make_owner_guard`): a dependency that verifies the token and
  requires the account to **own the business in the path** — applied to the config,
  LLM-provider, and Telegram-connect routers. 401 unauthenticated, 403 cross-tenant.

## Verification

- **Gate** (`make check`): ruff, mypy `--strict`, import-linter 3/3, **137 unit
  tests**, 97.9 % (security + auth 100 %).
- **Integration** (`logs/m1/integration.log`): `SqlAccountRepository` passes the port
  contract on real Postgres — **15 integration tests**; migrations reach head **0003**
  with the `account` table.
- **Real run** (`logs/m4/real-run.log`, live stack): two owners sign up; **Ana edits
  her own business (200)** but **Ana's token on Bob's business → 403**; no token →
  401; wrong password → 401. Postgres confirms Bob's business is **unchanged** (still
  "Bob Barber", not "HACKED") and **passwords are hashed at rest**.

## Definition of Done

- [x] An owner signs up, gets a business, and **cannot read or edit another business**
      — verified live and unit-tested.
- [x] Passwords hashed at rest; tokens signed; secrets keyed by `FRONTDESK_SECRET_KEY`.

## Hardening left for later (M6)

Token expiry/refresh, rate-limiting login, email verification / magic links, and CSRF
posture for cookie-based sessions if the dashboard uses them.
