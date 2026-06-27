"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type AppointmentView, type MessageView } from "@/app/lib/api";
import { isCancelled, STATUS_LABEL } from "@/app/lib/appointments";
import { formatDay, formatTime } from "@/app/lib/format";
import type { Locale } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { plainPreview } from "@/app/lib/text";
import { Icon } from "@/components/icons";
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

  useEffect(() => {
    const session = getSession();
    if (session === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState("anon");
      return;
    }
    Promise.all([
      api.appointments(session.businessId, session.token).catch(() => []),
      api.conversations(session.businessId, session.token).catch(() => []),
      api.getBusiness(session.businessId, session.token).catch(() => null),
    ]).then(([appts, msgs, business]) => {
      setAppointments(appts);
      setMessages(msgs);
      if (business) setTimeZone(business.timezone);
      setState("ready");
    });
  }, []);

  const active = appointments.filter((appointment) => !isCancelled(appointment.status));
  // The activity feed is a human-readable dialog — drop internal tool steps.
  const activity = messages.filter((message) => message.role !== "tool");

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
                />
              ))
          )}
        </Card>

        <Card className="overflow-hidden">
          <div className="px-5 pt-4 pb-2 font-bold">{t("overview.activity")}</div>
          {activity.length === 0 ? (
            <Hint text={t("conversations.empty")} />
          ) : (
            activity
              .slice(0, MAX_ROWS)
              .map((message, index) => (
                <ActivityRow
                  key={index}
                  message={message}
                  locale={locale}
                  timeZone={timeZone}
                  assistantLabel={t("overview.assistant")}
                />
              ))
          )}
        </Card>
      </div>
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
}: {
  appointment: AppointmentView;
  locale: Locale;
  timeZone: string;
  statusLabel: string;
}) {
  return (
    <div className="flex items-center gap-4 border-b border-line px-5 py-3 last:border-b-0">
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
    </div>
  );
}

function ActivityRow({
  message,
  locale,
  timeZone,
  assistantLabel,
}: {
  message: MessageView;
  locale: Locale;
  timeZone: string;
  assistantLabel: string;
}) {
  const fromAssistant = message.role === "assistant";
  const who = fromAssistant ? assistantLabel : message.customer;
  return (
    <div className="flex items-start gap-3 border-b border-line px-5 py-3 last:border-b-0">
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
          fromAssistant ? "bg-accent-soft text-accent" : "bg-pink-soft text-pink"
        }`}
      >
        {fromAssistant ? <Icon name="spark" size={15} /> : message.customer.slice(0, 2)}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate text-sm font-semibold">{who}</span>
          <span className="shrink-0 text-xs text-faint">
            {formatDay(message.at, locale, timeZone)} {formatTime(message.at, locale, timeZone)}
          </span>
        </div>
        <p className="truncate text-sm text-muted">{plainPreview(message.text)}</p>
      </div>
    </div>
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
