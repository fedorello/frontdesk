"use client";

import { useState } from "react";

import type { ServiceInput } from "@/app/lib/api";
import { CURRENCIES } from "@/app/lib/currencies";
import { useI18n } from "@/app/lib/I18nProvider";

import { AutoTextarea } from "./AutoTextarea";
import { WeeklyHoursEditor } from "./WeeklyHoursEditor";

export type Service = ServiceInput & { id: string };

const fieldClass =
  "w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent";

function priceLabel(service: Service, locale: string): string | null {
  if (service.price_cents == null || !service.currency) return null;
  return new Intl.NumberFormat(locale, { style: "currency", currency: service.currency }).format(
    service.price_cents / 100,
  );
}

export function ServiceCard({
  service,
  onSave,
  onRemove,
  startOpen = false,
}: {
  service: Service;
  onSave: (service: Service) => Promise<void>;
  onRemove: (id: string) => void;
  startOpen?: boolean;
}) {
  const { t, locale } = useI18n();
  const [open, setOpen] = useState(startOpen);
  const [name, setName] = useState(service.name);
  const [description, setDescription] = useState(service.description ?? "");
  const [duration, setDuration] = useState(service.duration_minutes);
  const [amount, setAmount] = useState(service.price_cents != null ? service.price_cents / 100 : 0);
  const [currency, setCurrency] = useState(service.currency || "USD");
  const [hours, setHours] = useState(service.working_hours ?? []);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await onSave({
        id: service.id,
        name,
        description,
        duration_minutes: duration,
        price_cents: Math.round(amount * 100),
        currency,
        working_hours: hours,
      });
      setOpen(false);
    } finally {
      setSaving(false);
    }
  };

  const price = priceLabel(service, locale);

  return (
    <div className="rounded-xl border border-line bg-canvas">
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <button type="button" onClick={() => setOpen(!open)} className="min-w-0 flex-1 text-left">
          <span className="font-semibold">{service.name}</span>
          <span className="ml-2 text-sm text-muted">
            {service.duration_minutes} min{price ? ` · ${price}` : ""}
          </span>
          {service.description && (
            <span className="block truncate text-xs text-muted">{service.description}</span>
          )}
        </button>
        <div className="flex shrink-0 items-center gap-3 text-xs">
          <button
            type="button"
            onClick={() => setOpen(!open)}
            className="text-accent hover:underline"
          >
            {open ? t("common.close") : t("settings.edit")}
          </button>
          <button
            type="button"
            onClick={() => onRemove(service.id)}
            className="text-danger hover:underline"
          >
            {t("settings.remove")}
          </button>
        </div>
      </div>

      {open && (
        <div className="space-y-4 border-t border-line px-4 py-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1">
              <span className="text-sm font-medium">{t("onboarding.serviceName")}</span>
              <input
                aria-label={t("onboarding.serviceName")}
                value={name}
                onChange={(event) => setName(event.target.value)}
                className={fieldClass}
              />
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium">{t("onboarding.duration")}</span>
              <input
                aria-label={t("onboarding.duration")}
                type="number"
                value={duration}
                onChange={(event) => setDuration(Number(event.target.value))}
                className={fieldClass}
              />
            </label>
          </div>

          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("settings.serviceDescription")}</span>
            <AutoTextarea
              ariaLabel={t("settings.serviceDescription")}
              value={description}
              onChange={setDescription}
              className={fieldClass}
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1">
              <span className="text-sm font-medium">{t("settings.price")}</span>
              <input
                aria-label={t("settings.price")}
                type="number"
                min={0}
                step="0.01"
                value={amount}
                onChange={(event) => setAmount(Number(event.target.value))}
                className={fieldClass}
              />
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium">{t("settings.currency")}</span>
              <select
                aria-label={t("settings.currency")}
                value={currency}
                onChange={(event) => setCurrency(event.target.value)}
                className={fieldClass}
              >
                {CURRENCIES.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">{t("settings.serviceSchedule")}</span>
            <WeeklyHoursEditor
              value={hours}
              onChange={setHours}
              locale={locale}
              closedLabel={t("settings.closed")}
            />
          </div>

          <button
            type="button"
            onClick={save}
            disabled={saving || name === ""}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-bold text-accent-contrast disabled:opacity-50"
          >
            {saving ? t("common.saving") : t("settings.save")}
          </button>
        </div>
      )}
    </div>
  );
}
