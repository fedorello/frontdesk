"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type AppointmentView, type MessageView } from "@/app/lib/api";
import { isCancelled, STATUS_LABEL } from "@/app/lib/appointments";
import { formatDay, formatTime } from "@/app/lib/format";
import type { Locale } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { AppointmentModal } from "@/components/AppointmentModal";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { StatusPill } from "@/components/ui/StatusPill";

type LoadState = "loading" | "anon" | "ready";
const MAX_ROWS = 6;

export default function Home() {
  const { t, locale } = useI18n();
  const [state, setState] = useState<LoadState>("loading");
  const [appointments, setAppointments] = useState<AppointmentView[]>([]);
  const [messages, setMessages] = useState<MessageView[]>([]);
  const [timeZone, setTimeZone] = useState("UTC");
  const [selected, setSelected] = useState<AppointmentView | null>(null);
  const session = getSession();

  useEffect(() => {
    const session = getSession();
    if (session === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState("anon");
      return;
    }
    Promise.all([
      api.appointments(session.businessId).catch(() => []),
      api.conversations(session.businessId).catch(() => []),
      api.getBusiness(session.businessId).catch(() => null),
    ]).then(([appts, msgs, business]) => {
      setAppointments(appts);
      setMessages(msgs);
      if (business) setTimeZone(business.timezone);
      setState("ready");
    });
  }, []);

  const active = appointments.filter((appointment) => !isCancelled(appointment.status));
  const chats = recentChats(messages, MAX_ROWS);

  if (state === "loading") {
    return <OverviewSkeleton />;
  }

  if (state === "anon") {
    return (
      <Page>
        <EmptyState
          icon="overview"
          title={t("overview.signedOutTitle")}
          body={t("calendar.connectFirst")}
          action={
            <>
              <Link
                href="/login"
                className="rounded-lg bg-accent px-4 py-2.5 text-sm font-bold text-accent-contrast"
              >
                {t("onboarding.logIn")}
              </Link>
              <Link
                href="/onboarding"
                className="rounded-lg border border-line-strong px-4 py-2.5 text-sm font-bold text-ink"
              >
                {t("onboarding.signUp")}
              </Link>
            </>
          }
        />
      </Page>
    );
  }

  return (
    <Page>
      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard
          icon="calendar"
          tone="accent"
          label={t("overview.bookings")}
          value={active.length}
        />
        <StatCard
          icon="conversations"
          tone="pink"
          label={t("overview.messages")}
          value={messages.length}
        />
      </div>

      <div className="mt-5 grid items-start gap-5 lg:grid-cols-[1.4fr_1fr]">
        <Card className="overflow-hidden">
          <CardHead title={t("nav.calendar")} href="/calendar" cta={t("overview.viewAll")} />
          {active.length === 0 ? (
            <Hint text={t("calendar.empty")} />
          ) : (
            active
              .slice(0, MAX_ROWS)
              .map((appointment) => (
                <AppointmentRow
                  key={appointment.id}
                  appointment={appointment}
                  locale={locale}
                  timeZone={timeZone}
                  statusLabel={
                    STATUS_LABEL[appointment.status]
                      ? t(STATUS_LABEL[appointment.status])
                      : appointment.status
                  }
                  onOpen={() => setSelected(appointment)}
                />
              ))
          )}
        </Card>

        <Card className="overflow-hidden">
          <CardHead
            title={t("overview.recentChats")}
            href="/conversations"
            cta={t("overview.viewAll")}
          />
          {chats.length === 0 ? (
            <Hint text={t("conversations.empty")} />
          ) : (
            chats.map((chat) => (
              <ChatRow key={chat.customer} chat={chat} locale={locale} timeZone={timeZone} />
            ))
          )}
        </Card>
      </div>

      {selected && session && (
        <AppointmentModal
          appointment={selected}
          timeZone={timeZone}
          locale={locale}
          businessId={session.businessId}
          onClose={() => setSelected(null)}
          onChanged={(result) => {
            setAppointments((previous) =>
              previous.map((item) =>
                item.id === result.id
                  ? {
                      ...item,
                      status: result.status,
                      starts_at: result.starts_at,
                      ends_at: result.ends_at,
                    }
                  : item,
              ),
            );
            setSelected(null);
          }}
        />
      )}
    </Page>
  );
}

function Page({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto w-full max-w-5xl px-6 py-8 sm:px-8">{children}</main>;
}

function CardHead({ title, href, cta }: { title: string; href: string; cta: string }) {
  return (
    <div className="flex items-center justify-between border-b border-line px-5 py-4">
      <span className="font-bold">{title}</span>
      <Link href={href} className="text-sm font-bold text-accent">
        {cta}
      </Link>
    </div>
  );
}

function Hint({ text }: { text: string }) {
  return <p className="px-5 py-6 text-sm text-muted">{text}</p>;
}

function AppointmentRow({
  appointment,
  locale,
  timeZone,
  statusLabel,
  onOpen,
}: {
  appointment: AppointmentView;
  locale: Locale;
  timeZone: string;
  statusLabel: string;
  onOpen: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full items-center gap-4 border-b border-line px-5 py-3 text-left transition last:border-b-0 hover:bg-canvas"
    >
      <div className="flex w-24 shrink-0 flex-col leading-tight">
        <span className="text-xs capitalize text-muted">
          {formatDay(appointment.starts_at, locale, timeZone)}
        </span>
        <span className="font-extrabold tabular-nums">
          {formatTime(appointment.starts_at, locale, timeZone)}
        </span>
      </div>
      <span className="flex-1 truncate text-sm font-semibold">{appointment.service}</span>
      <StatusPill status={appointment.status} label={statusLabel} />
    </button>
  );
}

interface ChatSummary {
  customer: string; // channel address (the thread key)
  name: string; // display name, or the address
  at: string; // time of the latest message
}

// Newest-first feed → one entry per customer, most-recent first.
function recentChats(messages: MessageView[], max: number): ChatSummary[] {
  const seen = new Map<string, ChatSummary>();
  for (const message of messages) {
    if (message.role === "tool" || seen.has(message.customer)) continue;
    seen.set(message.customer, {
      customer: message.customer,
      name: message.customer_name || message.customer,
      at: message.at,
    });
  }
  return [...seen.values()].slice(0, max);
}

function ChatRow({
  chat,
  locale,
  timeZone,
}: {
  chat: ChatSummary;
  locale: Locale;
  timeZone: string;
}) {
  return (
    <Link
      href={`/conversations?open=${encodeURIComponent(chat.customer)}`}
      className="flex items-center gap-3 border-b border-line px-5 py-3 transition last:border-b-0 hover:bg-canvas"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-pink-soft text-xs font-extrabold text-pink">
        {chat.name.slice(0, 2).toUpperCase()}
      </span>
      <span className="min-w-0 flex-1 truncate text-sm font-semibold">{chat.name}</span>
      <span className="shrink-0 text-xs text-faint">
        {formatDay(chat.at, locale, timeZone)} {formatTime(chat.at, locale, timeZone)}
      </span>
    </Link>
  );
}

function OverviewSkeleton() {
  return (
    <Page>
      <div className="grid gap-4 sm:grid-cols-2">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
      <div className="mt-5 grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
    </Page>
  );
}
