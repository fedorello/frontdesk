"use client";

import { useBotStatus } from "@/app/lib/BotStatusProvider";
import { useI18n } from "@/app/lib/I18nProvider";

/** Sidebar card: live Telegram bot health, from the shared BotStatus source. */
export function BotStatus() {
  const { t } = useI18n();
  const { status } = useBotStatus();

  if (status === null) {
    return null;
  }

  const tone = status.connected ? "text-success" : "text-danger";
  return (
    <div className="rounded-xl border border-line bg-surface-2 px-3 py-2.5">
      <div className={`flex items-center gap-2 text-xs font-bold ${tone}`}>
        <span className="h-2 w-2 rounded-full bg-current" />
        {status.connected ? t("bot.online") : t("bot.offline")}
      </div>
      {status.username && <div className="mt-0.5 text-[11px] text-faint">@{status.username}</div>}
    </div>
  );
}
