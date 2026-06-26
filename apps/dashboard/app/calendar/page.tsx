"use client";

import { useEffect, useState } from "react";

import { api, type AppointmentView } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";

const STATUS_STYLES: Record<string, string> = {
  confirmed: "text-success",
  pending: "text-warning",
  cancelled: "text-faint line-through",
};

function formatTime(iso: string): string {
  // "2026-06-26T13:00:00+00:00" → "13:00"
  const match = /T(\d{2}:\d{2})/.exec(iso);
  return match ? match[1] : iso;
}

export default function CalendarPage() {
  const { t } = useI18n();
  const [appointments, setAppointments] = useState<AppointmentView[] | null>(null);
  const [needsAuth, setNeedsAuth] = useState(false);

  useEffect(() => {
    const session = getSession();
    if (session === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setNeedsAuth(true);
      return;
    }
    api
      .appointments(session.businessId, session.token)
      .then(setAppointments)
      .catch(() => setAppointments([]));
  }, []);

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">{t("nav.calendar")}</h1>

      {needsAuth && <p className="mt-6 text-sm text-muted">{t("calendar.connectFirst")}</p>}

      {!needsAuth && appointments !== null && appointments.length === 0 && (
        <p className="mt-6 text-sm text-muted">{t("calendar.empty")}</p>
      )}

      {appointments !== null && appointments.length > 0 && (
        <ul className="mt-8 divide-y divide-line">
          {appointments.map((appointment, index) => (
            <li key={index} className="flex items-center justify-between py-3">
              <div>
                <span className="font-medium tabular-nums">
                  {formatTime(appointment.starts_at)}
                </span>
                <span className="text-muted"> · {appointment.service}</span>
              </div>
              <span className={`text-sm ${STATUS_STYLES[appointment.status] ?? "text-muted"}`}>
                {appointment.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
