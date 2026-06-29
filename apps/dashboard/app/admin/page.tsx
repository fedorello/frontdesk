"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type AdminOverview, type DailyCount } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession, isAdmin } from "@/app/lib/session";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { TrendChart } from "@/components/ui/TrendChart";

export const dynamic = "force-dynamic";

type LoadState = "loading" | "denied" | "ready";
const WINDOW_DAYS = 30;
const MS_PER_DAY = 86_400_000;

interface Series {
  signups: DailyCount[];
  replies: DailyCount[];
  bookings: DailyCount[];
  usage: DailyCount[];
}

export default function AdminPage() {
  const { t } = useI18n();
  const [state, setState] = useState<LoadState>("loading");
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [series, setSeries] = useState<Series | null>(null);

  useEffect(() => {
    if (!isAdmin(getSession())) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState("denied");
      return;
    }
    const to = new Date();
    const from = new Date(to.getTime() - WINDOW_DAYS * MS_PER_DAY);
    const fromIso = from.toISOString();
    const toIso = to.toISOString();
    Promise.all([
      api.adminOverview(),
      api.adminTimeseries("signups", fromIso, toIso),
      api.adminTimeseries("replies", fromIso, toIso),
      api.adminTimeseries("bookings", fromIso, toIso),
      api.adminTimeseries("llm_usage", fromIso, toIso),
    ])
      .then(([ov, signups, replies, bookings, usage]) => {
        setOverview(ov);
        setSeries({ signups, replies, bookings, usage });
        setState("ready");
      })
      .catch(() => setState("denied"));
  }, []);

  if (state === "loading") {
    return <AdminSkeleton />;
  }

  if (state === "denied" || overview === null || series === null) {
    return (
      <Page>
        <EmptyState icon="admin" title={t("admin.title")} body={t("admin.signedOut")} />
      </Page>
    );
  }

  const { totals, funnel } = overview;
  return (
    <Page>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon="admin"
          tone="accent"
          label={t("admin.totalBusinesses")}
          value={totals.total_businesses}
        />
        <StatCard
          icon="spark"
          tone="pink"
          label={t("admin.signups30")}
          value={totals.signups.last_30_days}
        />
        <StatCard
          icon="check"
          tone="neutral"
          label={t("admin.activeBusinesses")}
          value={totals.active_businesses_30d}
        />
        <StatCard
          icon="conversations"
          tone="accent"
          label={t("admin.customers")}
          value={totals.total_customers}
        />
        <StatCard
          icon="conversations"
          tone="pink"
          label={t("admin.agentReplies")}
          value={totals.total_agent_replies}
        />
        <StatCard
          icon="calendar"
          tone="accent"
          label={t("admin.appointments")}
          value={totals.appointments.total}
        />
        <StatCard
          icon="settings"
          tone="neutral"
          label={t("admin.botsConnected")}
          value={totals.telegram_bots_connected}
        />
        <StatCard
          icon="approvals"
          tone="pink"
          label={t("admin.pendingApprovals")}
          value={totals.pending_approvals}
        />
      </div>

      <div className="mt-5 grid items-start gap-5 lg:grid-cols-[1fr_1fr]">
        <Card className="p-5">
          <div className="mb-4 font-bold">{t("admin.funnel")}</div>
          <FunnelRow
            label={t("admin.funnelSignedUp")}
            value={funnel.signed_up}
            base={funnel.signed_up}
          />
          <FunnelRow
            label={t("admin.funnelConnected")}
            value={funnel.connected_channel}
            base={funnel.signed_up}
          />
          <FunnelRow
            label={t("admin.funnelMessaged")}
            value={funnel.received_message}
            base={funnel.signed_up}
          />
          <FunnelRow
            label={t("admin.funnelBooked")}
            value={funnel.booked_appointment}
            base={funnel.signed_up}
          />
          <div className="mt-4 flex gap-6 border-t border-line pt-4 text-sm">
            <Rate label={t("admin.noShowRate")} rate={overview.no_show_rate} />
            <Rate label={t("admin.cancellationRate")} rate={overview.cancellation_rate} />
          </div>
        </Card>

        <div className="grid gap-4">
          <TrendChart label={t("admin.trendSignups")} data={series.signups} />
          <TrendChart label={t("admin.trendReplies")} data={series.replies} />
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <TrendChart label={t("admin.trendBookings")} data={series.bookings} />
        <TrendChart label={t("admin.trendUsage")} data={series.usage} />
      </div>

      <div className="mt-6">
        <Link
          href="/admin/businesses"
          className="inline-flex rounded-lg bg-accent px-4 py-2.5 text-sm font-bold text-accent-contrast"
        >
          {t("admin.viewBusinesses")}
        </Link>
      </div>
    </Page>
  );
}

function Page({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto w-full max-w-5xl px-6 py-8 sm:px-8">{children}</main>;
}

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function FunnelRow({ label, value, base }: { label: string; value: number; base: number }) {
  const width = base > 0 ? Math.round((value / base) * 100) : 0;
  return (
    <div className="mb-3">
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className="font-semibold">{label}</span>
        <span className="tabular-nums text-muted">
          {value} · {width}%
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-surface-3">
        <div className="h-full rounded-full bg-accent" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function Rate({ label, rate }: { label: string; rate: number }) {
  return (
    <div>
      <div className="text-xl font-extrabold tabular-nums">{pct(rate)}</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}

function AdminSkeleton() {
  return (
    <Page>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }, (_, index) => (
          <Skeleton key={index} className="h-20" />
        ))}
      </div>
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </Page>
  );
}
