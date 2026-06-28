// The single source of truth for the UI language, shared across the marketing site and the
// app. localStorage is per-origin (can't cross tovayo.com <-> app.tovayo.com), so we use a
// cookie on the registrable domain (.tovayo.com spans both). On localhost it's host-only —
// and cookies ignore the port, so the two dev servers still share it. NEXT_PUBLIC_COOKIE_DOMAIN
// can override the derived domain for non-standard setups.

const COOKIE_NAME = "tovayo.locale";
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

function domainAttribute(): string {
  const override = process.env.NEXT_PUBLIC_COOKIE_DOMAIN;
  if (override) return `; Domain=${override}`;
  const host = window.location.hostname;
  const labels = host.split(".");
  if (/^[0-9.]+$/.test(host) || labels.length < 2) return ""; // localhost / IP -> host-only
  return `; Domain=.${labels.slice(-2).join(".")}`;
}

export function readLocaleCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)tovayo\.locale=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function writeLocaleCookie(locale: string): void {
  if (typeof document === "undefined") return;
  document.cookie =
    `${COOKIE_NAME}=${encodeURIComponent(locale)}; Path=/; Max-Age=${ONE_YEAR_SECONDS}` +
    `; SameSite=Lax${domainAttribute()}`;
}
