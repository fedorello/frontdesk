# Security Hardening — June 2026

Follow-up to the security audit of the Tovayo / frontdesk application (FastAPI API +
Next.js dashboard/web). The audit found **no Critical/High issues** and no working
cross-tenant data access. This document records the medium/low fixes that were
implemented in response, each as **problem → solution → result**.

All changes follow `CODING_PRINCIPLES.md`: limits live in `Settings`/named constants,
dependencies stay behind Protocols with in-memory fakes, new code is covered by tests,
and the full gate (ruff, mypy --strict, import-linter, pytest + coverage) is green.

**Scope of this batch:** 6 backend fixes + container hardening. Verified with
**315 unit + 27 integration tests** green.

| # | Severity | Area | Fix |
|---|----------|------|-----|
| 1 | Medium | Owner Telegram linking | Atomic single-use redeem of link codes |
| 2 | Medium/High* | Assistant / refunds | Authorize refunds to the requesting customer |
| 3 | Medium | Rate limiting | Spoof-resistant client IP behind a trusted proxy |
| 4 | Medium | Channels / cost | Bound inbound message length |
| 5 | Medium | Secrets | Fail closed on an empty secret key |
| 6 | Low | Logging / PII | Keep customer chat id out of INFO; blank recorder dir = off |
| 7 | Medium | Containers | Run web + dashboard as a non-root user |

\* High in raw form, reduced to Medium by the existing human-approval gate.

---

## 1. Atomic single-use redeem of owner-link codes

**Problem.** Linking a Telegram chat for owner notifications redeems a one-time UUID
code. `OwnerLinking.confirm` did `get → check used → bind → mark_used` as four separate
steps, and `mark_used` was `UPDATE … SET used = true WHERE code = :code` with no
`used = false` guard or lock. Two concurrent confirms of the same code could both pass
the "is it used?" check before either marked it used — so the "single-use" guarantee was
not actually enforced under concurrency (a TOCTOU race). Impact was low (both requests
need the owner's session), but the invariant was unsound.

**Solution.** The claim is now atomic and happens **before** binding:
`UPDATE telegram_link_code SET used = true WHERE code = :code AND used = false RETURNING code`.
The port method `TelegramLinkCodeStore.mark_used` now returns `bool` (True only if *this*
call claimed the row). `confirm` raises `LinkCodeError(USED)` and binds nothing when the
claim returns False. The specific `NOT_FOUND / EXPIRED / WRONG_BUSINESS` diagnostics are
preserved via the existing `redeem_problem` read.

**Result.** Exactly one redeem can win, with or without a lock. Covered by a unit test
(the in-memory store is single-use), a lost-race test (confirm surfaces `USED` and binds
nothing), and an integration test on real Postgres (second `mark_used` returns False).

---

## 2. Authorize refunds to the requesting customer

**Problem.** `issue_refund` is a sensitive tool gated behind the human-approval gate, but
`_do_refund` built the approval request straight from the model's raw arguments without
ever loading the appointment. A prompt-injected customer could make the agent request a
refund that references **another customer's** appointment id. Nothing was refunded
without a human approving, but the approval record could carry a foreign appointment id.

**Solution.** `_do_refund` now mirrors reschedule/cancel: it loads the appointment, returns
`_NO_SUCH_APPOINTMENT` if it does not exist, and returns `_NOT_THEIRS` if
`appointment.customer_id != customer.id` — **before** reaching the gate. The verified id is
used in the approval summary.

**Result.** A refund can only ever reference the requesting customer's own appointment.
Covered by tests for the gated, approved, foreign-appointment (refused), and
missing-appointment (refused) paths.

> Note: clamping the refund *amount* to the service price was deliberately not bundled
> here — the amount is reviewed by the human approver, and clamping needs `Money`-unit
> handling. Tracked as a follow-up.

---

## 3. Spoof-resistant client IP behind a trusted proxy

**Problem.** Per-IP rate limits on `/api/login`, `/api/signup`, and the OAuth start used
`client_ip`, which read the **left-most** entry of `X-Forwarded-For`. That entry is
fully attacker-controlled: a client could send a different `X-Forwarded-For` value per
request and get a fresh rate-limit bucket every time, defeating the brute-force throttle.

**Solution.** A trusted proxy *appends* the address it actually saw, so the trustworthy
value is N hops from the **right**, where N is the number of trusted proxies. `client_ip`
now takes `trusted_proxy_hops` (new `Settings.trusted_proxy_hops`, default 1 for Railway)
and returns `parts[-trusted_proxy_hops]`, falling back to the socket peer when the chain
is shorter than expected. A client can prepend anything; it is ignored.

**Result.** The login/signup throttle keys on an IP the client cannot forge. Covered by
tests for the happy path, prefix-spoofing (result unchanged), two-hop proxies, the
short-chain fallback, and the no-peer case (100% on `client_ip`).

---

## 4. Bound inbound message length

**Problem.** `InboundMessage.text` and `ChatRequest.text` were unbounded strings. An
oversized payload (via a webhook or the unauthenticated demo `/api/chat`) would be stored
in Postgres, replayed in history, and sent to the paid LLM every turn — a cost and
storage amplification vector.

**Solution.** New domain constant `MAX_MESSAGE_LENGTH = 4096` (Telegram's own ceiling).
The Telegram and WhatsApp parsers truncate inbound text to it; `ChatRequest.text` rejects
anything longer via `Field(max_length=…)` (and the web session id is bounded too).

**Result.** A single message can no longer blow up storage or token cost. Covered by
parser truncation tests (both channels) and a `/api/chat` 422-rejection test.

---

## 5. Fail closed on an empty secret key

**Problem.** `Settings.secret_key` defaults to `""`. The session- and OAuth-signing keys
are HKDF-derived from it and would happily derive deterministic, attacker-known subkeys
from an empty master (forgeable tokens). The only thing preventing a no-secret boot was
that the Fernet cipher happened to be constructed first and raised — an incidental safety
net that depended on import order.

**Solution.** The guard moved into the derivation itself: `_derive` raises
`ValueError("FRONTDESK_SECRET_KEY is required…")` on an empty master. Every consumer —
session signing, OAuth state, encryption — now fails closed independently of ordering.

**Result.** The app cannot start and derive tokens from an empty secret. Covered by a test
asserting all three derivations raise on `""`.

---

## 6. Keep customer chat id out of INFO; treat a blank recorder dir as off

**Problem.** (a) `telegram_inbound` logged the customer `chat_id` (a stable per-user
identifier / PII) at INFO, inconsistent with the message body which is correctly DEBUG.
(b) The opt-in per-prompt recorder is enabled by a non-empty `FRONTDESK_LLM_LOG_DIR`; a
blank/whitespace value (which a hosting CLI may leave when you try to "clear" a variable)
is truthy and would wire the recorder to a junk path.

**Solution.** (a) The INFO line logs only `business_id`; the `chat_id` drops to DEBUG.
(b) `provider_from_config` strips the value and treats blank/whitespace as "off".

**Result.** No PII at INFO; the prompt recorder is off unless a real directory is set.

---

## 7. Run web + dashboard containers as a non-root user

**Problem.** None of the Dockerfiles set a `USER`, so the processes ran as root inside the
container — widening the blast radius of any process compromise.

**Solution.** The `web` and `dashboard` images now create an unprivileged `app` user
(uid 10001), copy build artifacts with `--chown=app:app`, and `USER app` before `CMD`.
These standalone Next.js servers need no root and no writable volume.

**Result.** The two public-facing containers run unprivileged.

> The **API** container is intentionally **not** changed in this batch: it writes logs to a
> Railway volume mounted at `/app/logs`, and a non-root process would silently lose write
> access unless the mounted volume is chowned at startup. Doing that correctly needs a
> small entrypoint that chowns the volume and drops privileges (e.g. `gosu`), or a
> volume-UID configuration — tracked as a follow-up so we don't introduce a silent
> logging failure (`CODING_PRINCIPLES` §8.7).

---

## Deferred (not in this batch)

Recorded so they are tracked, not forgotten:

- **Session revocation.** Tokens are stateless HMAC; logout is client-side only and a
  password change does not invalidate existing sessions. Add a per-account
  `token_version` / `valid_after` checked in the owner guard. (Medium)
- **API container non-root** with a volume-aware entrypoint. (Medium — see §7)
- **Rate-limit / idempotency in Redis** instead of in-process, for correct limits across
  replicas/restarts. (Low)
- **Refund amount clamping** to the service price. (Low — see §2)
- **Login timing equalization** (dummy hash on missing account) and **signup
  enumeration** review. (Low)
- **Google email normalization** before lookup to avoid duplicate accounts. (Low)
- **Encrypt the webhook `secret_token`** at rest, like the bot token. (Low)

## Verification

- `make check` (api): ruff, mypy --strict, import-linter (3 contracts), pytest + coverage
  — **315 unit tests** green; new modules at 100% (`owner_linking`, `client_ip`).
- Integration suite on real Postgres — **27 tests** green, including the atomic-redeem
  claim and the migration chain.
