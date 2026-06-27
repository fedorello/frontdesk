# Landing page — designer brief (Tovayo)

> **For:** the designer building the public marketing/landing page.
> **Product:** Tovayo — a free, open-source AI receptionist for small service
> businesses. Hosted at **tovayo.com**; source code is public and MIT-licensed.

---

## 1. One-line positioning

**Tovayo is a free AI front desk for your small business — it answers customers,
books appointments, and sends reminders, 24/7, in their language.**

Two ways to get it, and **both are free**:

1. **Use the open source.** Take the code, run it yourself, change anything —
   including for commercial use. (MIT license.)
2. **Use the hosted service at tovayo.com.** Nothing to install. **Free and
   unlimited** — just connect your Telegram bot and go. (Fair use under the
   [Terms of Service](legal/TERMS_OF_SERVICE.md).)

The page must make it obvious that there is **no paywall** and **no "contact
sales"** — it's genuinely free, on purpose, because the project is open source.

## 2. Who it's for

Solo owners and tiny teams who run on messaging: salons, barbers, tutors,
coaches, astrologers, therapists, nail techs, clinics, repair shops. People who
lose bookings because they can't reply fast enough, and who don't want a clunky
CRM.

## 3. Tone & feel

- Warm, plain-spoken, confident. Field-note voice, not corporate.
- "It just works" and "you actually own it." Open-source pride without jargon.
- Calm, modern, lots of whitespace. The dashboard already has a clean dark/light
  design system — match its palette (accent blue, soft surfaces, rounded 2xl
  cards, subtle shadows). Reuse those tokens.

## 4. Page sections (top to bottom)

1. **Hero** — the one-liner above, a short subhead, and two primary CTAs:
   - `Start free` → sign up on the hosted app.
   - `View on GitHub` → the repo.
   - Small trust line under the buttons: "Free & unlimited · Open source · No
     card required."

2. **Live demo** — an embedded chat widget talking to a real demo business
   ("Ana Studio", one service: Haircut, with a working demo schedule). The
   visitor can actually ask for times and book — it shows the agent's reasoning
   and tool calls under each reply. **This is the hero proof; give it room.**
   _(Engineering note: the demo must run against a dedicated demo business with
   its own services and a live, always-bookable schedule — not the owner's real
   data.)_

3. **How it works** — 3 steps with icons:
   1. Sign up & describe your business (or self-host).
   2. Connect your Telegram bot (paste one token).
   3. Customers message your bot — Tovayo answers, books, and reminds.

4. **What it does** — feature grid (use simple icons):
   - Answers questions from your own info & FAQ.
   - Books, reschedules, and cancels real appointments.
   - Collects the details you need before booking (e.g. birth date for an
     astrologer).
   - Sends reminders to cut no-shows.
   - You can jump into any chat and reply as yourself; the AI steps aside.
   - Four languages out of the box (English, Spanish, Russian, Chinese).

5. **Open source vs hosted** — two side-by-side cards:
   - **Self-host (free forever):** full control, your servers, your data,
     commercial use allowed, MIT license. CTA → GitHub.
   - **Hosted at tovayo.com (free & unlimited):** zero setup, we run it, your
     data on our servers, deletable anytime. CTA → Start free.
   - Make clear these are equal first-class options, not "free vs paid".

6. **Trust & data** — short, honest block: conversations are stored on our
   servers so the assistant has context; you can delete your account and **all**
   your data at any time, irreversibly. Link to
   [Privacy Policy](legal/PRIVACY_POLICY.md) and
   [Terms of Service](legal/TERMS_OF_SERVICE.md).

7. **FAQ** — "Is it really free?", "Can I use it for my business commercially?",
   "Where is my data?", "Can I delete everything?", "Which channels?
   (Telegram today; WhatsApp planned)", "Do I need to know how to code?
   (No, for hosted)".

8. **Footer** — links: GitHub, Docs, Terms, Privacy, Status. Brand line: "Tovayo
   — open-source AI front desk."

## 5. Primary CTAs (in priority order)

1. **Start free** (hosted sign-up).
2. **View on GitHub** (self-host).
3. **Try the live demo** (scroll/anchor to the demo).

## 6. Must-say messages (don't lose these)

- Free. Unlimited. No card.
- Open source — take it and use it however you want, including commercially.
- Or just use tovayo.com — we host it for you, also free.
- Your data lives on our servers; you can wipe it anytime.
- Use it for what it's for (a real front desk) — see the Terms.

## 7. Out of scope for v1

Pricing tables (there is no price), testimonials we don't have yet, blog (the
dashboard already has one). Keep it to one focused page.
