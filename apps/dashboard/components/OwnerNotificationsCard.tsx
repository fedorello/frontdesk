"use client";

import type { OwnerTelegram } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";
import { ToggleSwitch } from "@/components/ToggleSwitch";

// The Telegram command the owner sends the bot to start linking (matches the backend).
const LINK_COMMAND = "/connect";

export function OwnerNotificationsCard({
  status,
  onToggle,
  onUnlink,
}: {
  status: OwnerTelegram;
  onToggle: (enabled: boolean) => void;
  onUnlink: () => void;
}) {
  const { t } = useI18n();
  return (
    <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
      <h2 className="font-bold">{t("settings.ownerNotificationsTitle")}</h2>
      <p className="mt-2 text-sm text-muted">{t("settings.ownerNotificationsHint")}</p>
      {status.linked ? (
        <div className="mt-3 space-y-3">
          <p className="text-sm font-semibold text-success">
            {t("settings.ownerNotificationsLinked", { name: status.telegram_name ?? "" })}
          </p>
          <div className="flex items-center justify-between gap-3 rounded-lg border border-line bg-canvas p-3">
            <span className="text-sm font-medium">{t("settings.ownerNotificationsToggle")}</span>
            <ToggleSwitch
              checked={status.notifications_enabled}
              onChange={onToggle}
              label={t("settings.ownerNotificationsToggle")}
            />
          </div>
          <button type="button" onClick={onUnlink} className="text-sm font-semibold text-danger">
            {t("settings.ownerNotificationsUnlink")}
          </button>
        </div>
      ) : (
        <p className="mt-3 rounded-lg bg-canvas p-3 text-sm text-muted">
          {t("settings.ownerNotificationsHowto", { command: LINK_COMMAND })}
        </p>
      )}
    </section>
  );
}
