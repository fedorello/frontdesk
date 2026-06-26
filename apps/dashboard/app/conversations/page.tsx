"use client";

import { useEffect, useState } from "react";

import { api, type MessageView } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";

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

export default function ConversationsPage() {
  const { t } = useI18n();
  const [state, setState] = useState<LoadState>("loading");
  const [threads, setThreads] = useState<Thread[]>([]);

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
      .then((messages) => {
        setThreads(toThreads(messages));
        setState("ready");
      });
  }, []);

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

      {state === "ready" && threads.length > 0 && (
        <Card className="divide-y divide-line overflow-hidden">
          {threads.map((thread) => (
            <ThreadRow key={thread.customer} thread={thread} />
          ))}
        </Card>
      )}
    </main>
  );
}

function ThreadRow({ thread }: { thread: Thread }) {
  return (
    <div className="flex items-center gap-3.5 px-5 py-3.5">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-pink-soft text-sm font-extrabold text-pink">
        {thread.customer.slice(0, 2)}
      </span>
      <div className="min-w-0 flex-1">
        <div className="font-semibold">{thread.customer}</div>
        <div className="truncate text-sm text-muted">{thread.last}</div>
      </div>
    </div>
  );
}
