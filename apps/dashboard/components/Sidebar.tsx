"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { MessageKey } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { useTheme } from "@/app/lib/ThemeProvider";
import { Icon, type IconName } from "@/components/icons";

const NAV: { href: string; key: MessageKey; icon: IconName }[] = [
  { href: "/", key: "nav.overview", icon: "overview" },
  { href: "/conversations", key: "nav.conversations", icon: "conversations" },
  { href: "/calendar", key: "nav.calendar", icon: "calendar" },
  { href: "/approvals", key: "nav.approvals", icon: "approvals" },
  { href: "/settings", key: "nav.settings", icon: "settings" },
];

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function Sidebar() {
  const { t } = useI18n();
  const { theme, toggle } = useTheme();
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-surface px-3.5 pt-5 pb-4 sm:flex">
      <div className="flex items-center gap-3 px-2 pb-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-accent text-[17px] font-extrabold text-accent-contrast">
          t
        </div>
        <div className="leading-tight">
          <div className="text-base font-bold tracking-tight">tovayo</div>
          <div className="text-[11.5px] font-medium text-faint">{t("nav.appTagline")}</div>
        </div>
      </div>

      <nav className="flex flex-col gap-1">
        {NAV.map((item) => {
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

      <Link
        href="/chat"
        className="mt-3.5 flex items-center justify-center gap-2 rounded-xl border border-dashed border-line-strong px-3 py-2.5 text-[13px] font-bold text-accent"
      >
        <Icon name="spark" size={16} />
        {t("nav.tryAssistant")}
      </Link>

      <button
        type="button"
        onClick={toggle}
        className="mt-auto flex items-center justify-center gap-2 rounded-xl border border-line bg-surface-3 px-3 py-2.5 text-[13px] font-semibold text-muted"
      >
        <Icon name={theme === "dark" ? "sun" : "moon"} size={15} />
        {theme === "dark" ? t("common.light") : t("common.dark")}
      </button>
    </aside>
  );
}
