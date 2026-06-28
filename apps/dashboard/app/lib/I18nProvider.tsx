"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { api } from "./api";
import { DEFAULT_LOCALE, isLocale, type Locale, type MessageKey, translate } from "./i18n";
import { readLocaleCookie, writeLocaleCookie } from "./localeCookie";
import { getSession } from "./session";

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey, vars?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function readSharedLocale(): Locale | null {
  const fromCookie = readLocaleCookie();
  return fromCookie !== null && isLocale(fromCookie) ? fromCookie : null;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);

  useEffect(() => {
    // The shared cookie (also set by the marketing site) is the source of truth.
    const shared = readSharedLocale();
    if (shared !== null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- restore the shared language on mount
      setLocaleState(shared);
      return;
    }
    // No shared choice yet: signed-in owners fall back to the language saved on their
    // business (DB, cross-device), and that seeds the cookie so both sites agree afterwards.
    const session = getSession();
    const pending = session && api.getBusiness?.(session.businessId);
    if (!pending) return;
    pending
      .then((business) => {
        if (business.locale !== undefined && isLocale(business.locale)) {
          setLocaleState(business.locale);
          writeLocaleCookie(business.locale);
        }
      })
      .catch(() => {});
  }, []);

  const setLocale = (next: Locale) => {
    setLocaleState(next);
    writeLocaleCookie(next); // the shared source of truth (app + marketing site)
    const session = getSession();
    if (session !== null) {
      // Also persist on the business so it follows the owner across devices and drives the bot.
      void api.setLocale?.(session.businessId, next)?.catch(() => {});
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
