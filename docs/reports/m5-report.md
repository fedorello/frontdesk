# M5 — Dashboard: onboarding + management UI (i18n) — report

**Status:** Functional core done (2026-06-26) · [SaaS plan, Phase E](../plans/saas-telegram-plan.md)

The dashboard's **functional, internationalized** layer is built and tested. The
**visual design is intentionally deferred to Fedor's designer** (per the
[UX brief](../design/ux-brief.md) hand-off) — these components are the skeleton the
mockups will skin.

## What was built

- **i18n from the first screen** (`app/lib/i18n.ts`): a per-locale message catalog
  (en/es/ru/zh), `translate()` with interpolation + English fallback, an
  `I18nProvider`/`useI18n` context, and a global `LanguageSwitcher`. No hard-coded
  user-facing strings in the new components.
- **Typed API client** (`app/lib/api.ts`): one place that knows the
  signup/login/business/services/resources/llm/telegram endpoints and shapes.
- **Internationalized nav** + the app wrapped in the i18n provider.
- **Onboarding wizard** (`app/onboarding/page.tsx`): account+business → service →
  choose AI (managed default or own key) → connect Telegram, wired to the real M2–M4
  APIs, fully translated.

## Verification

- **Dashboard gate**: typecheck, eslint (max-warnings 0), prettier, **13 unit tests**,
  production build — all green.
- **Playwright e2e** (`logs/m5/e2e.log`, real Chromium): the **whole onboarding happy
  path** (sign up → add service → pick AI → connect Telegram → "Connected as
  @ana_bot") drives the real UI with the API mocked at the network boundary; a second
  test switches the wizard to **Russian** via the language switcher. **4 e2e pass.**

## Live data — calendar wired

- A `GET /api/businesses/{id}/appointments` read endpoint (scoped by the M4 guard,
  resolves service names) + a client session store; the **calendar screen now renders
  the owner's real bookings** (i18n empty / sign-in states).
- **Live run** (`logs/m5/live-run.log`, full stack): Ana **signs up via the dashboard
  API**, configures her business over the API with her token, a customer **books via
  the assistant**, and `GET …/appointments` with Ana's token returns the real booking
  — `[("Haircut", "09:00", "pending")]`; **401 without a token**. This is exactly the
  data the calendar screen renders.

## What remains in M5

- **Conversations / Overview screens**: still placeholder — need a conversations read
  endpoint, then wiring (same pattern as the calendar).
- **Internationalize the remaining screens** (settings, approvals, conversations) —
  designer-independent.
- **The visual design** — awaiting the designer's mockups; the components are built to
  be restyled without changing the data/i18n layer.

## Definition of Done

- [x] i18n in place from the first screen; language switcher; ≥2 languages proven
      (en + ru) in an e2e.
- [x] Onboarding happy path implemented and covered by a Playwright e2e.
- [x] The calendar shows **real, auth-scoped bookings** (proven in a live run).
- [ ] Conversations / Overview show real data (needs a conversations read endpoint).
- [ ] Designer's visual design applied (hand-off pending).
