# CLAUDE.md

Project rules for AI assistants (and humans) working in this repo. Keep them.

## What this is

Frontdesk is an open-source **AI front desk for small service businesses**: it
answers customer messages, books appointments into a real calendar, sends
reminders to kill no-shows, and hands off to a human when needed — on the
channels customers already use (WhatsApp, Telegram). It is a **real-utility
product** built with an **AI-native** workflow.

## Rules

1. **English only.** All code, comments, docs, commits, and identifiers are in
   English. **Exception — chat language:** when replying to the user (Fedor) in
   the chat, always reply in **Russian**, using **plain, short, clear** language
   (simple words, no jargon dumps). This applies only to conversational replies,
   never to repository artifacts (which stay English).
2. **Follow [`CODING_PRINCIPLES.md`](./CODING_PRINCIPLES.md) strictly.** It is the
   engineering standard for this repo — clean code, tests, and discipline. When in
   doubt, it wins.
3. **Clean, structured layout.** Everything lives in a sensible folder. No loose
   files, no dumping ground. The structure should make the design obvious.
4. **Hexagonal architecture (ports & adapters).** The domain core — bookings,
   availability, reminders, the assistant's decision loop — must not import HTTP,
   a database driver, a messaging SDK, or any LLM SDK. Infrastructure (channels,
   storage, schedulers, LLM providers) lives at the edges as adapters behind
   ports. Keep the core pure and testable.
5. **Channel-agnostic.** WhatsApp, Telegram, and any future channel are adapters
   behind one messaging port. Adding a channel must never touch the core.
6. **Model-agnostic.** Every LLM provider is an adapter behind one port. Adding a
   provider must never touch the core.
7. **Human-in-the-loop where it matters.** Actions that move money or can't be
   undone pass an approval gate before they run, rather than being guessed.
8. **Tests are not optional.** Core logic is covered by fast, deterministic tests
   with in-memory fakes — no live API calls (LLM, messaging, or calendar) in
   tests.
9. **Conventional Commits, strictly.** Every commit message follows
   [Conventional Commits](https://www.conventionalcommits.org):
   `<type>(<optional scope>): <description>`. Allowed types: `feat`, `fix`,
   `docs`, `refactor`, `test`, `chore`, `build`, `ci`, `perf`, `style`, `revert`.
   Use the imperative mood, keep the subject short, and add a body for the _why_
   when it isn't obvious. Breaking changes use `!` and a `BREAKING CHANGE:`
   footer. One logical change per commit.
10. **Tooling & deployment.** Local development and deployment run through
    **Docker Compose**. A well-structured **Makefile** is the single entry point
    for common tasks — `make help` lists everything, with targets such as
    `make up`, `make down`, `make test`, `make lint`, `make fmt`, and `make check`
    (the full local gate). Keep targets discoverable and self-documenting.

## Documentation index

All docs live under [`docs/`](./docs/) (see [`docs/README.md`](./docs/README.md)
for the layout). Keep this index in sync — when you add a document, add it here.

- [`CODING_PRINCIPLES.md`](./CODING_PRINCIPLES.md) — the engineering standard for
  this repo (clean code, tests, discipline).
- [`docs/README.md`](./docs/README.md) — documentation layout and conventions.
- [`docs/stack.md`](./docs/stack.md) — the technology stack and pinned versions
  (verified 2026-06-25).
- [`docs/architecture/overview.md`](./docs/architecture/overview.md) — the full
  architecture: the hexagon, domain model, ports & adapters, and the answer /
  booking / reminder flows.
- [`docs/design/contracts.md`](./docs/design/contracts.md) — the precise contract:
  domain types, ports, use cases, the assistant's tools, state machines,
  invariants, the database schema, and errors.
- [`docs/plans/implementation-plan.md`](./docs/plans/implementation-plan.md) — the
  phased, inside-out build with a status snapshot and per-phase Definition of Done.
- [`docs/design/admin-dashboard.md`](./docs/design/admin-dashboard.md) — the admin
  role + cross-tenant operator analytics dashboard (design, data-model gaps,
  hexagonal fit, phased plan).
- [`docs/plans/admin-dashboard-plan.md`](./docs/plans/admin-dashboard-plan.md) — the
  inside-out implementation plan for the admin dashboard (phases, files, tests, DoD).
- [`docs/plans/premium-features-plan.md`](./docs/plans/premium-features-plan.md) — the general
  premium-feature entitlements system (config-driven registry, per-business entitlements,
  self-serve request + admin approval, Google-gated landing demo) and its first consumer, the
  voice receptionist.
- **ADRs** (`docs/adr/`): hexagonal foundations (0001), channels behind a
  messaging port (0002), multi-tenant by business (0003), durable reminders in
  PostgreSQL (0004), human-in-the-loop via Airlock (0005), model-agnostic LLM
  provider (0006), the assistant as a tool-use agent (0007), admin role &
  cross-tenant analytics (0012), premium-feature entitlements & operator management (0013).
