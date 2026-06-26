"use client";

import { useEffect, useState } from "react";

import { api, type TelegramStatus } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";

/** Sidebar card: live Telegram bot health for the signed-in business. */
export function BotStatus() {
  const { t } = useI18n();
  const [status, setStatus] = useState<TelegramStatus | null>(null);

  useEffect(() => {
    const session = getSession();
    if (session === null) {
      return;
    }
    api
      .telegramStatus(session.businessId, session.token)
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

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
