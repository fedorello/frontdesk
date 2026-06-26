"use client";

import type { Approval, ApprovalDecision } from "./types";

function formatArgs(args: Record<string, unknown>): string {
  return Object.entries(args)
    .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
    .join(", ");
}

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
          className="flex items-center justify-between gap-4 rounded-xl border border-zinc-200 p-4 dark:border-zinc-800"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium">{approval.summary}</span>
              {approval.risk === "sensitive" ? (
                <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-500/15 dark:text-amber-400">
                  sensitive
                </span>
              ) : null}
            </div>
            <p className="mt-0.5 truncate font-mono text-xs text-zinc-500">
              {approval.tool}({formatArgs(approval.args)})
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
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
