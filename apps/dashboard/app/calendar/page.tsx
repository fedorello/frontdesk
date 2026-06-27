"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { api, type AppointmentView } from "@/app/lib/api";
import { isCancelled, PENDING, STATUS_LABEL } from "@/app/lib/appointments";
import { formatDay, formatTime } from "@/app/lib/format";
import type { Locale } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { Icon } from "@/components/icons";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatusPill } from "@/components/ui/StatusPill";
import { ToggleSwitch } from "@/components/ToggleSwitch";

// Authenticated, client-data page that reads the ?q= search param — never static.
export const dynamic = "force-dynamic";

export default function CalendarPage() {
  return (
    <Suspense>
      <CalendarContent />
    </Suspense>
  );
}

type LoadState = "loading" | "anon" | "ready";
const MINUTES_PER_HOUR = 60;
const PAGE_SIZE = 8;

function durationMinutes(startsAt: string, endsAt: string): number {
  const minutes =
    (new Date(endsAt).getTime() - new Date(startsAt).getTime()) / (1000 * MINUTES_PER_HOUR);
  return Number.isFinite(minutes) ? Math.round(minutes) : 0;
}

// Search a booking by service, booking code, or any captured intake field/answer.
function matchesQuery(appointment: AppointmentView, query: string): boolean {
  return (
    appointment.service.toLowerCase().includes(query) ||
    appointment.id.toLowerCase().includes(query) ||
    (appointment.intake ?? []).some(
      (answer) =>
        answer.name.toLowerCase().includes(query) || answer.value.toLowerCase().includes(query),
    )
  );
}

function CalendarContent() {
  const { t, locale } = useI18n();
  const searchParams = useSearchParams();
  const [state, setState] = useState<LoadState>("loading");
  const [appointments, setAppointments] = useState<AppointmentView[]>([]);
  const [timeZone, setTimeZone] = useState("UTC");
  const [showCancelled, setShowCancelled] = useState(false);
  const [page, setPage] = useState(0);

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

  // Confirm a pending booking; apply the status the server actually returns (no optimism).
  const confirm = async (appointmentId: string) => {
    const session = getSession();
    if (session === null) return;
    const result = await api.confirmAppointment(session.businessId, appointmentId, session.token);
    setAppointments((previous) =>
      previous.map((item) =>
        item.id === appointmentId ? { ...item, status: result.status } : item,
      ),
    );
  };

  const cancelledCount = appointments.filter((item) => isCancelled(item.status)).length;
  const afterCancel = showCancelled
    ? appointments
    : appointments.filter((item) => !isCancelled(item.status));
  const query = (searchParams.get("q") ?? "").trim().toLowerCase();
  const visible = query ? afterCancel.filter((item) => matchesQuery(item, query)) : afterCancel;
  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const paged = visible.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  const toggleCancelled = (show: boolean) => {
    setShowCancelled(show);
    setPage(0);
  };

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
        <>
          {cancelledCount > 0 && (
            <label className="mb-4 flex items-center justify-end gap-2 text-sm">
              <span className="text-muted">{t("calendar.showCancelled")}</span>
              <ToggleSwitch
                checked={showCancelled}
                onChange={toggleCancelled}
                label={t("calendar.showCancelled")}
              />
            </label>
          )}

          {visible.length === 0 ? (
            <EmptyState
              icon={query ? "search" : "calendar"}
              title={query ? t("common.noResults") : t("calendar.empty")}
            />
          ) : (
            <div className="space-y-2.5">
              {paged.map((appointment) => (
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
                  onConfirm={appointment.status === PENDING ? confirm : undefined}
                  confirmLabel={t("calendar.confirm")}
                />
              ))}
            </div>
          )}

          {pageCount > 1 && (
            <Pagination
              page={safePage}
              pageCount={pageCount}
              onPage={setPage}
              prevLabel={t("calendar.prev")}
              nextLabel={t("calendar.next")}
            />
          )}
        </>
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
  onConfirm,
  confirmLabel,
}: {
  appointment: AppointmentView;
  locale: Locale;
  timeZone: string;
  refLabel: string;
  statusLabel: string;
  onConfirm?: (appointmentId: string) => Promise<void>;
  confirmLabel: string;
}) {
  const minutes = durationMinutes(appointment.starts_at, appointment.ends_at);
  const [confirming, setConfirming] = useState(false);

  const handleConfirm = async () => {
    if (!onConfirm) return;
    setConfirming(true);
    try {
      await onConfirm(appointment.id);
    } finally {
      setConfirming(false); // re-enable on failure so the owner can retry
    }
  };
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
      <div className="flex items-stretch gap-4 p-4">
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
      {onConfirm && (
        <button
          type="button"
          onClick={handleConfirm}
          disabled={confirming}
          className="flex w-full items-center justify-center gap-2 border-t border-line bg-success-soft px-4 py-3 text-sm font-semibold text-success transition hover:brightness-105 disabled:opacity-60"
        >
          <Icon name="check" size={18} />
          {confirmLabel}
        </button>
      )}
    </div>
  );
}
