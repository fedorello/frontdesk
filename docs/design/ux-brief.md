# Frontdesk — UI/UX brief

A brief for designing the Frontdesk web dashboard. It describes **what screens are
needed and what each must do** — not how they should look. Visual design (layout,
colour, type, components, branding) is yours. Please design for the flows and states
below.

---

## The product, in one paragraph

Frontdesk is an **AI receptionist** for small, appointment-based service businesses
(salons, clinics, tutors, studios). A business owner connects their own **Telegram**
bot; from then on the AI answers customers' messages, books appointments into a
calendar, sends reminders to reduce no-shows, and flags anything sensitive (like a
refund) for the owner to approve. This dashboard is where the owner **sets up** their
assistant and **watches and controls** what it does.

## Who uses it

The **business owner** (or a staff member) — typically non-technical, often on a
phone as much as a laptop. They are busy and want setup to be fast and obvious.

---

## Cross-cutting requirements (apply to every screen)

- **Multilingual — critical.** The whole UI must support multiple languages
  (initially English, Spanish, Russian, Chinese; more later). Design so that:
  - every piece of user-facing text is translatable (no text baked into images);
  - layouts tolerate **text 2–3× longer** than English without breaking;
  - there is a clear **language switcher**;
  - the design can accommodate **right-to-left** languages later.
- **Responsive:** must work well on both mobile and desktop.
- **States for every screen:** design the **loading**, **empty**, **error**, and
  **success/confirmation** states — not just the “full of data” happy path.
- **Accessibility:** legible contrast, clear focus states, usable with a keyboard.
- **Trust & clarity:** owners are handing the AI their customers and (for refunds)
  their money — the UI should make it obvious what the AI did and what needs a human.

---

## The screens

### 1. Sign up
Create an account. Purpose: get a new owner started.
Content: email, password (or a “magic link” email option). Link to log in.
States: validation errors, “check your email” if using magic links.

### 2. Log in
Return to an existing account. Includes a **forgot password / reset** path.

### 3. Onboarding wizard
A short, guided, multi-step setup shown right after first sign-up. The owner can do
steps in order and see progress. Each step is simple and skippable-where-sensible,
with a clear “you're done” at the end. Steps:

1. **Business profile** — business name, time zone, and **default language** (the
   language the assistant uses for first contact and reminders).
2. **Services** — add one or more services the business offers: name, duration, and
   (optional) price. At least one is required.
3. **Working hours** — when the business is open (per weekday; may differ by day).
4. **Knowledge base** — a few question/answer facts the assistant may use (e.g.
   “Where are you located?”, “Do you take card?”). The assistant only answers from
   these — empty is allowed but discouraged.
5. **Choose your AI** — how the assistant is powered. Two paths: use the **included
   default** (zero setup — we provide the model) or **bring your own provider** (pick
   OpenAI / Anthropic / OpenRouter, choose a model, and paste an API key). After
   pasting a key, show whether it **validated** or **failed**. The key is
   **write-only**: once saved it's shown only as a masked hint (e.g. `…ab12`), never
   in full. Make the trade-off clear (own key = your account/your bill; default =
   instant start).
6. **Connect Telegram** — the key step. The owner needs guidance to: create a bot in
   Telegram (via BotFather), copy the bot **token**, and paste it here. After pasting,
   show whether the connection **succeeded** (and the bot's name) or **failed**
   (invalid token). Once connected, the assistant is live.
7. **Done** — confirmation, a link to message/test their own bot, and into the
   dashboard.

Design the wizard's **progress**, the **per-step validation/errors**, and a way to
**come back later** if they leave mid-setup.

### 4. Overview / Home
The landing screen after onboarding. At-a-glance status:
- Is the Telegram bot **connected and healthy**?
- Today's appointments (a count and/or a short list).
- **Pending approvals** that need the owner (highlight if any).
- Recent activity (latest conversations/bookings).
Empty state: a friendly “nothing yet — share your bot with customers” nudge.

### 5. Conversations
A list of customer conversations (most recent first), and a way to open one to read
the **full thread**: what the customer wrote and how the assistant replied. Optionally
surface what the assistant **did** (checked availability, booked, escalated). Read-only
is fine for v1.
States: empty (no conversations yet), long threads, a conversation the assistant
**escalated** to a human (make that stand out).

### 6. Calendar / Appointments
The business's appointments — today and upcoming. The owner can see each appointment's
time, service, customer, and **status** (pending / confirmed / cancelled). A detail
view per appointment. (Editing/rescheduling from here is a plus, not required for v1.)
States: empty day, a full day, cancelled items.

### 7. Approvals
The inbox of **sensitive actions** the assistant flagged and is **holding** until a
human decides (e.g. a refund). Each item shows: a plain summary, the underlying action
and its details, and **Approve** / **Reject** actions. Approving/rejecting resolves and
removes it. This screen is about **trust and control** — make the “nothing runs until
you approve” idea clear.
States: empty (“nothing waiting — 🎉”), one or many items, the moment after a decision.

### 8. Settings
Grouped settings the owner manages over time. Sections:
- **Business profile** — name, time zone, default language.
- **Services** — add / edit / remove (same data as onboarding).
- **Working hours** — edit.
- **Knowledge base** — add / edit / remove Q&A entries.
- **AI provider** — choose the included **default** or **bring your own** (OpenAI /
  Anthropic / OpenRouter + model + API key). The saved key shows only as a masked
  hint with a “replace” / “remove” action; never the full key. A way to **test** the
  current provider.
- **Channels** — the **Telegram** connection: status, bot name, **reconnect** /
  **disconnect**, and re-paste a token. (Space for other channels later — keep it
  extensible; do not design WhatsApp now.)
- **Account** — email, change password, and the owner's **UI language** preference.
- *(Future, leave room but don't design now: team members, billing.)*

### 9. “Try your assistant” (preview)
A simple way for the owner to chat with their own assistant from the dashboard to test
it (a chat box; the assistant answers and can book as a real customer would). Helpful
during and after onboarding. Optional but valuable.

---

## Global shell

- Primary **navigation** between the main areas (Overview, Conversations, Calendar,
  Approvals, Settings) plus the **language switcher** and an account/sign-out control.
- A clear indicator when the **bot is disconnected** (so the owner notices their
  assistant is offline).

## What we'll do with this

Hand us the designs (any format — Figma, images, a prototype). We implement them in
the existing Next.js dashboard. So: focus on **screens, flows, content, and states**;
we'll handle the engineering. If a flow is unclear or you think a screen is missing,
flag it — this brief is the starting point, not the last word.
