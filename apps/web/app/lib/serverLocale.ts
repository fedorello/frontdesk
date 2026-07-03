import { cookies } from "next/headers";

import { LOCALES, type Locale } from "./locales";

// Server-side read of the shared language cookie, so server components (the legal pages) can pick
// localized content in the first render — no client flash. Defaults to English when unset/invalid.
export async function getLocale(): Promise<Locale> {
  const raw = (await cookies()).get("tovayo.locale")?.value;
  return (LOCALES as readonly string[]).includes(raw ?? "") ? (raw as Locale) : "en";
}
