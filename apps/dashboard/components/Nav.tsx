"use client";

import Link from "next/link";

import type { MessageKey } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { LanguageSwitcher } from "@/app/lib/LanguageSwitcher";

const LINKS: { href: string; key: MessageKey }[] = [
  { href: "/", key: "nav.overview" },
  { href: "/conversations", key: "nav.conversations" },
  { href: "/calendar", key: "nav.calendar" },
  { href: "/approvals", key: "nav.approvals" },
  { href: "/settings", key: "nav.settings" },
];

export function Nav() {
  const { t } = useI18n();
  return (
    <nav className="border-b border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center gap-1 px-6 py-3 text-sm">
        <span className="mr-2 font-semibold">tovayo</span>
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rounded-md px-3 py-1.5 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-100"
          >
            {t(link.key)}
          </Link>
        ))}
        <span className="ml-auto">
          <LanguageSwitcher />
        </span>
      </div>
    </nav>
  );
}
