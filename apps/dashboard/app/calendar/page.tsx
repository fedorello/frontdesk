"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { api, type AppointmentView } from "@/app/lib/api";
import { readCache, writeCache } from "@/app/lib/cache";
import { PENDING, STATUS_LABEL } from "@/app/lib/appointments";
import { formatDay, formatTime } from "@/app/lib/format";
import type { Locale } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { AppointmentModal } from "@/components/AppointmentModal";
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

function CalendarContent() {
  const { t, locale } = useI18n();
  const searchParams = useSearchParams();
  const query = (searchParams.get("q") ?? "").trim();
  const [state, setState] = useState<LoadState>("loading");
  const [items, setItems] = useState<AppointmentView[]>([]);
  const [total, setTotal] = useState(0);
  const [timeZone, setTimeZone] = useState("UTC");
  const [showCancelled, setShowCancelled] = useState(false);
  const [page, setPage] = useState(0);
  const [reload, setReload] = useState(0);
  const [selected, setSelected] = useState<AppointmentView | null>(null);
  const session = getSession();
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  // A new search (from the Topbar, via the URL) starts back at the first page. Adjusting state
  // during render is the React-sanctioned way to react to a changed input without an effect.
  const [lastQuery, setLastQuery] = useState(query);
  if (query !== lastQuery) {
    setLastQuery(query);
    setPage(0);
  }

  // Fetch ONE page from the server — the list is never pulled in full, so it scales to any volume.
  useEffect(() => {
    const current = getSession();
    if (current === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState("anon");
      return;
    }
    const bid = current.businessId;
    const isFirstView = page === 0 && !showCancelled && query === "";
    const key = `calendar.${bid}`;
    // Stale-while-revalidate, but only for the default landing view (first page, no filter/search).
    if (isFirstView) {
      const cached = readCache<{ items: AppointmentView[]; total: number; timeZone: string }>(key);
      if (cached) {
        setItems(cached.items);
        setTotal(cached.total);
        setTimeZone(cached.timeZone);
        setState("ready");
      }
    }
    void (async () => {
      const [pageData, business] = await Promise.all([
        api
          .appointments(bid, {
            limit: PAGE_SIZE,
            offset: page * PAGE_SIZE,
            includeCancelled: showCancelled,
            q: query,
          })
          .catch(() => ({ items: [], total: 0 })),
        api.getBusiness(bid).catch(() => null),
      ]);
      const tz = business ? business.timezone : "UTC";
      setItems(pageData.items);
      setTotal(pageData.total);
      setTimeZone(tz);
      setState("ready");
      if (isFirstView) {
        writeCache(key, { items: pageData.items, total: pageData.total, timeZone: tz });
      }
    })();
  }, [page, showCancelled, query, reload]);

  // Confirm a pending booking, then refetch so status/order/membership stay correct on this page.
  const confirm = async (appointmentId: string) => {
    const current = getSession();
    if (current === null) return;
    await api.confirmAppointment(current.businessId, appointmentId);
    setReload((value) => value + 1);
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

      {state === "ready" && (
        <>
          <label className="mb-4 flex items-center justify-end gap-2 text-sm">
            <span className="text-muted">{t("calendar.showCancelled")}</span>
            <ToggleSwitch
              checked={showCancelled}
              onChange={(show) => {
                setShowCancelled(show);
                setPage(0);
              }}
              label={t("calendar.showCancelled")}
            />
          </label>

          {items.length === 0 ? (
            <EmptyState
              icon={query ? "search" : "calendar"}
              title={query ? t("common.noResults") : t("calendar.empty")}
            />
          ) : (
            <div className="space-y-2.5">
              {items.map((appointment) => (
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
                  onOpen={() => setSelected(appointment)}
                />
              ))}
            </div>
          )}

          {pageCount > 1 && (
            <Pagination
              page={page}
              pageCount={pageCount}
              onPage={setPage}
              prevLabel={t("calendar.prev")}
              nextLabel={t("calendar.next")}
            />
          )}
        </>
      )}

      {selected && session && (
        <AppointmentModal
          appointment={selected}
          timeZone={timeZone}
          locale={locale}
          businessId={session.businessId}
          onClose={() => setSelected(null)}
          onChanged={() => {
            setSelected(null);
            setReload((value) => value + 1); // a cancel/reschedule can change this page's membership
          }}
        />
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
  onOpen,
}: {
  appointment: AppointmentView;
  locale: Locale;
  timeZone: string;
  refLabel: string;
  statusLabel: string;
  onConfirm?: (appointmentId: string) => Promise<void>;
  confirmLabel: string;
  onOpen: () => void;
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
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-stretch gap-4 p-4 text-left transition hover:bg-canvas"
      >
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
      </button>
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
