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

Shipped on 2026-06-28. Each has a regression test.

| Area | Issue | Fix |
|---|---|---|
| **Tenant IDOR (CRITICAL)** | `PUT/DELETE /api/businesses/{id}/services/{service_id}` (and resources) acted on a globally-unique object id, scoped only by the path `business_id` the guard validated — so any owner could overwrite or delete **another** business's services/resources by id. | Every mutation is scoped by `business_id`: SQL `DELETE ... WHERE id = :id AND business_id = :bid`, `ON CONFLICT (id) DO UPDATE ... WHERE service.business_id = :bid` (same for resources), the in-memory fakes mirror it, and `ServiceRepository.remove(id, business_id)` carries the tenant. Contract test asserts a foreign business can't delete/overwrite. |
| **Open approvals (CRITICAL)** | `GET/POST /api/approvals` had **no auth and no tenant scoping** — anyone could read every business's queued sensitive actions (with full tool args) and approve/deny them. | Each `PendingApproval` is tagged with its `business_id` (`SensitiveAction.business_id`); routes moved under `/api/businesses/{id}/approvals` behind the **owner guard**; `pending()`/`decide()` are scoped per tenant. Regression tests for cross-tenant list + decide. |
| **OAuth id_token** | The Google `id_token` was decoded without checking `aud`/`iss` — not pinned to this app's client. | Verify `aud == client_id` and `iss ∈ {accounts.google.com, https://accounts.google.com}`; the callback handles exchange failures with a redirect, not a 500. |
| **Webhook secret** | Telegram secret header compared with `!=` (timing oracle). | `hmac.compare_digest` (constant-time), matching the WhatsApp path. |
| **Password policy** | Signup accepted any password (including 1 char). | `min_length=8` on `SignupInput.password`. |
| **PII in logs** | Customer message bodies and agent tool args/results logged at INFO to a persisted file. | Demoted to DEBUG; the default INFO log no longer stores conversation PII. |
| **Security headers** | Neither Next app set any. | Both send `X-Frame-Options: DENY` (clickjacking), `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`. |

---

## 3. Planned hardening 🟡 / 🔵

Ordered by value. Each item: the problem, the risk, the approach, and rough effort.

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

---

## 4. Operational actions ⚙️

- **Rotate the OpenRouter API key.** A live `FRONTDESK_LLM_API_KEY` sits in the local,
  git-ignored `deploy/docker/.env` (verified: never committed, not in git history). It was
  surfaced during the audit, so rotate it in OpenRouter and update Railway Variables.
- **Keep all secrets in Railway Variables**, never baked into images (Dockerfiles only pass
  non-secret `NEXT_PUBLIC_*` build args — confirmed).
- **Add SCA to CI** (e.g. `pip-audit` / `trivy fs` for Python, `pnpm audit` for the apps) so a
  newly-disclosed CVE in a dependency fails the build. Dependencies are current today.
- **Treat the DEBUG data-flow log as a PII store** when enabled: access-controlled, short
  retention.

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

## 6. Roadmap (suggested order)

1. **3.1** Session cookie (HttpOnly) — closes the highest-leverage remaining vector. Pull **3.3**
   (OAuth state cookie) and the CORS-credentials change along with it.
2. **3.2** Rate limiting on auth endpoints.
3. **3.5** CSP with a nonce.
4. **3.6** Email validation + verification.
5. **3.4 / 3.8** HKDF key separation and DB-backed approvals (coordinate with a key rotation /
   the airlock follow-up).
6. **⚙️** Rotate the OpenRouter key now; add SCA to CI.
