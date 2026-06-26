"use client";

import { useEffect, useState } from "react";

import { api, type MessageView } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";

export default function ConversationsPage() {
  const { t } = useI18n();
  const [messages, setMessages] = useState<MessageView[] | null>(null);
  const [needsAuth, setNeedsAuth] = useState(false);

  useEffect(() => {
    const session = getSession();
    if (session === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setNeedsAuth(true);
      return;
    }
    api
      .conversations(session.businessId, session.token)
      .then(setMessages)
      .catch(() => setMessages([]));
  }, []);

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">{t("nav.conversations")}</h1>

      {needsAuth && <p className="mt-6 text-sm text-zinc-500">{t("conversations.connectFirst")}</p>}

      {!needsAuth && messages !== null && messages.length === 0 && (
        <p className="mt-6 text-sm text-zinc-500">{t("conversations.empty")}</p>
      )}

      {messages !== null && messages.length > 0 && (
        <ul className="mt-8 space-y-3">
          {messages.map((message, index) => (
            <li key={index} className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
              <div className="text-xs text-zinc-500">{message.customer}</div>
              <p className="mt-1 text-sm">
                <span className="text-zinc-500">{message.role}:</span> {message.text}
              </p>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
