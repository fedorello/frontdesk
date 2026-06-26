# ADR-0009: Bring-your-own LLM provider & API-key storage

**Status:** Accepted (planning) — part of the [SaaS plan](../plans/saas-telegram-plan.md)

> The hosted service is **tovayo.com** — an open-source AI receptionist for small
> businesses. This ADR covers how a business chooses which LLM powers its assistant.

## Context

Each business should be able to **bring its own LLM provider and model** and pay the
model bill directly, *or* use a **managed default** we provide. To bring their own,
an owner pastes an **API key** — a sensitive third-party credential. So this ADR has
two jobs:

1. Let a business pick a provider/model (their own key, or our default).
2. **Store that key safely** — encrypted, never leaked, validated, rotatable.

Providers to support now: **OpenAI, Anthropic, OpenRouter** (extensible later). Note
these already map onto the two adapters we have ([ADR-0006](0006-model-agnostic-llm-provider.md)):
`openai` and `openrouter` are the OpenAI-compatible adapter with different base URLs;
`anthropic` is the Anthropic adapter.

The managed default is **OpenRouter + `deepseek/deepseek-v4-flash`**, paid for by the
platform — so the default path is a cost centre and must be metered.

## Decision

### Per-business LLM configuration

Store an `llm_config` per business:

| field | meaning |
| --- | --- |
| `mode` | `default` (use the platform's provider) or `own` |
| `provider` | `openai` · `anthropic` · `openrouter` (when `own`) |
| `model` | the model id (when `own`) |
| `base_url` | optional override (derived from `provider` by default) |
| `api_key_ciphertext` | the encrypted key (when `own`) — **never plaintext** |
| `api_key_hint` | last 4 chars, for display only |

`mode = default` ignores the rest and uses the platform key + `deepseek-v4-flash` via
OpenRouter. Self-hosters configure their own default key in the environment.

### Provider resolution is tenant-aware

At request time, the assistant's provider is built **per business** (mirroring the
tenant-aware messaging in [ADR-0008](0008-multi-tenant-self-serve-saas.md)): look up
`llm_config`; on `own`, decrypt the key and build the matching adapter; on `default`,
use the platform provider. The domain core never sees a key.

### How the key is stored — the security decision

- **Encrypted at rest with authenticated symmetric encryption** (e.g. Fernet /
  AES-GCM). The database only ever holds ciphertext + a 4-char hint.
- The encryption key (KEK) comes from **outside the database** — an environment
  variable (`FRONTDESK_SECRET_KEY`) for self-host, a **KMS / secrets manager** for the
  hosted service. This is modelled as a `SecretCipher` **port** with two adapters
  (env-key now, KMS later) so the storage backend is swappable without touching call
  sites. The hosted service uses **envelope encryption** (a per-record data key
  wrapped by the KMS).
- **Write-only.** The key is accepted on input and **never returned** by any API or
  rendered in the UI — only `{configured, provider, model, hint}` is exposed.
- **Never logged.** Keys are kept out of logs, error messages, and request traces;
  the `Authorization` header is set at send time and never echoed.
- **Validated on entry.** Before saving, we make one cheap call (e.g. list models or a
  1-token completion) to confirm the key works, and tell the owner pass/fail.
- **Rotatable / deletable.** An owner can replace or remove their key (which reverts
  them to the default). KEK rotation re-encrypts stored keys (`MultiFernet`-style).

### Cost & abuse control on the managed default

Because the platform pays for the default path, it carries **per-tenant quotas / rate
limits** and usage accounting, with a clean seam for billing. Bringing your own key
removes that limit (you pay your provider). Self-hosters set their own policy.

## Consequences

- A business can run the assistant on **its own account and model** — full control and
  cost transparency — or get started instantly on our default with zero setup.
- Holding third-party credentials raises the security bar: encryption at rest, a KMS
  in production, strict no-logging, validation, and rotation are **product features**,
  not nice-to-haves. The `SecretCipher` port keeps this auditable and swappable.
- Provider support is extensible: adding Azure OpenAI, Bedrock, or a local model later
  is a new `provider` value + (if needed) an adapter — no schema churn.
- Being open-source, the same code serves self-hosters (env-key cipher, own default
  key) and the hosted tovayo.com (KMS, metered default) from one design.

## Out of scope (for now)

Billing/metering implementation, additional providers (Azure, Bedrock, local/Ollama),
and per-model cost dashboards. The schema and the `SecretCipher`/provider seams leave
room for each.
