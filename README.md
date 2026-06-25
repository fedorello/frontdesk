# Frontdesk

**An open-source AI front desk for small service businesses — it answers, books,
and reminds, so you stop losing money to missed messages and no-shows.**

Salons, clinics, tutors, studios, barbershops, repair shops — they run on
WhatsApp and Telegram. A message arrives after hours and nobody replies, so the
booking goes to whoever answered faster. A client forgets the appointment, the
slot sits empty, and it's too late to resell it. Staff burn hours on the same
back-and-forth: "what are your prices?", "do you have Friday at 5?", "can we move
it to Tuesday?".

Frontdesk is the assistant that handles all of that on the channels your
customers already use.

---

## The problem

For an appointment-based business, two leaks quietly drain revenue:

- **Missed messages.** Most enquiries arrive outside working hours or while staff
  are with a client. An unanswered message is a lost booking — the customer moves
  on to the next result.
- **No-shows.** Forgotten appointments leave empty slots that can't be filled at
  the last minute. For many small businesses that's 20–40% of the calendar.

The usual "fixes" don't fit a small business: a full-time receptionist is
expensive, generic chatbots are frustrating and can't actually book anything, and
booking widgets don't help the customer who only ever messages you on WhatsApp.

## What Frontdesk does

An AI assistant that lives on the channels your customers use and actually gets
work done:

- **Answers the common questions** — hours, prices, services, location,
  "do you do X?" — instantly, 24/7, in the customer's language.
- **Books appointments into a real calendar** — checks availability, avoids
  double-booking, and confirms.
- **Kills no-shows** — sends smart reminders with one-tap confirm or reschedule,
  so a forgotten slot becomes a kept one (or a freed one you can resell).
- **Hands off to a human** — anything it shouldn't decide alone (a refund, an
  edge case, an unhappy customer) is escalated, not guessed.

Self-hostable, multilingual, and model-agnostic: you own your data, your
calendar, and your customer relationships.

The point in one line: **turn missed messages and forgotten appointments into
booked, kept revenue — without hiring a receptionist.**

## Who it's for

Any small, appointment-based service business: hair & beauty, clinics and
therapists, tutors and coaches, studios, barbershops, repair and trades. If your
calendar is your revenue and your inbox is WhatsApp, this is for you.

## Planned architecture

Frontdesk is built as a real, maintainable product, not a demo script:

- **Hexagonal architecture (ports & adapters).** The domain core — bookings,
  availability, reminders, the assistant's decision loop — knows nothing about
  WhatsApp, a database, or any LLM vendor. Everything external is an adapter
  behind a port.
- **Channel-agnostic.** WhatsApp and Telegram are adapters behind one messaging
  port; adding a channel never touches the core.
- **Model-agnostic.** Every LLM provider sits behind one port — swap models with
  a config change.
- **Human-in-the-loop where it matters.** Sensitive actions pass an approval gate
  before they happen (the same discipline as
  [Airlock](https://github.com/fedorello/airlock)).
- **An admin dashboard** for the business: calendar, conversations, settings, and
  a clear view of what the assistant did and what it escalated.

The concrete stack and pinned versions will live in `docs/stack.md`; the leaning
is a Python (FastAPI) core, a Next.js admin app, Postgres for data, and Redis for
events and the reminder scheduler — run locally and in production through Docker
Compose, with a Makefile as the single entry point.

## Status

Early — built in the open. This repository starts with its engineering standard
and guidance; the implementation follows in staged, reviewed phases.

## How it's built

Directing Claude Code against a staged spec — the product framing, the
architecture, and the review are mine. The interesting part of the diff history
isn't the code, it's what an AI-native delivery loop looks like when the
engineer's job is to specify, review, and decide.

Everything is built and reviewed against [`CODING_PRINCIPLES.md`](./CODING_PRINCIPLES.md).

## License

[MIT](./LICENSE)
