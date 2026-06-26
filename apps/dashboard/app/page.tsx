"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/app/lib/api";
import type { MessageKey } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";

const LINKS: { href: string; key: MessageKey }[] = [
  { href: "/calendar", key: "nav.calendar" },
  { href: "/conversations", key: "nav.conversations" },
  { href: "/settings", key: "nav.settings" },
  { href: "/approvals", key: "nav.approvals" },
];

export default function Home() {
  const { t } = useI18n();
  const [counts, setCounts] = useState<{ bookings: number; messages: number } | null>(null);
  const [needsAuth, setNeedsAuth] = useState(false);

  useEffect(() => {
    const session = getSession();
    if (session === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setNeedsAuth(true);
      return;
    }
    Promise.all([
      api.appointments(session.businessId, session.token),
      api.conversations(session.businessId, session.token),
    ])
      .then(([bookings, messages]) =>
        setCounts({ bookings: bookings.length, messages: messages.length }),
      )
      .catch(() => setCounts({ bookings: 0, messages: 0 }));
  }, []);

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">{t("nav.overview")}</h1>

      {needsAuth && <p className="mt-4 text-sm text-zinc-500">{t("calendar.connectFirst")}</p>}

      {counts !== null && (
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <Stat label={t("overview.bookings")} value={counts.bookings} />
          <Stat label={t("overview.messages")} value={counts.messages} />
        </div>
      )}

      <ul className="mt-10 grid gap-4 sm:grid-cols-2">
        {LINKS.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              className="block rounded-xl border border-zinc-200 p-5 hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-900"
            >
              <h2 className="font-medium">{t(link.key)}</h2>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
      <div className="text-3xl font-semibold tabular-nums">{value}</div>
      <div className="mt-1 text-sm text-zinc-500">{label}</div>
    </div>
  );
}
