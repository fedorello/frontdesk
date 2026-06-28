// Cookies shared across the marketing site and the app. They live on the registrable domain
// (.tovayo.com spans tovayo.com + app.tovayo.com), so a preference set on one is the source of
// truth for the other — which localStorage (per-origin) cannot do. Host-only on localhost,
// where cookies ignore the port so the two dev servers still share them.

const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

function domainAttribute(): string {
  const override = process.env.NEXT_PUBLIC_COOKIE_DOMAIN;
  if (override) return `; Domain=${override}`;
  const host = window.location.hostname;
  const labels = host.split(".");
  if (/^[0-9.]+$/.test(host) || labels.length < 2) return ""; // localhost / IP -> host-only
  return `; Domain=.${labels.slice(-2).join(".")}`;
}

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  for (const part of document.cookie.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return null;
}

export function writeCookie(name: string, value: string): void {
  if (typeof document === "undefined") return;
  document.cookie =
    `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${ONE_YEAR_SECONDS}` +
    `; SameSite=Lax${domainAttribute()}`;
}
