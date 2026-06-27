"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { api, type MessageView } from "@/app/lib/api";
import { formatDay, formatTime } from "@/app/lib/format";
import type { Locale } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { plainPreview, stripMarkdown } from "@/app/lib/text";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";

// Authenticated, client-data page that reads the ?q= search param — never static.
export const dynamic = "force-dynamic";

export default function ConversationsPage() {
  return (
    <Suspense>
      <ConversationsContent />
    </Suspense>
  );
}

type LoadState = "loading" | "anon" | "ready";

interface Thread {
  customer: string;
  customerId: string;
  handled: boolean;
  last: string;
  at: string;
  count: number;
}

// The feed is newest-first; fold it into one entry per customer (latest message + count).
function toThreads(messages: MessageView[]): Thread[] {
  const byCustomer = new Map<string, Thread>();
  for (const message of messages) {
    const existing = byCustomer.get(message.customer);
    if (existing) {
      existing.count += 1;
    } else {
      byCustomer.set(message.customer, {
        customer: message.customer,
        customerId: message.customer_id,
        handled: message.handled,
        last: message.text,
        at: message.at,
        count: 1,
      });
    }
  }
  return [...byCustomer.values()];
}

// One customer's messages, oldest-first, without internal tool steps.
function threadMessages(messages: MessageView[], customer: string): MessageView[] {
  return messages
    .filter((message) => message.customer === customer && message.role !== "tool")
    .slice()
    .reverse();
}

function ConversationsContent() {
  const { t, locale } = useI18n();
  const searchParams = useSearchParams();
  const [state, setState] = useState<LoadState>("loading");
  const [messages, setMessages] = useState<MessageView[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [timeZone, setTimeZone] = useState("UTC");

  useEffect(() => {
    const session = getSession();
    if (session === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState("anon");
      return;
    }
    void (async () => {
      const [feed, business] = await Promise.all([
        api.conversations(session.businessId, session.token).catch(() => []),
        api.getBusiness(session.businessId, session.token).catch(() => null),
      ]);
      setMessages(feed);
      if (business) setTimeZone(business.timezone);
      setState("ready");
    })();
  }, []);

  const reload = async () => {
    const session = getSession();
    if (session === null) return;
    setMessages(await api.conversations(session.businessId, session.token).catch(() => []));
  };

  const threads = toThreads(messages);
  const selectedThread = selected ? threads.find((thread) => thread.customer === selected) : null;
  const session = getSession();
  const query = (searchParams.get("q") ?? "").trim().toLowerCase();
  const filtered = query
    ? threads.filter(
        (thread) =>
          thread.customer.toLowerCase().includes(query) ||
          plainPreview(thread.last).toLowerCase().includes(query),
      )
    : threads;

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

      {state === "ready" && selected !== null && selectedThread && session && (
        <ThreadDetail
          customer={selected}
          customerId={selectedThread.customerId}
          handled={selectedThread.handled}
          businessId={session.businessId}
          token={session.token}
          messages={threadMessages(messages, selected)}
          locale={locale}
          timeZone={timeZone}
          onBack={() => setSelected(null)}
          onChanged={reload}
          backLabel={t("conversations.back")}
        />
      )}

      {state === "ready" && selected === null && threads.length > 0 && filtered.length === 0 && (
        <EmptyState icon="search" title={t("common.noResults")} />
      )}

      {state === "ready" && selected === null && filtered.length > 0 && (
        <Card className="divide-y divide-line overflow-hidden">
          {filtered.map((thread) => (
            <ThreadRow
              key={thread.customer}
              thread={thread}
              locale={locale}
              timeZone={timeZone}
              onOpen={() => setSelected(thread.customer)}
            />
          ))}
        </Card>
      )}
    </main>
  );
}

function ThreadRow({
  thread,
  locale,
  timeZone,
  onOpen,
}: {
  thread: Thread;
  locale: Locale;
  timeZone: string;
  onOpen: () => void;
}) {
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
        <div className="flex items-baseline justify-between gap-2">
          <span className="flex min-w-0 items-baseline gap-2">
            <span className="truncate font-semibold">{thread.customer}</span>
            <span className="shrink-0 rounded-full bg-surface-3 px-1.5 py-0.5 text-[11px] font-medium text-muted">
              {thread.count}
            </span>
          </span>
          <span className="shrink-0 text-xs text-faint">
            {formatDay(thread.at, locale, timeZone)} {formatTime(thread.at, locale, timeZone)}
          </span>
        </div>
        <div className="truncate text-sm text-muted">{plainPreview(thread.last)}</div>
      </div>
    </button>
  );
}

const composerClass =
  "w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent";

function ThreadDetail({
  customer,
  customerId,
  handled,
  businessId,
  token,
  messages,
  locale,
  timeZone,
  onBack,
  onChanged,
  backLabel,
}: {
  customer: string;
  customerId: string;
  handled: boolean;
  businessId: string;
  token: string;
  messages: MessageView[];
  locale: Locale;
  timeZone: string;
  onBack: () => void;
  onChanged: () => Promise<void>;
  backLabel: string;
}) {
  const { t } = useI18n();
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await action();
      await onChanged();
    } finally {
      setBusy(false);
    }
  };

  const send = () => {
    const text = draft.trim();
    if (!text) return;
    void run(async () => {
      await api.sendOwnerMessage(businessId, customerId, text, token);
      setDraft("");
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
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
        {handled && (
          <button
            type="button"
            onClick={() => run(() => api.setHandoff(businessId, customerId, false, token))}
            disabled={busy}
            className="rounded-lg border border-line-strong px-3 py-1.5 text-sm font-medium hover:bg-canvas disabled:opacity-50"
          >
            {t("conversations.returnToAi")}
          </button>
        )}
      </div>

      {handled && (
        <p className="rounded-lg bg-warning-soft px-3 py-2 text-xs text-warning">
          {t("conversations.youAreHandling")}
        </p>
      )}

      <div className="space-y-2.5">
        {messages.map((message, index) => {
          const isOwner = message.role === "owner";
          const isAssistant = message.role === "assistant";
          const businessSide = isOwner || isAssistant;
          return (
            <div
              key={index}
              className={`flex flex-col ${businessSide ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm ${
                  isOwner
                    ? "bg-success text-accent-contrast"
                    : isAssistant
                      ? "bg-accent text-accent-contrast"
                      : "border border-line bg-surface"
                }`}
              >
                {stripMarkdown(message.text)}
              </div>
              <span className="mt-1 px-1 text-xs text-muted">
                {isOwner ? `${t("conversations.you")} · ` : ""}
                {formatTime(message.at, locale, timeZone)}
              </span>
            </div>
          );
        })}
      </div>

      <div className="space-y-2 border-t border-line pt-4">
        <textarea
          aria-label={t("conversations.reply")}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={t("conversations.replyPlaceholder")}
          rows={2}
          className={composerClass}
        />
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-muted">{t("conversations.replyHint")}</span>
          <button
            type="button"
            onClick={send}
            disabled={busy || draft.trim() === ""}
            className="shrink-0 rounded-lg bg-accent px-4 py-2 text-sm font-bold text-accent-contrast disabled:opacity-50"
          >
            {t("conversations.send")}
          </button>
        </div>
      </div>
    </div>
  );
}
