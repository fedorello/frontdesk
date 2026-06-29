"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";

// The Telegram command the owner sends the bot to get a fresh link (matches the backend).
const LINK_COMMAND = "/connect";

type Phase = "confirming" | "success" | "failed";

export default function ConnectTelegramPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [phase, setPhase] = useState<Phase>("confirming");

  useEffect(() => {
    const session = getSession();
    if (session === null) {
      router.replace("/login"); // must be signed in as the owner to prove ownership
      return;
    }
    const code = new URLSearchParams(window.location.search).get("code");
    if (!code) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPhase("failed");
      return;
    }
    void (async () => {
      try {
        await api.confirmOwnerTelegram(session.businessId, code);
        setPhase("success");
      } catch {
        setPhase("failed"); // unknown/expired/used code — the owner requests a fresh one
      }
    })();
  }, [router]);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md flex-col items-center justify-center px-6 text-center">
      <h1 className="text-2xl font-bold">{t("settings.ownerNotificationsTitle")}</h1>
      {phase === "confirming" && (
        <p className="mt-4 text-muted">{t("connectTelegram.confirming")}</p>
      )}
      {phase === "success" && (
        <p className="mt-4 font-semibold text-success">{t("connectTelegram.success")}</p>
      )}
      {phase === "failed" && (
        <p role="alert" className="mt-4 text-danger">
          {t("connectTelegram.failed", { command: LINK_COMMAND })}
        </p>
      )}
      <a href="/settings" className="mt-6 text-sm font-semibold text-accent">
        {t("connectTelegram.back")}
      </a>
    </main>
  );
}
