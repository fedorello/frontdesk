"use client";

import type { MessageKey } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";

const POINT_KEYS: MessageKey[] = [
  "chat.demoPoint1",
  "chat.demoPoint2",
  "chat.demoPoint3",
  "chat.demoPoint4",
];

export function DemoNote() {
  const { t } = useI18n();
  return (
    <aside className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-sm dark:border-zinc-800 dark:bg-zinc-900/50">
      <h2 className="font-medium">{t("chat.demoTitle")}</h2>
      <p className="mt-1 text-zinc-500">
        {t("chat.demoIntro", { studio: "Ana Studio", service: "Haircut" })}
      </p>
      <ul className="mt-3 space-y-1.5 text-zinc-600 dark:text-zinc-300">
        {POINT_KEYS.map((key) => (
          <li key={key} className="flex gap-2">
            <span aria-hidden>•</span>
            <span>{t(key)}</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
