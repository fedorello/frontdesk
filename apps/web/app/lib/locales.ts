// Plain (non-"use client") locale constants, so BOTH the server (root layout, reading the cookie)
// and the client i18n provider can import them. Values exported from a "use client" module become
// client references on the server, so they must live here instead.

export const LOCALES = ["en", "es", "ru", "zh"] as const;
export type Locale = (typeof LOCALES)[number];
export const LOCALE_NAMES: Record<Locale, string> = {
  en: "English",
  es: "Español",
  ru: "Русский",
  zh: "中文",
};
