"use client";

import Link from "next/link";
import { type ReactNode, useEffect, useState } from "react";

import { api, type AdminEntitlement } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";

export const dynamic = "force-dynamic";

type LoadState = "loading" | "denied" | "ready";

const rowId = (row: AdminEntitlement) => `${row.business_id}:${row.feature_key}`;

export default function AdminFeaturesPage() {
  const { t } = useI18n();
  const [state, setState] = useState<LoadState>("loading");
  const [rows, setRows] = useState<AdminEntitlement[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    // The backend admin guard is the gate; a rejected fetch (401/403) shows the denied state.
    api
      .adminPendingEntitlements()
      .then((items) => {
        setRows(items);
        setState("ready");
      })
      .catch(() => setState("denied"));
  }, []);

  const decide = async (row: AdminEntitlement, status: "active" | "suspended") => {
    const id = rowId(row);
    setBusy(id);
    try {
      await api.adminDecideFeature(row.business_id, row.feature_key, status);
      setRows((current) => current.filter((item) => rowId(item) !== id)); // decided → leave the queue
    } finally {
      setBusy(null);
    }
  };

  if (state === "loading")
    return (
      <Page>
        <Skeleton className="h-96" />
      </Page>
    );

  if (state === "denied")
    return (
      <Page>
        <EmptyState icon="admin" title={t("admin.featureRequests")} body={t("admin.signedOut")} />
      </Page>
    );

  return (
    <Page>
      <div className="mb-4">
        <Link href="/admin" className="text-sm font-bold text-accent">
          ← {t("admin.title")}
        </Link>
      </div>
      <h1 className="text-lg font-bold">{t("admin.featureRequests")}</h1>
      {rows.length === 0 ? (
        <p className="mt-6 text-sm text-muted">{t("admin.noRequests")}</p>
      ) : (
        <div className="mt-4 space-y-3">
          {rows.map((row) => (
            <div
              key={rowId(row)}
              className="flex items-center justify-between gap-4 rounded-xl border border-line bg-surface p-4 shadow-card"
            >
              <div className="min-w-0">
                <p className="font-semibold">{row.feature_key}</p>
                <p className="mt-0.5 text-sm text-muted">{row.business_id}</p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  disabled={busy === rowId(row)}
                  onClick={() => decide(row, "active")}
                  className="rounded-lg bg-accent px-3 py-1.5 text-sm font-bold text-accent-contrast disabled:opacity-50"
                >
                  {t("admin.approve")}
                </button>
                <button
                  type="button"
                  disabled={busy === rowId(row)}
                  onClick={() => decide(row, "suspended")}
                  className="rounded-lg border border-line px-3 py-1.5 text-sm font-bold disabled:opacity-50"
                >
                  {t("admin.suspend")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Page>
  );
}

function Page({ children }: { children: ReactNode }) {
  return <main className="mx-auto w-full max-w-5xl px-6 py-8 sm:px-8">{children}</main>;
}
