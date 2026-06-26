"use client";

import type { WorkingHours } from "@/app/lib/api";
import type { Locale } from "@/app/lib/i18n";

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
    <div className="space-y-1.5">
      {WEEKDAYS.map((weekday) => {
        const hours = value.find((h) => h.weekday === weekday);
        const label = weekdayLabel(weekday, locale);
        return (
          <div key={weekday} className="flex items-center gap-2 text-sm">
            <label className="flex w-32 shrink-0 items-center gap-2">
              <input
                type="checkbox"
                checked={hours !== undefined}
                onChange={(event) =>
                  setDay(
                    weekday,
                    event.target.checked
                      ? { weekday, opens: DEFAULT_OPEN, closes: DEFAULT_CLOSE }
                      : null,
                  )
                }
                className="accent-accent"
              />
              <span className="capitalize">{label}</span>
            </label>
            {hours !== undefined ? (
              <div className="flex items-center gap-1.5">
                <input
                  type="time"
                  aria-label={`${label} ·`}
                  value={toInput(hours.opens)}
                  onChange={(event) =>
                    setDay(weekday, { ...hours, opens: fromInput(event.target.value) })
                  }
                  className={timeInputClass}
                />
                <span className="text-muted">–</span>
                <input
                  type="time"
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
