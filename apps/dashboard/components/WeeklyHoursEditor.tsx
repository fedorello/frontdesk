"use client";

import type { WorkingHours } from "@/app/lib/api";
import type { Locale } from "@/app/lib/i18n";

import { ToggleSwitch } from "./ToggleSwitch";

const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6]; // Monday = 0
const DEFAULT_OPEN = "09:00:00";
const DEFAULT_CLOSE = "17:00:00";

// Localized weekday name. 2024-01-01 is a Monday, so weekday 0 lands on Monday.
function weekdayLabel(weekday: number, locale: Locale): string {
  const date = new Date(Date.UTC(2024, 0, 1 + weekday));
  return new Intl.DateTimeFormat(locale, { weekday: "long", timeZone: "UTC" }).format(date);
}

const toInput = (value: string): string => value.slice(0, 5); // "HH:MM:SS" -> "HH:MM"
const fromInput = (value: string): string => (value.length === 5 ? `${value}:00` : value);

const timeInputClass = "rounded-md border border-line-strong bg-surface px-2 py-1 text-ink";

export function WeeklyHoursEditor({
  value,
  onChange,
  locale,
  closedLabel,
}: {
  value: WorkingHours[];
  onChange: (hours: WorkingHours[]) => void;
  locale: Locale;
  closedLabel: string;
}) {
  const setDay = (weekday: number, hours: WorkingHours | null) => {
    const next = value.filter((h) => h.weekday !== weekday);
    if (hours) next.push(hours);
    next.sort((a, b) => a.weekday - b.weekday);
    onChange(next);
  };

  return (
    <div className="divide-y divide-line rounded-xl border border-line">
      {WEEKDAYS.map((weekday) => {
        const hours = value.find((h) => h.weekday === weekday);
        const label = weekdayLabel(weekday, locale);
        const isOpen = hours !== undefined;
        return (
          <div
            key={weekday}
            className={`flex h-14 items-center gap-3 px-3 text-sm ${isOpen ? "" : "opacity-60"}`}
          >
            <ToggleSwitch
              checked={isOpen}
              label={label}
              onChange={(open) =>
                setDay(
                  weekday,
                  open ? { weekday, opens: DEFAULT_OPEN, closes: DEFAULT_CLOSE } : null,
                )
              }
            />
            <span className="w-28 shrink-0 capitalize">{label}</span>
            {isOpen ? (
              <div className="flex items-center gap-1.5">
                <input
                  type="time"
                  aria-label={`${label} — from`}
                  value={toInput(hours.opens)}
                  onChange={(event) =>
                    setDay(weekday, { ...hours, opens: fromInput(event.target.value) })
                  }
                  className={timeInputClass}
                />
                <span className="text-muted">–</span>
                <input
                  type="time"
                  aria-label={`${label} — to`}
                  value={toInput(hours.closes)}
                  onChange={(event) =>
                    setDay(weekday, { ...hours, closes: fromInput(event.target.value) })
                  }
                  className={timeInputClass}
                />
              </div>
            ) : (
              <span className="text-muted">{closedLabel}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
