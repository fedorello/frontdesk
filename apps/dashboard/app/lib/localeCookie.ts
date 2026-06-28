// The UI language, shared across the marketing site and the app via a cookie (see cookie.ts).
import { readCookie, writeCookie } from "./cookie";

const LOCALE_COOKIE = "tovayo.locale";

export function readLocaleCookie(): string | null {
  return readCookie(LOCALE_COOKIE);
}

export function writeLocaleCookie(locale: string): void {
  writeCookie(LOCALE_COOKIE, locale);
}
