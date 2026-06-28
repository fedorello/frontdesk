"use client";

import { useState } from "react";

import { api, type AppointmentResult, type AppointmentView } from "@/app/lib/api";
import { isCancelled, PENDING, STATUS_LABEL } from "@/app/lib/appointments";
import { formatDay, formatTime, utcIsoToZonedInput, zonedToUtcIso } from "@/app/lib/format";
import type { Locale } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { StatusPill } from "@/components/ui/StatusPill";

const fieldClass =
  "w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent";

const CheckBadge = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    <circle cx="12" cy="12" r="9" />
    <path d="m8.5 12 2.5 2.5 4.5-5" />
  </svg>
);

export function AppointmentModal({
  appointment,
  timeZone,
  locale,
  businessId,
  onClose,
  onChanged,
}: {
  appointment: AppointmentView;
  timeZone: string;
  locale: Locale;
  businessId: string;
  onClose: () => void;
  onChanged: (result: AppointmentResult) => void;
}) {
  const { t } = useI18n();
  const [reason, setReason] = useState("");
  const [newTime, setNewTime] = useState(utcIsoToZonedInput(appointment.starts_at, timeZone));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cancelled = isCancelled(appointment.status);
  const statusLabel = STATUS_LABEL[appointment.status]
    ? t(STATUS_LABEL[appointment.status])
    : appointment.status;

  const run = async (action: () => Promise<AppointmentResult>) => {
    setBusy(true);
    setError(null);
    try {
      onChanged(await action());
    } catch {
      setError(t("calendar.actionFailed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      role="presentation"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={appointment.service}
        onClick={(event) => event.stopPropagation()}
        className="max-h-[90vh] w-full max-w-md overflow-auto rounded-2xl border border-line bg-surface p-5 shadow-pop"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-bold">{appointment.service}</h2>
            <p className="text-sm text-muted">
              {formatDay(appointment.starts_at, locale, timeZone)}{" "}
              {formatTime(appointment.starts_at, locale, timeZone)} ({timeZone})
            </p>
          </div>
          <StatusPill status={appointment.status} label={statusLabel} />
        </div>

        <p className="mt-2 break-all font-mono text-xs text-faint">
          {t("calendar.ref")}: {appointment.id}
        </p>

        {appointment.intake && appointment.intake.length > 0 && (
          <dl className="mt-3 space-y-1 rounded-lg border border-line bg-canvas p-3 text-sm">
            {appointment.intake.map((answer, index) => (
              <div key={index} className="flex gap-2">
                <dt className="shrink-0 text-muted">{answer.name}:</dt>
                <dd className="text-ink">{answer.value}</dd>
              </div>
            ))}
          </dl>
        )}

        {error && (
          <p role="alert" className="mt-3 rounded-lg bg-danger-soft p-2.5 text-sm text-danger">
            {error}
          </p>
        )}

        {cancelled ? (
          <p className="mt-4 text-sm text-muted">{t("calendar.statusCancelled")}</p>
        ) : (
          <div className="mt-4 space-y-5">
            {appointment.status === PENDING && (
              <div className="space-y-2.5 rounded-xl border border-success/40 bg-success-soft/40 p-3.5">
                <div className="flex items-center gap-2 text-sm font-semibold text-success">
                  <CheckBadge />
                  {t("calendar.awaitingConfirmation")}
                </div>
                <button
                  type="button"
                  onClick={() =>
                    run(async () => {
                      // Confirm only flips the status; the time is unchanged, so carry it over.
                      const result = await api.confirmAppointment(businessId, appointment.id);
                      return {
                        id: result.id,
                        status: result.status,
                        starts_at: appointment.starts_at,
                        ends_at: appointment.ends_at,
                      };
                    })
                  }
                  disabled={busy}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-success px-4 py-2.5 text-sm font-bold text-white transition hover:opacity-90 disabled:opacity-50"
                >
                  <CheckBadge />
                  {t("calendar.confirmBooking")}
                </button>
              </div>
            )}

            <div className="space-y-2">
              <span className="text-sm font-semibold">{t("calendar.reschedule")}</span>
              <input
                type="datetime-local"
                aria-label={t("calendar.newTime")}
                value={newTime}
                onChange={(event) => setNewTime(event.target.value)}
                className={fieldClass}
              />
              <button
                type="button"
                onClick={() =>
                  run(() =>
                    api.rescheduleAppointment(
                      businessId,
                      appointment.id,
                      zonedToUtcIso(newTime, timeZone),
                    ),
                  )
                }
                disabled={busy}
                className="rounded-lg bg-accent px-4 py-2 text-sm font-bold text-accent-contrast disabled:opacity-50"
              >
                {t("calendar.move")}
              </button>
            </div>

            <div className="space-y-2 border-t border-line pt-4">
              <span className="text-sm font-semibold">{t("calendar.cancelBooking")}</span>
              <textarea
                aria-label={t("calendar.cancelReason")}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder={t("calendar.cancelReasonPlaceholder")}
                rows={2}
                className={fieldClass}
              />
              <p className="text-xs text-muted">{t("calendar.cancelReasonHint")}</p>
              <button
                type="button"
                onClick={() => run(() => api.cancelAppointment(businessId, appointment.id, reason))}
                disabled={busy}
                className="rounded-lg bg-danger-soft px-4 py-2 text-sm font-bold text-danger disabled:opacity-50"
              >
                {t("calendar.cancelBooking")}
              </button>
            </div>
          </div>
        )}

        <button
          type="button"
          onClick={onClose}
          className="mt-5 w-full rounded-lg border border-line-strong px-4 py-2 text-sm font-medium hover:bg-canvas"
        >
          {t("common.close")}
        </button>
      </div>
    </div>
  );
}
