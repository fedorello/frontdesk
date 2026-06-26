"use client";

import { useCallback, useEffect, useState } from "react";

import { useI18n } from "@/app/lib/I18nProvider";

import { ApprovalsList } from "./ApprovalsList";
import type { Approval, ApprovalDecision } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ApprovalsPage() {
  const { t } = useI18n();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [reachable, setReachable] = useState(true);

  const load = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/approvals`);
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
    try {
      await fetch(`${API_URL}/api/approvals/${id}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ approved: decision === "approve" }),
      });
    } finally {
      await load();
    }
  }

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">{t("nav.approvals")}</h1>
      <p className="mt-2 max-w-2xl text-sm text-zinc-500">
        Sensitive actions the assistant flagged, gated by{" "}
        <span className="font-medium">airlock</span>. Nothing happens until you approve —
        that&apos;s the whole point of the gate.
      </p>
      <div className="mt-8">
        {reachable ? (
          <ApprovalsList approvals={approvals} onDecide={(id, decision) => decide(id, decision)} />
        ) : (
          <p className="text-sm text-zinc-500">
            Can&apos;t reach the API on :8000 — start it with <code>make stack-up</code>.
          </p>
        )}
      </div>
    </main>
  );
}
