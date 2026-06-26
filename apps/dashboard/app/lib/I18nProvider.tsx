"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { DEFAULT_LOCALE, isLocale, type Locale, type MessageKey, translate } from "./i18n";

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey, vars?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);
const STORAGE_KEY = "tovayo.locale";

function readStoredLocale(): Locale | null {
  try {
    const stored = window.localStorage?.getItem(STORAGE_KEY);
    return stored !== null && stored !== undefined && isLocale(stored) ? stored : null;
  } catch {
    return null;
  }
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);

  useEffect(() => {
    const stored = readStoredLocale();
    if (stored !== null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLocaleState(stored);
    }
  }, []);

  const setLocale = (next: Locale) => {
    setLocaleState(next);
    try {
      window.localStorage?.setItem(STORAGE_KEY, next);
    } catch {
      // storage unavailable (SSR / private mode) — keep the in-memory choice
    }
  };

  const t = (key: MessageKey, vars?: Record<string, string | number>) =>
    translate(locale, key, vars);

  return <I18nContext.Provider value={{ locale, setLocale, t }}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (context === null) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return context;
}
