"use client";

import { LOCALE_NAMES, LOCALES, type Locale } from "./i18n";
import { useI18n } from "./I18nProvider";

export function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();
  return (
    <select
      value={locale}
      onChange={(event) => setLocale(event.target.value as Locale)}
      aria-label="Language"
      className="rounded-md border border-zinc-300 bg-transparent px-2 py-1 text-sm dark:border-zinc-700"
    >
      {LOCALES.map((option) => (
        <option key={option} value={option}>
          {LOCALE_NAMES[option]}
        </option>
      ))}
    </select>
  );
}
