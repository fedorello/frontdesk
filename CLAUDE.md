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
   English.
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

Keep this index in sync — when you add a document, add it here.

- [`CODING_PRINCIPLES.md`](./CODING_PRINCIPLES.md) — the engineering standard for
  this repo (clean code, tests, discipline).
