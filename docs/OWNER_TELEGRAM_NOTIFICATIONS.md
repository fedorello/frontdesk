# Owner Telegram Notifications — Design

> Notify the **business owner**, via the same business Telegram bot, whenever the schedule
> changes — a booking, reschedule, or cancellation (with extra emphasis when a booking needs
> the owner's confirmation). The owner links their personal Telegram account once with a
> one‑time code, and can toggle the notifications on/off.

This document is the implementation contract. It follows `docs/CODING_PRINCIPLES.md` (clean
architecture, DI through Protocols, no hardcode, 100% testable with in‑memory fakes, English
comments). It grounds every decision in the **existing** code so the feature drops in cleanly.

---

## 1. Goals & non‑goals

**Goals**

- The owner receives a Telegram message on every customer‑driven schedule change:
  **booked**, **rescheduled**, **cancelled**. A booking that needs confirmation is flagged.
- The owner links one Telegram account to their business via a **one‑time UUID code**, proving
  ownership through their authenticated dashboard session.
- A single **toggle** turns these notifications on/off.
- Sent through the business's **own** bot (the one already connected for customers).

**Non‑goals (explicitly out of scope, tracked separately)**

- Inline “Confirm / Decline” buttons inside the Telegram notification (callback handling). MVP
  links to the dashboard to confirm. → future enhancement.
- Multiple owner/staff recipients per business (MVP supports **one** owner chat per business).
- Customer‑facing notifications (this is owner‑only).
- Notifying the owner of their **own** dashboard actions (de‑duplication of self‑actions).

---

## 2. What already exists (grounding)

| Capability | Where | Reuse |
| --- | --- | --- |
| `AppointmentBooked`, `AppointmentCancelled`, `AppointmentConfirmed` events | `application/ports.py` (DomainEvent subtypes) | trigger source |
| `BookAppointment` / `CancelAppointment` publish events | `application/appointments.py` | trigger points |
| `RescheduleAppointment` — **publishes nothing today** | `application/appointments.py` | **must add** `AppointmentRescheduled` |
| `EventPublisher` Protocol; only `LoggingEventPublisher` / `InMemoryEventPublisher` | `ports.py`, `infrastructure/events.py`, `infrastructure/memory.py` | **no reactor exists** — must add fan‑out |
| Per‑business bot token (encrypted), resolution | `SqlTelegramBotRepository`, `tenancy.py` | resolve the bot to send through |
| Low‑level send to a bare `chat_id` | `telegram_send_message(token, chat_id, text, client)` in `infrastructure/channels/telegram.py` | send to the owner's chat (no `Customer` needed) |
| Inbound update → `chat_id` + `text` | `parse_telegram_inbound()` (`telegram.py`); dispatched by `telegram_inbound.py` | intercept the link command |
| Owner auth guard (session cookie → account → business) | `make_owner_guard()` in `interface/auth.py` | protect the confirm/toggle endpoints |
| Per‑business config write‑API pattern | `business_config.py` (`put_llm`) | model the new endpoints |
| Repo + Postgres adapter + `CREATE TABLE` + alembic | `adapters.py`, `schema.py`, `alembic/versions/` (latest **0018**) | new tables = migration **0019** |

Two genuinely new things: **(a)** an event fan‑out so something can *react* to events (today they
are only logged), and **(b)** the owner‑link + notifier machinery.

---

## 3. User flows

### 3.1 Linking (owner‑initiated from Telegram — the requested flow)

```
Owner (Telegram)                Bot / API                         Dashboard (browser, signed in)
  | send "/connect"  ───────────►|
  |                              | create one‑time LinkCode(uuid)
  |                              |   bound to (business_id, chat_id, telegram_name), 15‑min TTL
  |◄── "Open this link while signed in as the owner:
  |     https://<dashboard>/connect-telegram?code=<uuid> (expires in 15 min)"
  |                                                                 | open the link (authenticated)
  |                                                                 | POST /api/businesses/{id}/telegram-owner/confirm {code}
  |                              | guard: session owns {id}; code valid, unexpired, unused,
  |                              |        and code.business_id == {id}
  |                              | upsert OwnerTelegramLink(business_id, chat_id, name, enabled=true)
  |                              | mark code used
  |                                                                 |◄── { linked: true, telegram_name: "@..." }
  |◄── (optional) bot confirms: "✅ Notifications are on for this chat."
```

The browser session proves **who the owner is**; the code proves **which Telegram chat**; the
endpoint binds them. The confirm screen **shows the Telegram account name** being linked so the
owner verifies it is theirs before confirming (see §10 Security).

### 3.2 Notification (on every schedule change)

```
Customer books/reschedules/cancels (via the assistant or any path through the use cases)
   → BookAppointment/RescheduleAppointment/CancelAppointment publishes a DomainEvent
   → DispatchingEventPublisher fans out to listeners
   → OwnerNotifier: link exists & enabled?  → load appointment+service+customer+business
                                              → format localized message
                                              → send via the business bot to owner's chat (best‑effort)
```

### 3.3 Toggle / status / unlink (dashboard, owner‑guarded)

- `GET  /telegram-owner` → `{ linked, telegram_name, notifications_enabled }`
- `PUT  /telegram-owner/notifications` `{ enabled }` → mute/unmute
- `DELETE /telegram-owner` → unlink the chat

---

## 4. Domain model (new)

Pure types in `domain/` — no infrastructure imports.

```python
# domain/ids.py — branded ids (no raw str; §2.3)
LinkCode = NewType("LinkCode", str)   # the one-time UUID in the link

# domain/models.py (or a new domain/notifications.py if models.py nears 400 lines)
class NotificationEvent(StrEnum):                 # which change happened (§7.2 no magic strings)
    BOOKED = "booked"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"

@dataclass(frozen=True, slots=True)
class OwnerTelegramLink:
    """The owner's linked Telegram chat for a business, and whether alerts are on."""
    business_id: BusinessId
    chat_id: str                 # Telegram chat id, stored as text (matches customer.address)
    telegram_name: str           # display name / @username, shown back for verification
    notifications_enabled: bool = True

@dataclass(frozen=True, slots=True)
class TelegramLinkCode:
    """A one-time code that proves a Telegram chat asked to be linked; short-lived."""
    code: LinkCode
    business_id: BusinessId
    chat_id: str
    telegram_name: str
    expires_at: datetime         # timezone-aware UTC (§7.7)
    used: bool = False
```

Business rule helpers live in the domain (pure, 100% testable):

```python
def code_is_redeemable(code: TelegramLinkCode, business_id: BusinessId, now: datetime) -> bool:
    """A code may be redeemed once, before expiry, by its own business."""
    return (not code.used) and code.expires_at > now and code.business_id == business_id
```

---

## 5. Ports (Protocols) — new

All in `application/ports.py`, each one a single use‑case (ISP). Implementations are injected
(DIP); every one gets an in‑memory fake for tests.

```python
class OwnerTelegramLinkRepository(Protocol):
    async def get(self, business_id: BusinessId) -> OwnerTelegramLink | None: ...
    async def upsert(self, link: OwnerTelegramLink) -> None: ...
    async def remove(self, business_id: BusinessId) -> None: ...

class TelegramLinkCodeStore(Protocol):
    async def issue(self, code: TelegramLinkCode) -> None: ...
    async def get(self, code: LinkCode) -> TelegramLinkCode | None: ...
    async def mark_used(self, code: LinkCode) -> None: ...

class EventListener(Protocol):
    """Reacts to a published DomainEvent. New reactions = new listeners (OCP), no use-case edits."""
    async def on_event(self, event: DomainEvent) -> None: ...

class OwnerNotificationSender(Protocol):
    """Sends a message to a chat through a given business's own bot."""
    async def send(self, business_id: BusinessId, chat_id: str, message: str) -> None: ...
```

> `OwnerNotificationSender` keeps the notifier free of `httpx` and the bot repository (DIP): the
> notifier asks “send this to this chat for this business”; the adapter resolves the bot token and
> performs the HTTP call.

---

## 6. Event fan‑out (the core architectural addition)

Today `EventPublisher` has only a logging implementation; nothing reacts. Introduce a composite
that fans a published event out to a list of `EventListener`s, **isolating failures** so a slow or
failing notification can never break a booking (the event is published *after* the appointment is
already committed; §8.7 — log, don't swallow silently).

```python
# infrastructure/events.py
class DispatchingEventPublisher:
    """Publishes by notifying each listener; one listener's failure never affects the others."""
    def __init__(self, listeners: Sequence[EventListener], logger: LoggerLike) -> None:
        self._listeners = tuple(listeners)
        self._log = logger

    async def publish(self, event: DomainEvent) -> None:
        for listener in self._listeners:
            try:
                await listener.on_event(event)
            except Exception as error:                    # noqa: BLE001 — isolation boundary
                # Best-effort side effects: log and continue; the booking already succeeded.
                self._log.warning("event listener failed: %s on %s", error, type(event).__name__)
```

- `LoggingEventListener` replaces the inline logging (keeps current behavior).
- `OwnerNotifier` (below) is just another listener.
- Wiring (`build_assistant_deps` in `interface/app.py`): construct
  `DispatchingEventPublisher([LoggingEventListener(...), OwnerNotifier(...)])` and pass it where
  `EventPublisher` is expected today. **One** wiring point; every appointment path already routes
  through the use cases that publish, so notifications fire from the assistant, the poller, and any
  future dashboard booking UI without further changes.

> The `except Exception` here is the deliberate, documented isolation boundary required by a
> fan‑out (§8.3 allows it *with* logging and an explicit decision). It is the only one in the feature.

### 6.1 Add the missing reschedule event

`RescheduleAppointment.__call__` currently publishes nothing. Add, consistent with the others:

```python
# application/ports.py
@dataclass(frozen=True, slots=True)
class AppointmentRescheduled(DomainEvent):
    appointment_id: AppointmentId

# application/appointments.py — RescheduleAppointment.__call__, after the move succeeds:
await self._events.publish(AppointmentRescheduled(moved.business_id, moved.id))
```

Events stay **minimal** (`business_id` + `appointment_id`) — handlers fetch fresh data, never act
on a stale snapshot. (Trade-off: the “old time” for a reschedule is not in the event; MVP shows the
**new** time only. Showing “moved from X to Y” would enrich the event with the previous slot — a
noted future option.)

---

## 7. The notifier (application service)

```python
# application/owner_notifier.py
_HANDLED = {                                  # registry, not an if/elif switch (§3.2 OCP)
    AppointmentBooked: NotificationEvent.BOOKED,
    AppointmentRescheduled: NotificationEvent.RESCHEDULED,
    AppointmentCancelled: NotificationEvent.CANCELLED,
}   # AppointmentConfirmed is intentionally absent — that is the owner's own action.

class OwnerNotifier:                          # implements EventListener
    """On a schedule change, message the business owner through their bot (if linked + enabled)."""
    def __init__(
        self,
        links: OwnerTelegramLinkRepository,
        appointments: AppointmentRepository,
        services: ServiceRepository,
        customers: CustomerRepository,
        businesses: BusinessRepository,
        sender: OwnerNotificationSender,
    ) -> None: ...

    async def on_event(self, event: DomainEvent) -> None:
        kind = _HANDLED.get(type(event))
        if kind is None:
            return
        link = await self._links.get(event.business_id)
        if link is None or not link.notifications_enabled:
            return
        message = await self._compose(kind, event.appointment_id, event.business_id)
        if message is not None:
            await self._sender.send(event.business_id, link.chat_id, message)
```

- `_compose` loads appointment → service → customer → business, then renders a **localized**
  template (per `business.locale`, mirroring `assistant._RECEIPT`). It marks pending bookings:
  *“⚠️ Needs your confirmation — open the dashboard.”*
- Six injected dependencies is acceptable for an *orchestrating* application service with a single
  responsibility (notify on a change). If `_compose` grows, split a `ScheduleChangeSummary`
  read/format service out (read deps move there; the notifier keeps link‑check + send). Noted, not
  done for MVP (YAGNI).
- Time is rendered in the **business** timezone via the existing `format_when` / `Clock`; all stored
  datetimes are UTC (§7.7).

Message templates (§7.8 — localized, in a constants table, not inline):

```python
# Example shape; full es/ru/zh provided in code.
_TEMPLATES = {
  ("en", NotificationEvent.BOOKED): "🆕 New booking: **{service}** — {when}\nCustomer: {customer}{confirm}",
  ("en", NotificationEvent.RESCHEDULED): "🔁 Rescheduled: **{service}** — now {when}\nCustomer: {customer}",
  ("en", NotificationEvent.CANCELLED): "❌ Cancelled: **{service}** — {when}\nCustomer: {customer}",
  # ...es / ru / zh...
}
_CONFIRM_SUFFIX = {"en": "\n⚠️ Needs your confirmation — open the dashboard.", ...}
```

### 7.1 The sender adapter

```python
# infrastructure/channels/telegram.py (sibling of telegram_send_message)
class TelegramOwnerNotificationSender:        # implements OwnerNotificationSender
    def __init__(self, bots: TelegramBotRepository, client: httpx.AsyncClient, base: str) -> None: ...
    async def send(self, business_id: BusinessId, chat_id: str, message: str) -> None:
        bot = await self._bots.get(business_id)
        if bot is None:
            _logger.warning("owner notification skipped: no bot for business=%s", business_id)
            return                            # not connected — nothing to send through
        await telegram_send_html(bot.bot_token, chat_id, markdown_to_telegram_html(message), self._client, self._base)
```

`telegram_send_html` is a thin sibling of the existing `telegram_send_message` that sets
`parse_mode=HTML` (reusing `markdown_to_telegram_html`). Best‑effort: logs and returns on
`httpx.HTTPError` (no exception escapes into the fan‑out).

---

## 8. Database & migrations

Two tables (one persistent binding, one ephemeral code), mirroring the `telegram_bot` pattern in
`schema.py`. New alembic migration **`0019_owner_telegram.py`**, idempotent (`CREATE TABLE IF NOT
EXISTS`), `down_revision = "0018"`. Also add the `CREATE` statements to `schema.py` (the canonical
schema used by migration 0001 + the integration conftest), per the established convention.

```sql
CREATE TABLE owner_telegram_link (
    business_id           text PRIMARY KEY REFERENCES business(id) ON DELETE CASCADE,
    chat_id               text NOT NULL,
    telegram_name         text NOT NULL,
    notifications_enabled boolean NOT NULL DEFAULT true,
    linked_at             timestamptz NOT NULL DEFAULT now()      -- §7.7 TIMESTAMPTZ
);

CREATE TABLE telegram_link_code (
    code           text PRIMARY KEY,                              -- the UUID
    business_id    text NOT NULL REFERENCES business(id) ON DELETE CASCADE,
    chat_id        text NOT NULL,
    telegram_name  text NOT NULL,
    expires_at     timestamptz NOT NULL,
    used           boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_link_code_expiry ON telegram_link_code (expires_at);
```

- `chat_id` stays text (consistent with `customer.address` holding the Telegram chat id).
- Repositories `SqlOwnerTelegramLinkRepository` / `SqlTelegramLinkCodeStore` follow the
  `SqlTelegramBotRepository` shape (`text()` SQL, `mappings().first()`, `ON CONFLICT` upsert).
- The link's `chat_id` is **not a secret** (it's the owner's own chat id) → no encryption needed,
  unlike the bot token. (PII‑adjacent: never logged — §11 Security.)
- Expired codes are pruned opportunistically on `issue`/`get` (a `DELETE ... WHERE expires_at < now`)
  — cheap, no separate job (KISS); the index keeps it fast.
- `import-linter`: domain imports nothing outward; the notifier (application) depends only on
  Protocols; adapters live in infrastructure — all three contracts stay green.

---

## 9. HTTP API (interface layer)

New router `interface/owner_telegram.py`, every endpoint behind `make_owner_guard` (session →
account → owns `{business_id}`), Pydantic models for all I/O (§2.3), rate‑limited on the mutating
ones (§ Security checklist). UUIDs via the injected `IdGenerator`; expiry via the injected `Clock`.

| Method & path | Body | Guard | Effect |
| --- | --- | --- | --- |
| `GET /api/businesses/{id}/telegram-owner` | — | owner | `{ linked, telegram_name, notifications_enabled }` |
| `POST /api/businesses/{id}/telegram-owner/confirm` | `{ code }` | owner + rate‑limit | redeem code → upsert link → mark used → `{ linked, telegram_name }`; `404` unknown, `410` expired/used, `409` wrong business |
| `PUT /api/businesses/{id}/telegram-owner/notifications` | `{ enabled }` | owner | toggle; `404` if not linked |
| `DELETE /api/businesses/{id}/telegram-owner` | — | owner | unlink |

Code **issuance** is **not** an HTTP endpoint — it happens inside the bot (§9.1), because the code
must be bound to the Telegram `chat_id`, which only the inbound update carries.

### 9.1 Telegram command interception

The link is requested from inside Telegram. In `telegram_inbound.handle`, **before** dispatching to
the assistant, check for the link command:

```python
OWNER_LINK_COMMAND = "/connect"   # named constant (could be a Settings field); matched exactly,
                                  # also accepting the "/connect@botusername" form Telegram appends.

# telegram_inbound.handle(bot, message):
if _is_link_command(message.text, bot.username):
    await self._owner_linking.start(bot.business_id, message)   # issue code + reply with link
    return                                                       # do NOT run the assistant
await self._assistant_for(bot).handle(message)
```

`OwnerLinking.start` (application service): build `TelegramLinkCode(uuid, business_id, chat_id,
telegram_name, now + LINK_CODE_TTL)`, `code_store.issue(...)`, then send the owner the dashboard
link `f"{settings.dashboard_url}/connect-telegram?code={uuid}"` via the bot. `dashboard_url` and
`LINK_CODE_TTL` come from `Settings`/a named constant — **no hardcoded URLs or numbers** (§7.1/§7.9).

> Giving any chat a code is harmless: a code is useless without an authenticated owner session at
> the confirm step (§10). The command is exact‑match, so normal customer text never triggers it.

---

## 10. Security

- **Binding requires both factors:** a valid owner **session** (proves the business owner) *and* a
  valid **code** (proves the Telegram chat). The confirm endpoint enforces `code.business_id == {id}`
  and that the session owns `{id}` (via the guard).
- **Identity shown before confirm:** the confirm response/screen displays the `telegram_name` being
  linked, so the owner verifies it is **their** account before enabling. This blocks the phishing
  variant where an attacker generates a code for *their* chat and tricks the owner into confirming
  it.
- **Codes:** one‑time (`used`), short‑lived (`LINK_CODE_TTL = 15 min`, a justified constant — long
  enough to switch apps, short enough to limit exposure; §8.6), single active code per chat
  (re‑issuing supersedes), pruned after expiry.
- **Rate limiting:** the `/connect` command (per chat) and `/confirm` (per IP) reuse the existing
  `RateLimiter` (§ Security checklist — new mutating surfaces).
- **No secrets/PII in logs:** never log the code, `chat_id`, or `telegram_name`. The bot token stays
  encrypted at rest (unchanged). The link `chat_id` is the owner's own id — stored plain, never
  logged.
- **Tenant isolation:** every read/write is scoped by `business_id`; cross‑business codes rejected.

---

## 11. Configuration (no hardcode — §7)

| Setting | Source | Default | Why |
| --- | --- | --- | --- |
| dashboard base URL for the link | `Settings.dashboard_url` (exists) | — | §7.9 no inline URLs |
| `LINK_CODE_TTL` | named constant (or `Settings`) | 15 min | §8.6 justified timeout |
| `OWNER_LINK_COMMAND` | named constant (or `Settings`) | `/connect` | §7.2 no magic string |
| notifications default on link | constant | `true` | the owner linked precisely to get alerts |

Everything is DI‑injected (`Clock`, `IdGenerator`, `Settings`, repositories, sender) — no global
singletons, no `os.getenv` sprinkled in code (§6, §7.3).

---

## 12. Frontend (dashboard)

Feature‑scoped, locale‑aware (§7.8), strict TS.

- **Settings → “Owner notifications” section:**
  - If **not linked**: instructions — “Open your business bot in Telegram, send `/connect`, then
    open the link it sends you here.” (The bot, not the dashboard, starts the flow.)
  - If **linked**: show the linked Telegram account + a **toggle** (calls `PUT …/notifications`) +
    an **Unlink** button (`DELETE`).
- **New page `/connect-telegram`** (owner‑authenticated; redirects to login and back if needed):
  reads `?code=…`, `POST`s `…/telegram-owner/confirm`, shows the linked account name + success, or a
  clear error (expired/used/wrong account). Strings in the i18n module for `en/es/ru/zh`.
- `api.ts`: `getOwnerTelegram`, `confirmOwnerTelegram(code)`, `setOwnerNotifications(enabled)`,
  `unlinkOwnerTelegram()` — typed, no `any`.

---

## 13. Testing (§10 — coverage is a merge gate)

- **Domain (100%):** `code_is_redeemable` (used / expired / wrong business / valid); template
  selection per locale + fallback.
- **Application / services (100% incl. error paths):**
  - `OwnerNotifier`: notifies on each handled event; **skips** when no link, when disabled, when the
    appointment is gone; ignores `AppointmentConfirmed`; marks pending bookings. Uses
    `InMemory*` fakes + a `FakeOwnerNotificationSender` that records sends.
  - `DispatchingEventPublisher`: fans out to all listeners; **one listener raising does not stop the
    others** and is logged.
  - `OwnerLinking.start`: issues a code with the right TTL (via `FixedClock`) and sends the link.
  - Confirm logic: valid redeem; rejects expired/used/wrong‑business.
- **Integration (real Postgres, ≥95%):** `SqlOwnerTelegramLinkRepository` and
  `SqlTelegramLinkCodeStore` round‑trips, `ON CONFLICT` upsert, expiry pruning; **migration 0019
  upgrades a clean DB** (the “migrate up works” test).
- **Interface (≥95%):** the four endpoints — guard rejects non‑owners (401/403), confirm
  happy‑path + 404/410/409, toggle, unlink; the `/connect` command interception (command →
  link issued + assistant **not** run; normal text → assistant runs). Sender adapter contract via
  recorded `httpx.MockTransport` (no live calls).
- **AI agent tools (100%):** unchanged — the command interception is verified to **bypass** the
  assistant, so the agent contract is untouched.
- All in‑memory **fakes**, not mocks; deterministic via `Clock`/`Random`/`IdGenerator` (§10.3).

---

## 14. Edge cases & decisions

- **Bot not connected** → sender logs and no‑ops (nothing to send through). Link can still be stored;
  notifications resume once a bot is connected.
- **Owner unlinks** → row removed; events stop notifying immediately.
- **Re‑link a different chat** → upsert overwrites (one owner chat per business; §1 non‑goal covers
  multi‑recipient).
- **Duplicate events** (retries) → at‑most‑best‑effort; a rare duplicate notice is low‑harm. A
  dedupe key is a noted future option, not MVP (YAGNI).
- **Latency** → the notification send is awaited inside the publishing call, *after* the appointment
  is committed and (for the assistant path) *after* the customer receipt is already sent; one bounded
  HTTP call with the client's timeout. Acceptable; not fire‑and‑forget (§8.7 — it is awaited and
  logged). If it ever needs to be off the request path, route it through the existing reminder
  worker — noted, not MVP.
- **Self‑actions** (owner books via a future dashboard UI) → still notified in MVP; the toggle is the
  escape hatch. De‑dup of self‑actions is a non‑goal.

---

## 15. Alternatives considered

**Deep‑link `t.me/<bot>?start=<code>` (browser → Telegram), recommended to evaluate.** The owner
generates the code from the **dashboard** (already authenticated); clicking the link opens Telegram
and sends `/start <code>`; the bot binds the presser's `chat_id`. This is the Telegram‑standard
pattern and is **more phishing‑resistant** (the code never leaves the owner's authenticated
dashboard, so there is no attacker‑supplied link to confirm). It needs `/start <param>` parsing in
`parse_telegram_inbound`/inbound handling and a code‑issuing endpoint on the dashboard. The
requested flow (§3.1, Telegram → browser) is fully viable with the identity‑confirmation mitigation
in §10; this alternative is documented so the trade‑off is an explicit, reversible choice.

---

## 16. File‑by‑file plan (review the doc, then implement in this order)

1. **Domain** — `LinkCode`, `NotificationEvent`, `OwnerTelegramLink`, `TelegramLinkCode`,
   `code_is_redeemable`; + `AppointmentRescheduled` event in `ports.py`. *(+ unit tests)*
2. **Application** — port Protocols (§5); `OwnerNotifier`, `OwnerLinking`; publish
   `AppointmentRescheduled` in `RescheduleAppointment`. *(+ unit tests with fakes)*
3. **Infrastructure** — `DispatchingEventPublisher` + `LoggingEventListener`; `Sql*` repos +
   `telegram_send_html` + `TelegramOwnerNotificationSender`; `InMemory*` fakes; `schema.py`
   tables; **migration 0019**. *(+ integration tests)*
4. **Interface** — `owner_telegram.py` router (4 endpoints); `/connect` interception in
   `telegram_inbound`; wire `DispatchingEventPublisher([... OwnerNotifier ...])` in
   `build_assistant_deps`/`app.py`. *(+ interface tests)*
5. **Frontend** — settings section + toggle + `/connect-telegram` page + `api.ts` + i18n
   (`en/es/ru/zh`). *(+ component/e2e tests)*
6. **Gates** — `make check` (ruff, mypy --strict, import‑linter, coverage), web gate, all green;
   ADR note if any rule is bent (none expected).

Each step is independently testable and leaves the build green before the next.
```
