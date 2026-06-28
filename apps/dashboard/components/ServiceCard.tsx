"use client";

import { useState } from "react";

import type { Group, ServiceInput } from "@/app/lib/api";
import { CURRENCIES } from "@/app/lib/currencies";
import { useI18n } from "@/app/lib/I18nProvider";
import { MAX_DESCRIPTION } from "@/app/lib/limits";

import { AutoTextarea } from "./AutoTextarea";
import { CharCount } from "./CharCount";
import { IntakeFieldsEditor } from "./IntakeFieldsEditor";
import { ToggleSwitch } from "./ToggleSwitch";

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
  groups,
  onSave,
  onRemove,
  onDuplicate,
  startOpen = false,
}: {
  service: Service;
  groups: Group[];
  onSave: (service: Service) => Promise<void>;
  onRemove: (id: string) => void;
  onDuplicate?: (service: Service) => void;
  startOpen?: boolean;
}) {
  const { t, locale } = useI18n();
  const [open, setOpen] = useState(startOpen);
  const [name, setName] = useState(service.name);
  const [description, setDescription] = useState(service.description ?? "");
  const [duration, setDuration] = useState(service.duration_minutes);
  const [amount, setAmount] = useState(service.price_cents != null ? service.price_cents / 100 : 0);
  const [currency, setCurrency] = useState(service.currency || "USD");
  // The single group this service belongs to (its schedule + calendar). Default to the first.
  const [groupId, setGroupId] = useState(service.resource_ids?.[0] ?? groups[0]?.id ?? "");
  const [maxAdvanceDays, setMaxAdvanceDays] = useState(service.max_advance_days ?? 30);
  const [intakeFields, setIntakeFields] = useState(service.intake_fields ?? []);
  const [requiresConfirmation, setRequiresConfirmation] = useState(
    service.requires_confirmation ?? false,
  );
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
        resource_ids: groupId ? [groupId] : [],
        max_advance_days: maxAdvanceDays,
        intake_fields: intakeFields.filter((item) => item.name.trim() !== ""),
        requires_confirmation: requiresConfirmation,
      });
      setOpen(false);
    } finally {
      setSaving(false);
    }
  };

  const price = priceLabel(service, locale);

  return (
    <div className="rounded-xl border border-line bg-canvas">
      <div className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="min-w-0 text-left sm:flex-1"
        >
          <span className="block font-semibold break-words">{service.name}</span>
          <span className="block text-sm text-muted">
            {service.duration_minutes} min{price ? ` · ${price}` : ""}
          </span>
          {service.description && (
            <span className="mt-0.5 block truncate text-xs text-muted">{service.description}</span>
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
          {onDuplicate && (
            <button
              type="button"
              onClick={() => onDuplicate(service)}
              className="text-ink hover:underline"
            >
              {t("settings.duplicate")}
            </button>
          )}
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
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{t("settings.serviceDescription")}</span>
              <CharCount value={description} max={MAX_DESCRIPTION} />
            </div>
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

          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("settings.group")}</span>
            <select
              aria-label={t("settings.group")}
              value={groupId}
              onChange={(event) => setGroupId(event.target.value)}
              className={fieldClass}
            >
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
            <span className="text-xs text-muted">{t("settings.groupHint")}</span>
          </label>

          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("settings.maxAdvanceDays")}</span>
            <input
              aria-label={t("settings.maxAdvanceDays")}
              type="number"
              min={1}
              value={maxAdvanceDays}
              onChange={(event) => setMaxAdvanceDays(Number(event.target.value))}
              className={fieldClass}
            />
            <span className="text-xs text-muted">{t("settings.maxAdvanceDaysHint")}</span>
          </label>

          <div className="space-y-2">
            <span className="text-sm font-medium">{t("settings.intakeTitle")}</span>
            <p className="text-xs text-muted">{t("settings.intakeHint")}</p>
            <IntakeFieldsEditor value={intakeFields} onChange={setIntakeFields} />
          </div>

          <div className="flex items-start justify-between gap-3 rounded-lg border border-line bg-canvas p-3">
            <div className="min-w-0">
              <span className="text-sm font-medium">{t("settings.requiresConfirmation")}</span>
              <p className="text-xs text-muted">{t("settings.requiresConfirmationHint")}</p>
            </div>
            <ToggleSwitch
              checked={requiresConfirmation}
              onChange={setRequiresConfirmation}
              label={t("settings.requiresConfirmation")}
            />
          </div>

          <button
            type="button"
            onClick={save}
            disabled={saving || name === "" || description.length > MAX_DESCRIPTION}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-bold text-accent-contrast disabled:opacity-50"
          >
            {saving ? t("common.saving") : t("settings.save")}
          </button>
        </div>
      )}
    </div>
  );
}
