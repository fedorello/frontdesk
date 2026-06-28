# Security Hardening Plan — Tovayo

> Living document. Tracks the security posture of the Tovayo service (the marketing site
> `tovayo.com`, the dashboard `app.tovayo.com`, and the API) and the work to harden it.
> Born out of the security audit on **2026-06-28**.

**Legend:** ✅ Done (shipped) · 🟡 Planned · 🔵 Recommended (needs a decision) · ⚙️ Operational

---

## 1. Scope & threat model

Tovayo is a **multi-tenant** SaaS: one deployment serves many small businesses, each with its
own Telegram bot, schedule, conversations, and bookings. The dominant risks, in order:

1. **Tenant isolation** — one owner must never read or mutate another business's data.
2. **Account/session compromise** — token theft, brute force, OAuth abuse.
3. **The agent acting on untrusted input** — prompt injection driving sensitive actions.
4. **Data at rest / in logs** — customer conversations and PII.
5. **Web surface** — XSS, clickjacking, headers, secrets in the bundle.

The architecture already puts the safety boundary for sensitive actions *outside* the model
(Airlock gate, ADR-0005), and the owner guard scopes routes per tenant. This plan closes the
gaps the audit found and lists the remaining hardening.

---

## 2. Completed hardening ✅

The first batch (audit remediation) and the full §3 plan both shipped on **2026-06-28**. Each
item has a regression test; the whole gate (ruff/mypy/import-linter/pytest + integration,
dashboard typecheck/lint/test/build) is green.

**Audit remediation:**

| Area | Issue | Fix |
|---|---|---|
| **Tenant IDOR (CRITICAL)** | `PUT/DELETE /api/businesses/{id}/services/{service_id}` (and resources) acted on a globally-unique object id, scoped only by the path `business_id` the guard validated — so any owner could overwrite or delete **another** business's services/resources by id. | Every mutation is scoped by `business_id`: SQL `DELETE ... WHERE id = :id AND business_id = :bid`, `ON CONFLICT (id) DO UPDATE ... WHERE service.business_id = :bid` (same for resources), the in-memory fakes mirror it, and `ServiceRepository.remove(id, business_id)` carries the tenant. Contract test asserts a foreign business can't delete/overwrite. |
| **Open approvals (CRITICAL)** | `GET/POST /api/approvals` had **no auth and no tenant scoping** — anyone could read every business's queued sensitive actions (with full tool args) and approve/deny them. | Routes moved under `/api/businesses/{id}/approvals` behind the **owner guard**, scoped per tenant (later DB-backed — see 3.8). Regression tests for cross-tenant list + decide. |
| **OAuth id_token** | The Google `id_token` was decoded without checking `aud`/`iss` — not pinned to this app's client. | Verify `aud == client_id` and `iss ∈ {accounts.google.com, https://accounts.google.com}`; the callback handles exchange failures with a redirect, not a 500. |
| **Webhook secret** | Telegram secret header compared with `!=` (timing oracle). | `hmac.compare_digest` (constant-time), matching the WhatsApp path. |
| **Password policy** | Signup accepted any password (including 1 char). | `min_length=8` on `SignupInput.password`. |
| **PII in logs** | Customer message bodies and agent tool args/results logged at INFO to a persisted file. | Demoted to DEBUG; the default INFO log no longer stores conversation PII. |
| **Security headers** | Neither Next app set any. | Both send `X-Frame-Options: DENY` (clickjacking), `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`. |

**§3 hardening plan (all implemented):**

| # | What shipped |
|---|---|
| **3.1** | HttpOnly session cookie: the auth token is no longer in `localStorage` or any URL — set by the API on login/signup/OAuth (`Secure`, `SameSite=Lax`), guard reads cookie-or-Bearer, `/api/logout` clears it; dashboard uses `credentials: include` and stores only the business id + display identity. |
| **3.2** | Per-IP rate limiting (fixed window, `RateLimiter` port) on login (10/5min), signup (5/hr), and OAuth start; 429 on trip, logged; X-Forwarded-For aware. |
| **3.3** | OAuth `state` bound to a browser cookie (constant-time compare) — login-CSRF closed. |
| **3.4** | HKDF key separation: one master key derives independent encryption / session-signing / OAuth-state subkeys. `MultiFernet` keeps legacy ciphertext decryptable (no prod break). |
| **3.5** | Content-Security-Policy with a per-request nonce (proxy/middleware) on both apps — no `unsafe-inline` for scripts; `frame-ancestors 'none'`, `object-src 'none'`. |
| **3.6** | `EmailStr` validation + case normalization on signup/login. (Full email-verification anti-enumeration still deferred — see §3-future; rate limiting bounds enumeration meanwhile.) |
| **3.7** | CORS locked to an explicit origin (never `*`) with `allow_credentials`; default falls back to the dashboard origin. |
| **3.8** | DB-backed approval queue (`ApprovalStore` port, `approval` table, migration 0014): restart-safe and cross-process — a poller-raised approval shows in the API inbox. |
| **logging** | Full file logging hardened (`FRONTDESK_LOG_FILE`, rotating, dir auto-created); security events (signup/login/logout, auth rejects, rate-limit trips, OAuth state failures) flow to the file with no PII/secrets. |

---

## 3. Future / deferred

Genuinely out of scope for this pass (need new infrastructure or a product decision). The
original detailed write-ups are kept below for reference.

- **Email-verification anti-enumeration** — needs an email provider; signup still returns a
  distinct 409. Mitigated for now by the signup rate limit (3.2).
- **KMS-backed cipher** — `SecretCipher` port is ready; swap `FernetCipher` for a KMS adapter
  when warranted.
- **Redis-backed rate limiter / approval pub-sub** — the in-memory `RateLimiter` is per-instance;
  move to Redis when the API scales beyond one instance.

<details>
<summary>Original §3 plan write-ups (now implemented — kept for reference)</summary>

### 3.1 🔵 HIGH — Move the session token out of `localStorage` and out of the URL
**Problem.** The bearer session token is stored in `localStorage` (`app/lib/session.ts`) and,
on Google sign-in, delivered in the **redirect URL query string** (`/auth/callback?token=…`).
**Risk.** Any XSS on the dashboard reads the token from `localStorage` → full account takeover.
The token in the URL leaks to browser history, the `Referer` header, and proxy/access logs.
**Approach.** Issue the session as an **`HttpOnly; Secure; SameSite=Lax` cookie** set by the API
(on `/api/login`, `/api/signup`, and the OAuth callback redirect). The dashboard stops touching
the raw token; the API reads the cookie instead of the `Authorization` header. This single change
closes both the XSS-theft and the URL-leak vectors. Requires CORS `allow_credentials=True`
locked to the dashboard origin, and a CSRF defense for cookie-auth (SameSite=Lax + a custom
header check or double-submit token).
**Effort:** Medium–Large (touches the whole auth transport: API, dashboard, CORS).

### 3.2 🟡 HIGH — Rate limiting / lockout on `login` and `signup`
**Problem.** No throttling on `/api/login` or `/api/signup`.
**Risk.** Credential stuffing / brute force; unlimited automated account creation; enumeration.
**Approach.** Per-IP and per-account fixed-window or token-bucket limiter with exponential backoff
/ temporary lockout. Redis is already a dependency — back it there behind a `RateLimiter`
protocol (DI, in-memory fake for tests). Apply to login, signup, and the OAuth `/start`.
**Effort:** Medium.

### 3.3 🟡 HIGH — Bind the OAuth `state` to the browser (login CSRF)
**Problem.** `state` is a free-floating signed token; the callback checks only its signature +
freshness, not that it belongs to the initiating browser.
**Risk.** Login-CSRF / session fixation — a victim can be silently logged into an attacker's flow.
**Approach.** Set the `state` (or a PKCE `code_verifier`) in an `HttpOnly; SameSite=Lax; Secure`
cookie at `/start` and compare it (constant-time) at `/callback`. Pairs naturally with 3.1.
**Effort:** Small–Medium.

### 3.4 🔵 MEDIUM — Separate keys via HKDF
**Problem.** One `FRONTDESK_SECRET_KEY` is reused for Fernet encryption, HMAC session-token
signing, and OAuth-state signing.
**Risk.** No live cross-protocol break today, but rotation is coupled (rotating to invalidate
sessions also makes every stored bot token / LLM key undecryptable) and a future change to a
signing routine could open an oracle.
**Approach.** Derive three independent subkeys with HKDF (`info=b"fernet"`, `b"session"`,
`b"oauth-state"`) from the master key. **Do this at a planned key rotation** — changing the key
derivation re-keys everything, so it must be coordinated with re-encrypting stored secrets.
**Effort:** Medium (plus a data migration / re-encrypt step).

### 3.5 🔵 MEDIUM — Content-Security-Policy
**Problem.** No CSP (the other headers ship; CSP was deferred).
**Risk.** No defense-in-depth against a future XSS; weaker exfiltration resistance.
**Approach.** Add a strict CSP to both Next apps. The inline no-flash theme script in the layout
needs a **per-request nonce** (or a sha256 hash in `script-src`) — do **not** fall back to
`'unsafe-inline'`. Add `frame-ancestors 'none'` (complements `X-Frame-Options`).
**Effort:** Medium (nonce plumbing through the layout).

### 3.6 🟡 MEDIUM — Email validation & anti-enumeration on signup
**Problem.** `email` is a plain `str` (not `EmailStr`); signup returns a distinct `409 email
already registered`, so account existence is observable.
**Risk.** Malformed/duplicate-normalized emails; account enumeration feeding the brute-force.
**Approach.** Use pydantic `EmailStr` (adds the `email-validator` dep) and normalize case before
the uniqueness check. Gate signup behind email verification, or return a uniform response so
existence isn't directly observable. Pairs with 3.2.
**Effort:** Small (validation) / Medium (verification flow).

### 3.7 🟡 LOW — CORS default
**Problem.** `cors_allow_origins` defaults to `*` in code (production is already locked to the
dashboard origin via `FRONTDESK_CORS_ALLOW_ORIGINS`, so prod is mitigated).
**Approach.** Default to `settings.dashboard_url` instead of `*`, and never combine `*` with a
future `allow_credentials=True` (see 3.1).
**Effort:** Small.

### 3.8 🔵 MEDIUM — DB-backed approval queue
**Problem.** Approvals live in an **in-memory** per-process queue (a dogfood of airlock-hitl), so
an approval raised in the poller process isn't visible to the API's inbox, and it's lost on
restart (tracked already in ADR-0010's follow-up).
**Approach.** Move the queue behind an `ApprovalStore` port with a Postgres-backed
implementation, keyed by `business_id` (the scoping from §2 carries over). Restart-safe and
consistent across processes.
**Effort:** Medium.

</details>

---

## 4. Operational actions ⚙️

- ✅ **SCA in CI** — a `security` job runs `pip-audit` (Python, via the official action) and
  `pnpm audit --audit-level high` (both apps) on every push/PR, failing on a high/critical
  advisory. (One transitive *moderate* in `postcss` is below the gate.)
- ⏳ **Rotate the OpenRouter API key.** A live `FRONTDESK_LLM_API_KEY` sits in the local,
  git-ignored `deploy/docker/.env` (verified: never committed, not in git history). It was
  surfaced during the audit — rotate it in OpenRouter and update Railway Variables. **(Manual:
  only the account owner can do this.)**
- ✅ **Secrets stay in Railway Variables**, never baked into images (Dockerfiles only pass
  non-secret `NEXT_PUBLIC_*` build args).
- **Treat the DEBUG data-flow log as a PII store** when enabled: access-controlled, short
  retention. File logging is enabled via `FRONTDESK_LOG_FILE` (rotating).

---

## 5. Verified secure (audit, 2026-06-28)

These were checked and found sound — listed so they're not re-litigated:

- **Session tokens** are HMAC-SHA256 signed, verified with `hmac.compare_digest`, with expiry
  (`token_max_age_seconds`) enforced end-to-end through the guard.
- **Passwords** use PBKDF2-HMAC-SHA256 at 200k iterations, constant-time verify.
- **SQL injection:** every `text(...)` query binds user-influenced values as parameters; the
  `SqlBusinessEraser` f-string iterates a hardcoded table whitelist (no user input).
- **Secrets in git:** none. `.gitignore` covers `.env*`; git history has no API key or Fernet
  key; only `.env.example` placeholders are tracked.
- **Tenant isolation** of appointments and conversations re-checks the object's `business_id`
  (`TenantMismatch`) before acting — the pattern §2.1 now extends to services/resources.
- **XSS:** React escapes all user-controlled strings (customer/business names, message bodies,
  intake answers); no `dangerouslySetInnerHTML` with user data; `react-markdown` runs without
  `rehype-raw` and drops `javascript:` URLs; legal-page markdown is static.
- **Client bundle:** no secret in any `NEXT_PUBLIC_*`; the Google **client secret lives only on
  the API**.
- **Telegram webhook** verifies a per-bot secret token (now constant-time) and resolves the
  business from the path — a valid secret for one bot can't drive another's.
- **Dependencies** are current with no known-vulnerable security-relevant versions.

---

## 6. Roadmap — ✅ complete (2026-06-28)

All of §3 (3.1–3.8) and the SCA CI job shipped on 2026-06-28, in roadmap order, each gated and
tested. The only open items are the genuinely-deferred ones in §3-future and the **manual**
OpenRouter key rotation in §4.
