"use client";

import { useState } from "react";

import { api } from "./api";
import { LOCALE_NAMES, LOCALES, type Locale } from "./i18n";
import { useI18n } from "./I18nProvider";
import { getSession } from "./session";

// Persist the owner's choice to the business so the bot + owner notifications speak it too;
// best-effort and only when signed in (the switcher also shows on login/onboarding).
function persistLocale(locale: Locale): void {
  const session = getSession();
  if (session !== null) void api.setLocale(session.businessId, locale).catch(() => {});
}

const GlobeIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.9"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18Z" />
  </svg>
);
const ChevronIcon = () => (
  <svg
    width="13"
    height="13"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.4"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="m6 9 6 6 6-6" />
  </svg>
);
const CheckIcon = () => (
  <svg
    width="13"
    height="13"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="3"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="m5 12 5 5L20 6" />
  </svg>
);

export function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Language"
        className="flex h-9 items-center gap-1.5 rounded-[10px] border border-line bg-surface px-2.5 text-sm font-bold text-muted transition hover:bg-surface-3"
      >
        <GlobeIcon />
        <span className="uppercase">{locale}</span>
        <ChevronIcon />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-2 w-36 rounded-xl border border-line bg-surface p-1 shadow-pop">
            {LOCALES.map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => {
                  setLocale(l);
                  persistLocale(l);
                  setOpen(false);
                }}
                className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm font-semibold transition ${
                  l === locale ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-3"
                }`}
              >
                {LOCALE_NAMES[l]}
                {l === locale && <CheckIcon />}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
