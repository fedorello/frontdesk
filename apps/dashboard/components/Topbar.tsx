"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { MessageKey } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { LanguageSwitcher } from "@/app/lib/LanguageSwitcher";
import { clearSession, getSession } from "@/app/lib/session";
import { Icon } from "@/components/icons";

const TITLES: Record<string, MessageKey> = {
  "/": "nav.overview",
  "/conversations": "nav.conversations",
  "/calendar": "nav.calendar",
  "/approvals": "nav.approvals",
  "/settings": "nav.settings",
};

export function Topbar() {
  const { t } = useI18n();
  const router = useRouter();
  const pathname = usePathname();
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSignedIn(getSession() !== null);
  }, [pathname]);

  const logOut = () => {
    clearSession();
    setSignedIn(false);
    router.push("/login");
  };

  const titleKey = TITLES[pathname] ?? "nav.overview";

  return (
    <header className="flex shrink-0 items-center gap-4 border-b border-line bg-surface px-5 py-3.5 sm:px-8">
      <h1 className="text-[19px] font-bold tracking-tight">{t(titleKey)}</h1>
      <div className="ml-3 hidden max-w-sm flex-1 items-center gap-2 rounded-xl bg-surface-3 px-3.5 py-2.5 md:flex">
        <span className="text-faint">
          <Icon name="search" size={16} />
        </span>
        <input
          aria-label={t("common.search")}
          placeholder={t("common.search")}
          className="w-full border-none bg-transparent text-sm text-ink outline-none"
        />
      </div>
      <div className="ml-auto flex items-center gap-2.5">
        <LanguageSwitcher />
        {signedIn ? (
          <button
            type="button"
            onClick={logOut}
            className="rounded-lg border border-line-strong px-3 py-2 text-sm font-semibold text-muted hover:bg-surface-3"
          >
            {t("auth.logOut")}
          </button>
        ) : (
          <Link
            href="/login"
            className="rounded-lg bg-accent px-4 py-2 text-sm font-bold text-accent-contrast"
          >
            {t("onboarding.logIn")}
          </Link>
        )}
      </div>
    </header>
  );
}
