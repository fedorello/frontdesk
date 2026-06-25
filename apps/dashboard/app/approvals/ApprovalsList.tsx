"use client";

import type { Approval, ApprovalDecision } from "./types";

export function ApprovalsList({
  approvals,
  onDecide,
}: {
  approvals: Approval[];
  onDecide: (id: string, decision: ApprovalDecision) => void;
}) {
  if (approvals.length === 0) {
    return <p className="text-sm text-zinc-500">Nothing waiting for approval. 🎉</p>;
  }

  return (
    <ul className="space-y-3">
      {approvals.map((approval) => (
        <li
          key={approval.id}
          className="flex items-center justify-between rounded-xl border border-zinc-200 p-4 dark:border-zinc-800"
        >
          <div>
            <p className="font-medium">{approval.summary}</p>
            <p className="text-xs text-zinc-500">
              {approval.business} · {approval.requestedAt}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => onDecide(approval.id, "approve")}
              className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
            >
              Approve
            </button>
            <button
              type="button"
              onClick={() => onDecide(approval.id, "reject")}
              className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900"
            >
              Reject
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
