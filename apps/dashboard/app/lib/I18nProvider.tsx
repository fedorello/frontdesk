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
    // Fast paint from the shared-cookie cache (it also bridges the marketing site).
    const cached = readSharedLocale();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- paint the cached language on mount
    if (cached !== null) setLocaleState(cached);
    // The single source of truth is the language saved on the business. A signed-in owner
    // reconciles the UI to it (and refreshes the cache); signed out there is no business, so the
    // cookie stands. This way the cookie can never silently diverge from the business.
    const session = getSession();
    if (session === null) return;
    const pending = api.getBusiness?.(session.businessId);
    if (pending === undefined) return;
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
    writeLocaleCookie(next); // refresh the cache (shared with the marketing site)
    const session = getSession();
    if (session !== null) {
      // The authoritative write: the business's language is the source of truth — it follows the
      // owner across devices and drives the bot + owner notifications.
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
