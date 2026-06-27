"use client";

import { useI18n } from "@/app/lib/I18nProvider";

// Shows how many characters remain, or — once past the limit — how many over (in red).
export function CharCount({ value, max }: { value: string; max: number }) {
  const { t } = useI18n();
  const remaining = max - value.length;
  const over = remaining < 0;
  return (
    <span className={`text-xs ${over ? "font-medium text-danger" : "text-muted"}`}>
      {over
        ? t("settings.charsOver", { n: -remaining })
        : t("settings.charsLeft", { n: remaining })}
    </span>
  );
}
