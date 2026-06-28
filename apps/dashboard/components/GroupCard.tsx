"use client";

import { useState } from "react";

import type { Group, WorkingHours } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";

import { WeeklyHoursEditor } from "./WeeklyHoursEditor";

const fieldClass =
  "w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent";

// A service group: one specialist/calendar with a name and a weekly schedule shared by all
// its services. Editing the schedule here changes availability for every service in the group.
export function GroupCard({
  group,
  onSave,
  onRemove,
  startOpen = false,
}: {
  group: Group;
  onSave: (group: Group) => Promise<void>;
  onRemove: (id: string) => void;
  startOpen?: boolean;
}) {
  const { t, locale } = useI18n();
  const [open, setOpen] = useState(startOpen);
  const [name, setName] = useState(group.name);
  const [hours, setHours] = useState<WorkingHours[]>(group.working_hours ?? []);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await onSave({ id: group.id, name, working_hours: hours });
      setOpen(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-line bg-canvas">
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <button type="button" onClick={() => setOpen(!open)} className="min-w-0 flex-1 text-left">
          <span className="block font-semibold break-words">{group.name}</span>
          <span className="block text-sm text-muted">{t("settings.groupScheduleHint")}</span>
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
            onClick={() => onRemove(group.id)}
            className="text-danger hover:underline"
          >
            {t("settings.remove")}
          </button>
        </div>
      </div>

      {open && (
        <div className="space-y-4 border-t border-line px-4 py-4">
          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("settings.groupName")}</span>
            <input
              aria-label={t("settings.groupName")}
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={fieldClass}
            />
          </label>

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
