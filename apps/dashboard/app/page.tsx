"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/app/lib/api";
import type { MessageKey } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { Icon, type IconName } from "@/components/icons";

const LINKS: { href: string; key: MessageKey; icon: IconName }[] = [
  { href: "/calendar", key: "nav.calendar", icon: "calendar" },
  { href: "/conversations", key: "nav.conversations", icon: "conversations" },
  { href: "/settings", key: "nav.settings", icon: "settings" },
  { href: "/approvals", key: "nav.approvals", icon: "approvals" },
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
    <main className="mx-auto w-full max-w-5xl px-6 py-8 sm:px-8">
      {needsAuth && <p className="text-sm text-muted">{t("calendar.connectFirst")}</p>}

      {counts !== null && (
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard
            icon="calendar"
            tone="accent"
            label={t("overview.bookings")}
            value={counts.bookings}
          />
          <StatCard
            icon="conversations"
            tone="pink"
            label={t("overview.messages")}
            value={counts.messages}
          />
        </div>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="group flex items-center gap-4 rounded-2xl border border-line bg-surface p-5 shadow-card transition-shadow hover:shadow-pop"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface-3 text-muted group-hover:text-accent">
              <Icon name={link.icon} />
            </span>
            <span className="font-semibold">{t(link.key)}</span>
          </Link>
        ))}
      </div>
    </main>
  );
}

function StatCard({
  icon,
  tone,
  label,
  value,
}: {
  icon: IconName;
  tone: "accent" | "pink";
  label: string;
  value: number;
}) {
  const chip = tone === "accent" ? "bg-accent-soft text-accent" : "bg-pink-soft text-pink";
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-5 shadow-card">
      <span className={`flex h-12 w-12 items-center justify-center rounded-xl ${chip}`}>
        <Icon name={icon} size={22} />
      </span>
      <div>
        <div className="text-3xl font-extrabold tabular-nums leading-none">{value}</div>
        <div className="mt-1.5 text-sm text-muted">{label}</div>
      </div>
    </div>
  );
}
