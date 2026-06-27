"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useI18n } from "@/app/lib/I18nProvider";
import { useTheme } from "@/app/lib/ThemeProvider";
import { BotStatus } from "@/components/BotStatus";
import { Icon } from "@/components/icons";
import { Logo } from "@/components/Logo";
import { isActive, NAV_ITEMS } from "@/components/nav-items";

export function Sidebar() {
  const { t } = useI18n();
  const { theme, toggle } = useTheme();
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-surface px-3.5 pt-5 pb-4 sm:flex">
      <div className="flex items-center gap-2.5 px-2 pb-5">
        <Logo size={34} />
        <div className="leading-tight">
          <div className="text-base font-extrabold tracking-tight">Tovayo</div>
          <div className="text-[11.5px] font-medium text-faint">{t("nav.appTagline")}</div>
        </div>
      </div>

      <nav className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
                active
                  ? "bg-accent-soft text-accent"
                  : "text-muted hover:bg-surface-3 hover:text-ink"
              }`}
            >
              <Icon name={item.icon} />
              {t(item.key)}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto space-y-2.5">
        <BotStatus />
        <button
          type="button"
          onClick={toggle}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-line bg-surface-3 px-3 py-2.5 text-[13px] font-semibold text-muted"
        >
          <Icon name={theme === "dark" ? "sun" : "moon"} size={15} />
          {theme === "dark" ? t("common.light") : t("common.dark")}
        </button>
      </div>
    </aside>
  );
}
