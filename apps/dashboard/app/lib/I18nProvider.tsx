"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { api } from "./api";
import { DEFAULT_LOCALE, isLocale, type Locale, type MessageKey, translate } from "./i18n";
import { getSession } from "./session";

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
    const fromStorage = () => {
      const stored = readStoredLocale();
      if (stored !== null) setLocaleState(stored);
    };
    const session = getSession();
    // Signed in: the business's saved language (persisted in DB) is the source of truth.
    const pending = session && api.getBusiness?.(session.businessId, session.token);
    if (!pending) {
      fromStorage();
      return;
    }
    pending
      .then((business) => {
        if (business.locale !== undefined && isLocale(business.locale)) {
          setLocaleState(business.locale);
        }
      })
      .catch(fromStorage);
  }, []);

  const setLocale = (next: Locale) => {
    setLocaleState(next);
    try {
      window.localStorage?.setItem(STORAGE_KEY, next);
    } catch {
      // storage unavailable (SSR / private mode) — keep the in-memory choice
    }
    const session = getSession();
    if (session !== null) {
      // Persist the choice so it follows the owner across devices and drives the bot.
      void api.setLocale?.(session.businessId, next, session.token)?.catch(() => {});
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
