"use client";

import { useSearchParams } from "next/navigation";
import { type KeyboardEvent, Suspense, useEffect, useLayoutEffect, useRef, useState } from "react";

import { api, type MessageView } from "@/app/lib/api";
import { formatDay, formatTime } from "@/app/lib/format";
import type { Locale } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { stripMarkdown } from "@/app/lib/text";
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
const THREAD_PAGE = 20; // messages shown per "load older" step

interface Thread {
  customer: string; // channel address (the fallback label / id)
  customerId: string;
  name: string; // display name, or the address if none
  handled: boolean;
  lastReceived?: string; // when the customer last wrote
  lastSent?: string; // when we last replied (assistant or owner)
  count: number;
}

// The feed is newest-first; fold it into one entry per customer with the last in/out times.
function toThreads(messages: MessageView[]): Thread[] {
  const byCustomer = new Map<string, Thread>();
  for (const message of messages) {
    let thread = byCustomer.get(message.customer);
    if (!thread) {
      thread = {
        customer: message.customer,
        customerId: message.customer_id,
        name: message.customer_name || message.customer,
        handled: message.handled,
        count: 0,
      };
      byCustomer.set(message.customer, thread);
    }
    thread.count += 1;
    if (message.role === "customer" && !thread.lastReceived) thread.lastReceived = message.at;
    if ((message.role === "assistant" || message.role === "owner") && !thread.lastSent) {
      thread.lastSent = message.at;
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
          thread.name.toLowerCase().includes(query) ||
          thread.customer.toLowerCase().includes(query),
      )
    : threads;

  const threadOpen = state === "ready" && selected !== null && selectedThread !== null;

  return (
    <main
      className={`mx-auto w-full max-w-3xl px-6 sm:px-8 ${
        threadOpen ? "flex h-full flex-col py-6" : "py-8"
      }`}
    >
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
          key={selectedThread.customerId}
          customer={selectedThread.name}
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
              receivedLabel={t("conversations.received")}
              sentLabel={t("conversations.sent")}
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
  receivedLabel,
  sentLabel,
  onOpen,
}: {
  thread: Thread;
  locale: Locale;
  timeZone: string;
  receivedLabel: string;
  sentLabel: string;
  onOpen: () => void;
}) {
  const stamp = (iso: string) =>
    `${formatDay(iso, locale, timeZone)} ${formatTime(iso, locale, timeZone)}`;
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full items-center gap-3.5 px-5 py-3.5 text-left transition hover:bg-canvas"
    >
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-pink-soft text-sm font-extrabold text-pink">
        {thread.name.slice(0, 2).toUpperCase()}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="truncate font-semibold">{thread.name}</span>
          <span className="shrink-0 rounded-full bg-surface-3 px-1.5 py-0.5 text-[11px] font-medium text-muted">
            {thread.count}
          </span>
        </div>
        <div className="mt-0.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted">
          {thread.lastReceived && (
            <span>
              <span className="text-faint">↓ {receivedLabel}:</span> {stamp(thread.lastReceived)}
            </span>
          )}
          {thread.lastSent && (
            <span>
              <span className="text-faint">↑ {sentLabel}:</span> {stamp(thread.lastSent)}
            </span>
          )}
        </div>
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
  const [visible, setVisible] = useState(THREAD_PAGE);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const keepScroll = useRef(0);

  const shown = messages.slice(Math.max(0, messages.length - visible));
  const hasOlder = visible < messages.length;

  // Open the thread / a new message arrives → jump to the latest (the point of interest).
  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ block: "end" }); // optional: jsdom has no scrollIntoView
  }, [customerId, messages.length]);

  // "Load older" prepends above; keep the viewport anchored so it doesn't jump.
  useLayoutEffect(() => {
    const element = scrollRef.current;
    if (element && keepScroll.current) {
      element.scrollTop += element.scrollHeight - keepScroll.current;
      keepScroll.current = 0;
    }
  }, [visible]);

  const loadOlder = () => {
    if (scrollRef.current) keepScroll.current = scrollRef.current.scrollHeight;
    setVisible((current) => current + THREAD_PAGE);
  };

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

  // Cmd+Enter on macOS, Ctrl+Enter elsewhere — both arrive as metaKey/ctrlKey + Enter.
  const onComposerKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      send();
    }
  };
  const isMac = typeof navigator !== "undefined" && /Mac/i.test(navigator.platform);
  const sendShortcut = isMac ? "⌘↵" : "Ctrl+↵";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center justify-between gap-3 pb-3">
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
        <p className="mb-3 shrink-0 rounded-lg bg-warning-soft px-3 py-2 text-xs text-warning">
          {t("conversations.youAreHandling")}
        </p>
      )}

      <div ref={scrollRef} className="min-h-0 flex-1 space-y-2.5 overflow-y-auto py-1">
        {hasOlder && (
          <div className="flex justify-center pb-1">
            <button
              type="button"
              onClick={loadOlder}
              className="rounded-full border border-line-strong px-3 py-1 text-xs font-medium text-muted hover:bg-canvas"
            >
              {t("conversations.loadOlder")}
            </button>
          </div>
        )}
        {shown.map((message, index) => {
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
        <div ref={bottomRef} />
      </div>

      <div className="shrink-0 space-y-2 border-t border-line bg-bg pt-3">
        <textarea
          aria-label={t("conversations.reply")}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onComposerKeyDown}
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
            className="flex shrink-0 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-bold text-accent-contrast disabled:opacity-50"
          >
            {t("conversations.send")}
            <kbd className="rounded bg-black/15 px-1.5 py-0.5 font-sans text-[11px] font-medium">
              {sendShortcut}
            </kbd>
          </button>
        </div>
      </div>
    </div>
  );
}
