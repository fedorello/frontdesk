import type { Locale } from "./i18n";

// Instants are stored in UTC; render them in the given IANA time zone (default UTC),
// locale-formatted — so the schedule shows the business's local wall-clock time.
export function formatTime(iso: string, locale: Locale, timeZone = "UTC"): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone,
  }).format(date);
}

export function formatDay(iso: string, locale: Locale, timeZone = "UTC"): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat(locale, {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone,
  }).format(date);
}
