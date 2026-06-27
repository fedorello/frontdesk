"use client";

import { type FormEvent, useState } from "react";

import { useI18n } from "@/app/lib/I18nProvider";
import { DemoNote } from "@/components/DemoNote";

import { ChatThread } from "./ChatThread";
import type { ChatMessage } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ChatPage() {
  const { t } = useI18n();
  const [session] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(event: FormEvent) {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || busy) return;

    setMessages((current) => [...current, { role: "user", text: trimmed }]);
    setText("");
    setBusy(true);
    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text: trimmed, session }),
      });
      const data = (await response.json()) as { reply: string; trace?: ChatMessage["trace"] };
      setMessages((current) => [
        ...current,
        { role: "assistant", text: data.reply, trace: data.trace },
      ]);
    } catch {
      setMessages((current) => [...current, { role: "assistant", text: t("chat.error") }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-6 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">{t("chat.title")}</h1>
      <div className="mt-4">
        <DemoNote />
      </div>

      <div className="mt-6 flex-1 overflow-y-auto rounded-xl border border-line bg-surface shadow-card p-4 ">
        <ChatThread messages={messages} />
        {busy && <p className="mt-3 text-sm text-faint">{t("chat.thinking")}</p>}
      </div>

      <form onSubmit={send} className="mt-4 flex gap-2">
        <input
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={t("chat.placeholder")}
          aria-label={t("chat.message")}
          className="flex-1 rounded-md border border-line-strong px-3 py-2 text-sm outline-none focus:border-zinc-500 dark:bg-accent"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-accent px-4 py-2.5 text-sm font-bold text-accent-contrast disabled:opacity-50"
        >
          {t("chat.send")}
        </button>
      </form>
    </main>
  );
}
