# ADR-0005: Human-in-the-loop via Airlock

**Status:** Accepted — implemented (see below)

## Context

The assistant takes real actions on behalf of a business. Most are safe (answer a
question, read availability). Some are not: issuing a refund, sending a payment link,
overriding a cancellation policy, or anything that moves money or can't be undone. An
LLM can be wrong or talked into the wrong thing by a customer message, so these
actions must not run on the model's say-so alone — the business owner has to be able
to approve them.

## Decision

Reuse the [Airlock](https://github.com/fedorello/airlock) pattern via the published
**`airlock-hitl`** package as the `ApprovalGate` adapter. Sensitive tools the
assistant can call are tagged so they **pause** for human approval (approve / edit /
reject) before they execute; safe tools run automatically. Approvals surface in the
dashboard.

## Consequences

- A model mistake — or a manipulative customer message — can't quietly cost the
  business money; the boundary is enforced by the architecture, not by trusting the
  prompt.
- We dogfood our own primitive, and keep the gate logic out of Frontdesk's core
  (it's an adapter behind the `ApprovalGate` port).
- A small amount of latency on sensitive actions, by design — the owner decides. The
  default tier list is conservative and configurable per business.

## Implementation

Both published packages are dogfooded:

- **Backend** (`airlock-hitl`, PyPI): `infrastructure/airlock_gate.py`'s
  `AirlockApprovalGate` implements the `ApprovalGate` port by turning a sensitive
  action into an Airlock `Tool`/`ToolCall` and running it through Airlock's
  `RiskBasedGatePolicy`; when it needs a human, an Airlock `ApprovalRequest` is
  raised and queued. The production composition root wires this gate. `/api/approvals`
  lists the pending requests and records decisions.
- **Dashboard** (`@fedorello/airlock`, npm): the Approvals inbox types its data with
  Airlock's exported `RiskTier`/approval contract and reads/decides against the API.

Airlock's full agent runtime (the `Agent`/`AgentRunner` run loop) is intentionally
not adopted — Frontdesk has its own assistant loop — so we reuse Airlock's gate
policy and approval domain, not its runner.
