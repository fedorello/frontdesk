import type { Metadata } from "next";

import { LegalShell } from "@/components/LegalShell";

export const metadata: Metadata = { title: "Privacy Policy — Tovayo" };

const PRIVACY = `# Privacy Policy

_Last updated: 27 June 2026_

> **In short:** To run your AI front desk, we store your business settings and the
> **conversations** between your bot and your customers on our servers — that's how the
> assistant remembers context and books appointments. You can **delete your account and
> everything in it at any time**, permanently.

This policy covers the **hosted service at tovayo.com**. If you self-host the open-source
code, you run your own database and this policy does not apply — you are the data controller.

## 1. What we store

- **Account data** — your email and a hashed password.
- **Business profile** — name, owner name, time zone, description, address / online flag,
  services, working hours, FAQ, and your chosen language.
- **Connection secrets** — your Telegram bot token and (optional) your own AI API key,
  **encrypted at rest**.
- **Customers** — for each person who messages your bot: their channel id, display name (if
  the channel provides one), and language.
- **Conversations** — the full message history between your bot, your customers, the AI
  assistant, and you, stored so the assistant has context across messages.
- **Bookings** — appointments and the intake answers you configured to collect, plus reminders.
- **Operational counters** — minimal usage counts for cost control and diagnostics.

We do **not** sell your data, and we do **not** use your conversations to train our own models.

## 2. Why we store it

Solely to operate the Service for you: answer customers, schedule and remind, give you a
dashboard, prevent abuse, and keep the system running.

## 3. Who else processes it

To function, message content and related data are shared with an **AI model provider** (to
generate replies), your **messaging channel** (e.g. Telegram), and our **hosting provider**
(where the servers and database run). These act as processors for running the Service.

## 4. How long we keep it

We keep your data while your account is active. **When you delete your account, we permanently
erase your business and all associated records** — conversations, customers, bookings,
services, settings, and connection secrets — in one irreversible operation.

## 5. Your choices and rights

- **Delete everything, anytime.** Settings → *Danger zone* → *Delete account* removes your
  account and all its data, permanently. There is no undo.
- **Access / correction.** You can view and edit your business data in the dashboard at any time.
- Depending on where you live, you may have additional rights (access, erasure, portability,
  objection). Contact us to exercise them.

## 6. Your customers' data

Your customers' messages and details are data **you** bring into the Service. You are
responsible for having a lawful basis to process them (see the [Terms](/terms), §5). When you
delete your account, their data tied to your business is deleted too.

## 7. Security

Secrets (bot tokens, API keys) are encrypted at rest, and access is restricted to the running
Service. No system is perfectly secure, but we take reasonable measures to protect your data.

## 8. Children

The Service is for businesses and is not directed at children. Don't use it to collect data
from children unlawfully.

## 9. Changes

We may update this policy; material changes will be announced in-product or on tovayo.com.

## 10. Contact

Privacy questions or requests: **privacy@tovayo.com**.
`;

export default function PrivacyPage() {
  return <LegalShell content={PRIVACY} />;
}
