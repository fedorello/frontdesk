"use client";

import { useEffect, useState } from "react";

import { api, type MessageView } from "@/app/lib/api";
import { formatTime } from "@/app/lib/format";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import type { Locale } from "@/app/lib/i18n";

type LoadState = "loading" | "anon" | "ready";

interface Thread {
  customer: string;
  last: string;
}

// The feed is newest-first; keep each customer's first (latest) message.
function toThreads(messages: MessageView[]): Thread[] {
  const seen = new Set<string>();
  const threads: Thread[] = [];
  for (const message of messages) {
    if (!seen.has(message.customer)) {
      seen.add(message.customer);
      threads.push({ customer: message.customer, last: message.text });
    }
  }
  return threads;
}

// One customer's messages, oldest-first, without internal tool steps.
function threadMessages(messages: MessageView[], customer: string): MessageView[] {
  return messages
    .filter((message) => message.customer === customer && message.role !== "tool")
    .slice()
    .reverse();
}

export default function ConversationsPage() {
  const { t, locale } = useI18n();
  const [state, setState] = useState<LoadState>("loading");
  const [messages, setMessages] = useState<MessageView[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    const session = getSession();
    if (session === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState("anon");
      return;
    }
    api
      .conversations(session.businessId, session.token)
      .catch(() => [])
      .then((feed) => {
        setMessages(feed);
        setState("ready");
      });
  }, []);

  const threads = toThreads(messages);

  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-8 sm:px-8">
      {state === "loading" && (
        <div className="space-y-3">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      )}

      {state === "anon" && (
        <EmptyState icon="conversations" title={t("conversations.connectFirst")} />
      )}

      {state === "ready" && threads.length === 0 && (
        <EmptyState icon="conversations" title={t("conversations.empty")} />
      )}

      {state === "ready" && selected !== null && (
        <ThreadDetail
          customer={selected}
          messages={threadMessages(messages, selected)}
          locale={locale}
          onBack={() => setSelected(null)}
          backLabel={t("conversations.back")}
        />
      )}

      {state === "ready" && selected === null && threads.length > 0 && (
        <Card className="divide-y divide-line overflow-hidden">
          {threads.map((thread) => (
            <ThreadRow
              key={thread.customer}
              thread={thread}
              onOpen={() => setSelected(thread.customer)}
            />
          ))}
        </Card>
      )}
    </main>
  );
}

function ThreadRow({ thread, onOpen }: { thread: Thread; onOpen: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full items-center gap-3.5 px-5 py-3.5 text-left transition hover:bg-canvas"
    >
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-pink-soft text-sm font-extrabold text-pink">
        {thread.customer.slice(0, 2)}
      </span>
      <div className="min-w-0 flex-1">
        <div className="font-semibold">{thread.customer}</div>
        <div className="truncate text-sm text-muted">{thread.last}</div>
      </div>
    </button>
  );
}

function ThreadDetail({
  customer,
  messages,
  locale,
  onBack,
  backLabel,
}: {
  customer: string;
  messages: MessageView[];
  locale: Locale;
  onBack: () => void;
  backLabel: string;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          className="rounded-lg border border-line-strong px-3 py-1.5 text-sm font-medium hover:bg-canvas"
        >
          ← {backLabel}
        </button>
        <h2 className="font-bold">{customer}</h2>
      </div>
      <div className="space-y-2.5">
        {messages.map((message, index) => {
          const fromAssistant = message.role === "assistant";
          return (
            <div
              key={index}
              className={`flex flex-col ${fromAssistant ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm ${
                  fromAssistant ? "bg-accent text-accent-contrast" : "bg-surface border border-line"
                }`}
              >
                {message.text}
              </div>
              <span className="mt-1 px-1 text-xs text-muted">{formatTime(message.at, locale)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
