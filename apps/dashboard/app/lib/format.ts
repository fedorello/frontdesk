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

// Interpret a naive "YYYY-MM-DDTHH:mm" (from <input type=datetime-local>) as a wall-clock
// time in `timeZone`, and return the matching UTC instant as ISO. Used so the owner enters
// the business's local time regardless of their own browser zone.
export function zonedToUtcIso(local: string, timeZone: string): string {
  const asIfUtc = new Date(`${local}:00Z`);
  const inZone = new Date(asIfUtc.toLocaleString("en-US", { timeZone }));
  const inUtc = new Date(asIfUtc.toLocaleString("en-US", { timeZone: "UTC" }));
  return new Date(asIfUtc.getTime() + (inUtc.getTime() - inZone.getTime())).toISOString();
}

// The inverse: a UTC ISO instant → "YYYY-MM-DDTHH:mm" wall-clock in `timeZone`, for
// pre-filling a datetime-local input.
export function utcIsoToZonedInput(iso: string, timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(new Date(iso));
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "00";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
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
