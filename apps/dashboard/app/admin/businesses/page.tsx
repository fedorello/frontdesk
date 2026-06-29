"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type BusinessSummary, type DirectorySort } from "@/app/lib/api";
import { formatDay } from "@/app/lib/format";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession, isAdmin } from "@/app/lib/session";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";

export const dynamic = "force-dynamic";

type LoadState = "loading" | "denied" | "ready";
const PAGE_SIZE = 20;
const ADMIN_TZ = "UTC"; // the operator view is platform-wide; render dates in UTC

const SORTS: { value: DirectorySort; label: string }[] = [
  { value: "signup_date", label: "admin.colSignup" },
  { value: "name", label: "admin.colName" },
  { value: "appointments", label: "admin.colAppointments" },
  { value: "customers", label: "admin.colCustomers" },
  { value: "replies", label: "admin.colReplies" },
  { value: "last_activity", label: "admin.colLastActivity" },
];

export default function AdminBusinessesPage() {
  const { t, locale } = useI18n();
  const [state, setState] = useState<LoadState>("loading");
  const [rows, setRows] = useState<BusinessSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [sort, setSort] = useState<DirectorySort>("signup_date");
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!isAdmin(getSession())) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState("denied");
      return;
    }
    api
      .adminBusinesses({ limit: PAGE_SIZE, offset, sort, descending: true, q: query })
      .then((page) => {
        setRows(page.items);
        setTotal(page.total);
        setState("ready");
      })
      .catch(() => setState("denied"));
  }, [offset, sort, query]);

  if (state === "loading") {
    return (
      <Page>
        <Skeleton className="h-96" />
      </Page>
    );
  }

  if (state === "denied") {
    return (
      <Page>
        <EmptyState icon="admin" title={t("admin.businesses")} body={t("admin.signedOut")} />
      </Page>
    );
  }

  const lastPage = offset + PAGE_SIZE >= total;
  return (
    <Page>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Link href="/admin" className="text-sm font-bold text-accent">
          ← {t("admin.back")}
        </Link>
        <input
          aria-label={t("admin.searchBusinesses")}
          placeholder={t("admin.searchBusinesses")}
          value={query}
          onChange={(event) => {
            setOffset(0);
            setQuery(event.target.value);
          }}
          className="ml-auto w-48 rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
        />
        <label className="flex items-center gap-2 text-sm">
          <select
            aria-label={t("admin.colName")}
            value={sort}
            onChange={(event) => {
              setOffset(0);
              setSort(event.target.value as DirectorySort);
            }}
            className="rounded-lg border border-line-strong bg-surface px-2 py-2 text-sm"
          >
            {SORTS.map((option) => (
              <option key={option.value} value={option.value}>
                {t(option.label as Parameters<typeof t>[0])}
              </option>
            ))}
          </select>
        </label>
      </div>

      {rows.length === 0 ? (
        <EmptyState icon="admin" title={t("admin.empty")} />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-xs uppercase text-faint">
              <tr>
                <Th>{t("admin.colName")}</Th>
                <Th>{t("admin.colSignup")}</Th>
                <Th>{t("admin.colCustomers")}</Th>
                <Th>{t("admin.colAppointments")}</Th>
                <Th>{t("admin.colReplies")}</Th>
                <Th>{t("admin.colLastActivity")}</Th>
                <Th>{t("admin.colLlm")}</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.business_id} className="border-b border-line last:border-b-0">
                  <Td>
                    <span className="font-semibold">{row.name}</span>
                  </Td>
                  <Td>{formatDay(row.created_at, locale, ADMIN_TZ)}</Td>
                  <Td className="tabular-nums">{row.customer_count}</Td>
                  <Td className="tabular-nums">{row.appointments.total}</Td>
                  <Td className="tabular-nums">{row.agent_reply_count}</Td>
                  <Td>
                    {row.last_activity_at ? formatDay(row.last_activity_at, locale, ADMIN_TZ) : "—"}
                  </Td>
                  <Td>{row.uses_own_llm ? t("admin.llmOwn") : t("admin.llmDefault")}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <div className="mt-4 flex items-center justify-between text-sm">
        <button
          type="button"
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          className="rounded-lg border border-line-strong px-3 py-1.5 font-semibold disabled:opacity-40"
        >
          {t("admin.prev")}
        </button>
        <span className="tabular-nums text-muted">{total}</span>
        <button
          type="button"
          disabled={lastPage}
          onClick={() => setOffset(offset + PAGE_SIZE)}
          className="rounded-lg border border-line-strong px-3 py-1.5 font-semibold disabled:opacity-40"
        >
          {t("admin.next")}
        </button>
      </div>
    </Page>
  );
}

function Page({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto w-full max-w-5xl px-6 py-8 sm:px-8">{children}</main>;
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-4 py-3 font-semibold">{children}</th>;
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-4 py-3 ${className}`}>{children}</td>;
}
