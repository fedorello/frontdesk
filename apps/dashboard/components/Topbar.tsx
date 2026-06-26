"use client";

import { usePathname } from "next/navigation";

import type { MessageKey } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { LanguageSwitcher } from "@/app/lib/LanguageSwitcher";
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
  const pathname = usePathname();
  const titleKey = TITLES[pathname] ?? "nav.overview";

  return (
    <header className="flex shrink-0 items-center gap-4 border-b border-line bg-surface px-5 py-3.5 sm:px-8">
      <div className="text-[19px] font-bold tracking-tight">{t(titleKey)}</div>
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
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-pink-soft text-sm font-extrabold text-pink">
          M
        </div>
      </div>
    </header>
  );
}
