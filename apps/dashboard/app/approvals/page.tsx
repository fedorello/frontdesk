"use client";

import { useCallback, useEffect, useState } from "react";

import { API_URL } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { Icon } from "@/components/icons";

import { ApprovalsList } from "./ApprovalsList";
import type { Approval, ApprovalDecision } from "./types";

export default function ApprovalsPage() {
  const { t } = useI18n();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [reachable, setReachable] = useState(true);

  const load = useCallback(async () => {
    const session = getSession();
    if (session === null) return;
    try {
      const response = await fetch(`${API_URL}/api/businesses/${session.businessId}/approvals`, {
        credentials: "include", // the HttpOnly session cookie authenticates
      });
      setApprovals((await response.json()) as Approval[]);
      setReachable(true);
    } catch {
      setReachable(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot fetch on mount
    void load();
  }, [load]);

  async function decide(id: string, decision: ApprovalDecision) {
    const session = getSession();
    if (session === null) return;
    try {
      await fetch(`${API_URL}/api/businesses/${session.businessId}/approvals/${id}`, {
        method: "POST",
        credentials: "include", // the HttpOnly session cookie authenticates
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ approved: decision === "approve" }),
      });
    } finally {
      await load();
    }
  }

  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-8 sm:px-8">
      <div className="mb-6 flex items-start gap-3 rounded-xl border border-line bg-surface p-4">
        <span className="mt-0.5 shrink-0 text-accent">
          <Icon name="approvals" size={20} />
        </span>
        <p className="text-sm leading-relaxed text-muted">{t("approvals.subtitle")}</p>
      </div>
      {reachable ? (
        <ApprovalsList approvals={approvals} onDecide={(id, decision) => decide(id, decision)} />
      ) : (
        <p className="text-sm text-muted">{t("approvals.unreachable")}</p>
      )}
    </main>
  );
}
