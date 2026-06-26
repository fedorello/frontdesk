"use client";

import { useEffect, useState } from "react";

import { api, type AppointmentView } from "@/app/lib/api";
import { formatTime } from "@/app/lib/format";
import type { Locale } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatusPill } from "@/components/ui/StatusPill";

type LoadState = "loading" | "anon" | "ready";
const MINUTES_PER_HOUR = 60;

function durationMinutes(startsAt: string, endsAt: string): number {
  const minutes =
    (new Date(endsAt).getTime() - new Date(startsAt).getTime()) / (1000 * MINUTES_PER_HOUR);
  return Number.isFinite(minutes) ? Math.round(minutes) : 0;
}

export default function CalendarPage() {
  const { t, locale } = useI18n();
  const [state, setState] = useState<LoadState>("loading");
  const [appointments, setAppointments] = useState<AppointmentView[]>([]);

  useEffect(() => {
    const session = getSession();
    if (session === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState("anon");
      return;
    }
    api
      .appointments(session.businessId, session.token)
      .catch(() => [])
      .then((items) => {
        setAppointments(items);
        setState("ready");
      });
  }, []);

  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-8 sm:px-8">
      {state === "loading" && (
        <div className="space-y-3">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      )}

      {state === "anon" && <EmptyState icon="calendar" title={t("calendar.connectFirst")} />}

      {state === "ready" && appointments.length === 0 && (
        <EmptyState icon="calendar" title={t("calendar.empty")} />
      )}

      {state === "ready" && appointments.length > 0 && (
        <div className="space-y-2.5">
          {appointments.map((appointment, index) => (
            <AppointmentCard key={index} appointment={appointment} locale={locale} />
          ))}
        </div>
      )}
    </main>
  );
}

function AppointmentCard({
  appointment,
  locale,
}: {
  appointment: AppointmentView;
  locale: Locale;
}) {
  const minutes = durationMinutes(appointment.starts_at, appointment.ends_at);
  return (
    <div className="flex items-stretch gap-4 rounded-2xl border border-line bg-surface p-4 shadow-card">
      <div className="flex min-w-14 flex-col items-center justify-center border-r border-line pr-4">
        <span className="font-extrabold tabular-nums">
          {formatTime(appointment.starts_at, locale)}
        </span>
        <span className="text-xs text-faint">{minutes}m</span>
      </div>
      <div className="flex flex-1 flex-col justify-center">
        <span className="font-semibold">{appointment.service}</span>
      </div>
      <div className="flex items-center">
        <StatusPill status={appointment.status} />
      </div>
    </div>
  );
}
