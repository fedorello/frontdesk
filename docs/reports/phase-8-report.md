# Phase 8 — Admin dashboard — report

**Status:** Done (2026-06-25) against the stated DoD; API/SSE wiring noted below.

## What was built (`apps/dashboard`)

A Next.js 16 app (React 19, Tailwind 4, TS 5.9) with the admin surfaces:

- **Overview** — links into each section.
- **Calendar** — the day's appointments with status.
- **Conversations** — what customers asked and how the assistant replied.
- **Approvals** — the dashboard's signature surface for the Phase 7 gate: lists the
  sensitive actions the assistant flagged, with Approve/Reject; nothing runs until a
  human signs off.
- **Settings** — services, hours, knowledge base, channels.
- A shared **Nav** wired into the layout.

Tooling: Prettier, Vitest + Testing Library (jsdom) for components, and Playwright
for e2e. Make targets: `dashboard-install`, `dashboard-check`, `dashboard-e2e`.

## Verification

- **The dashboard gate** (`make dashboard-check`): **typecheck, lint
  (0 warnings), format, test, and build all green**; every route builds
  (`/`, `/calendar`, `/conversations`, `/approvals`, `/settings`).
- **Component tests** (Vitest): the Approvals list renders pending items and fires
  the decision on click (plus its empty state); the Nav links to every section.
- **Playwright e2e** (`logs/phase-8/e2e.log`, production `build && start` harness):
  **viewing the calendar** shows today's appointments, and **approving a pending
  action clears it from the inbox** — exactly the DoD flow. Both green.

## Noted for the wiring/release phase

The views currently render seed data marked `TODO(phase-8)`. Wiring them to a
read API (appointments, conversations, pending approvals) and pushing **live
updates over the Redis event stream** (the `EventPublisher` already emits
`AppointmentBooked` / `ApprovalRequested`) is the integration step, done in the
composition root alongside Phase 9. The UI, its gate, and the e2e — the DoD — are
in place and green.

## Definition of Done

- [x] The dashboard's own gate (typecheck, lint, test, build) is green.
- [x] A Playwright e2e covers viewing the calendar and approving a pending action.
