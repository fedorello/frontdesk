// The marketing site's canonical origin and shared metadata — one source of truth for
// metadataBase, Open Graph URLs, the sitemap, and robots. Override per environment with
// NEXT_PUBLIC_SITE_URL (no trailing slash); defaults to production.
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://tovayo.com";

export const SITE_TITLE =
  "Tovayo — a free AI front desk for your small business";

export const SITE_DESCRIPTION =
  "Tovayo answers customers, books appointments, and sends reminders — 24/7, in their " +
  "language. Free and open source, or hosted for you. Both free.";
