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

## What remains in M5

- **Live-data screens**: Conversations / Calendar / Overview currently render
  placeholder data. Wiring them to real data needs **read endpoints** (`GET
  /api/businesses/{id}/conversations`, `…/appointments`, scoped by the M4 guard) —
  backend work, then the screens.
- **Internationalize the remaining existing screens** (settings, approvals,
  conversations, calendar) — designer-independent, straightforward.
- **The visual design** — awaiting the designer's mockups; these components are built
  to be restyled without changing the data/i18n layer.

## Definition of Done

- [x] i18n in place from the first screen; language switcher; ≥2 languages proven
      (en + ru) in an e2e.
- [x] Onboarding happy path implemented and covered by a Playwright e2e.
- [ ] All management screens show **real** scoped data (needs read endpoints).
- [ ] Designer's visual design applied (hand-off pending).
