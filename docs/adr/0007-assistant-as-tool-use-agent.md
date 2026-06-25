# ADR-0007: The assistant is a tool-use agent

**Status:** Accepted

## Context

A naive "AI receptionist" is a chatbot that free-texts answers and "confirms" a
booking in prose that nothing actually records. That double-books customers, invents
prices, and promises slots that don't exist. The assistant must *do* real work
against the real calendar — reliably — while the model only handles language and
intent.

## Decision

Implement the assistant as a **tool-use (ReAct) loop** whose tools **are the domain
use cases**, not free-form text:

- `answer_question`, `find_availability`, `book`, `reschedule`, `cancel`, `escalate`.

The model decides *what* to attempt; the typed, tested core decides *whether and how*
it happens. `book` enforces no double-booking, lead time, and policy in code, not in
the prompt. The assistant answers facts only from the business's knowledge base and
the real calendar — it does not invent prices or availability — and escalates when it
isn't sure. Sensitive tools pass the approval gate
([ADR-0005](./0005-human-in-the-loop-via-airlock.md)).

## Consequences

- Bookings are correct by construction: the calendar, not the prose, is the truth.
- The assistant is grounded — no hallucinated prices or slots — which is what makes it
  trustworthy for a real business.
- The loop is testable with a scripted fake provider: given a message and tool
  results, assert the actions taken.
