# ADR-0002: Channels behind a messaging port

**Status:** Accepted

## Context

Customers reach small businesses on the channels they already use — WhatsApp first,
Telegram next, maybe Instagram or SMS later. Each has a different API: WhatsApp uses
Meta's **Cloud API** (Graph API) with webhooks and signed payloads; Telegram uses
the **Bot API**. Their message shapes, button/quick-reply models, and delivery
semantics differ. We must not let those differences leak into the assistant or the
booking logic.

## Decision

Define one **`MessagingPort`** in the application layer: send a message (text plus
optional quick-reply buttons) to a customer, and a normalized inbound message type
that every channel maps to. Each channel is an **adapter**:

- inbound: a FastAPI webhook that verifies the signature/secret, then translates the
  provider payload into the normalized inbound message;
- outbound: an httpx client that renders the normalized message into the provider's
  format.

The core speaks only the normalized shapes. WhatsApp is the first adapter; Telegram
the second.

## Consequences

- The assistant and booking flows are channel-agnostic and channel-tested with a
  fake messaging adapter.
- Adding a channel is one adapter + one webhook route; the core is untouched.
- Channel-specific capabilities (e.g. WhatsApp template messages, button limits) are
  handled in the adapter, with a sensible normalized subset in the port.
