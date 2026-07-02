"use client";

import type { IntakeField } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";

export const MAX_INTAKE_FIELDS = 5;

const field =
  "w-full rounded-md border border-line-strong bg-surface px-2.5 py-1.5 text-sm text-ink outline-none focus:border-accent";

// Edits up to 5 questions the assistant collects from the customer before booking.
export function IntakeFieldsEditor({
  value,
  onChange,
}: {
  value: IntakeField[];
  onChange: (fields: IntakeField[]) => void;
}) {
  const { t } = useI18n();

  const patch = (index: number, change: Partial<IntakeField>) =>
    onChange(value.map((item, i) => (i === index ? { ...item, ...change } : item)));
  const remove = (index: number) => onChange(value.filter((_, i) => i !== index));
  const add = () =>
    onChange([...value, { name: "", description: "", ask: "", normalize: "" }]);

  return (
    <div className="space-y-2">
      {value.map((item, index) => (
        <div key={index} className="space-y-2 rounded-lg border border-line bg-canvas p-3">
          <div className="flex items-center gap-2">
            <input
              aria-label={t("settings.intakeName")}
              value={item.name}
              onChange={(event) => patch(index, { name: event.target.value })}
              placeholder={t("settings.intakeName")}
              className={`${field} font-medium`}
            />
            <button
              type="button"
              onClick={() => remove(index)}
              className="shrink-0 text-xs text-danger hover:underline"
            >
              {t("settings.remove")}
            </button>
          </div>
          <input
            aria-label={t("settings.intakeDescription")}
            value={item.description ?? ""}
            onChange={(event) => patch(index, { description: event.target.value })}
            placeholder={t("settings.intakeDescription")}
            className={field}
          />
          <input
            aria-label={t("settings.intakeAsk")}
            value={item.ask ?? ""}
            onChange={(event) => patch(index, { ask: event.target.value })}
            placeholder={t("settings.intakeAsk")}
            className={field}
          />
          <input
            aria-label={t("settings.intakeNormalize")}
            value={item.normalize ?? ""}
            onChange={(event) => patch(index, { normalize: event.target.value })}
            placeholder={t("settings.intakeNormalize")}
            className={field}
          />
        </div>
      ))}
      {value.length < MAX_INTAKE_FIELDS && (
        <button
          type="button"
          onClick={add}
          className="rounded-md border border-line-strong px-3 py-1.5 text-sm font-medium hover:bg-canvas"
        >
          + {t("settings.addIntakeField")}
        </button>
      )}
    </div>
  );
}
