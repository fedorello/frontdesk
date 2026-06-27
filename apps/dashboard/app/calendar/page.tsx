"use client";

import { useEffect, useState } from "react";

import { api, type AppointmentView } from "@/app/lib/api";
import { formatDay, formatTime } from "@/app/lib/format";
import type { Locale, MessageKey } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatusPill } from "@/components/ui/StatusPill";

type LoadState = "loading" | "anon" | "ready";
const MINUTES_PER_HOUR = 60;

// Backend AppointmentStatus values → localized chip labels.
const STATUS_LABEL: Record<string, MessageKey> = {
  pending: "calendar.statusPending",
  confirmed: "calendar.statusConfirmed",
  completed: "calendar.statusCompleted",
  cancelled: "calendar.statusCancelled",
};

function durationMinutes(startsAt: string, endsAt: string): number {
  const minutes =
    (new Date(endsAt).getTime() - new Date(startsAt).getTime()) / (1000 * MINUTES_PER_HOUR);
  return Number.isFinite(minutes) ? Math.round(minutes) : 0;
}

export default function CalendarPage() {
  const { t, locale } = useI18n();
  const [state, setState] = useState<LoadState>("loading");
  const [appointments, setAppointments] = useState<AppointmentView[]>([]);
  const [timeZone, setTimeZone] = useState("UTC");

  useEffect(() => {
    const session = getSession();
    if (session === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState("anon");
      return;
    }
    void (async () => {
      const [items, business] = await Promise.all([
        api.appointments(session.businessId, session.token).catch(() => []),
        api.getBusiness(session.businessId, session.token).catch(() => null),
      ]);
      setAppointments(items);
      if (business) setTimeZone(business.timezone);
      setState("ready");
    })();
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
          {appointments.map((appointment) => (
            <AppointmentCard
              key={appointment.id}
              appointment={appointment}
              locale={locale}
              timeZone={timeZone}
              refLabel={t("calendar.ref")}
              statusLabel={
                STATUS_LABEL[appointment.status]
                  ? t(STATUS_LABEL[appointment.status])
                  : appointment.status
              }
            />
          ))}
        </div>
      )}
    </main>
  );
}

function AppointmentCard({
  appointment,
  locale,
  timeZone,
  refLabel,
  statusLabel,
}: {
  appointment: AppointmentView;
  locale: Locale;
  timeZone: string;
  refLabel: string;
  statusLabel: string;
}) {
  const minutes = durationMinutes(appointment.starts_at, appointment.ends_at);
  return (
    <div className="flex items-stretch gap-4 rounded-2xl border border-line bg-surface p-4 shadow-card">
      <div className="flex min-w-16 flex-col items-center justify-center border-r border-line pr-4 text-center">
        <span className="text-xs font-medium capitalize text-muted">
          {formatDay(appointment.starts_at, locale, timeZone)}
        </span>
        <span className="font-extrabold tabular-nums">
          {formatTime(appointment.starts_at, locale, timeZone)}
        </span>
        <span className="text-xs text-faint">{minutes}m</span>
      </div>
      <div className="flex min-w-0 flex-1 flex-col justify-center">
        <span className="font-semibold">{appointment.service}</span>
        <span className="font-mono text-xs text-faint" title={appointment.id}>
          {refLabel}: {appointment.id}
        </span>
        {appointment.intake && appointment.intake.length > 0 && (
          <dl className="mt-1.5 space-y-0.5">
            {appointment.intake.map((answer, index) => (
              <div key={index} className="flex gap-1.5 text-xs">
                <dt className="shrink-0 text-muted">{answer.name}:</dt>
                <dd className="truncate text-ink">{answer.value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
      <div className="flex items-center">
        <StatusPill status={appointment.status} label={statusLabel} />
      </div>
    </div>
  );
}
