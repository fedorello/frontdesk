"use client";

import { useI18n } from "@/app/lib/I18nProvider";

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
  const { t } = useI18n();
  if (approvals.length === 0) {
    return <p className="text-sm text-muted">{t("approvals.empty")}</p>;
  }

  return (
    <ul className="space-y-3">
      {approvals.map((approval) => (
        <li
          key={approval.id}
          className="flex items-center justify-between gap-4 rounded-xl border border-line bg-surface shadow-card p-4 "
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium">{approval.summary}</span>
              {approval.risk === "sensitive" ? (
                <span className="rounded bg-warning-soft px-1.5 py-0.5 text-xs font-semibold text-warning">
                  {t("approvals.sensitive")}
                </span>
              ) : null}
            </div>
            <p className="mt-0.5 truncate font-mono text-xs text-muted">
              {approval.tool}({formatArgs(approval.args)})
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              onClick={() => onDecide(approval.id, "approve")}
              className="rounded-md bg-success px-3 py-1.5 text-sm font-bold text-accent-contrast hover:opacity-90"
            >
              {t("approvals.approve")}
            </button>
            <button
              type="button"
              onClick={() => onDecide(approval.id, "reject")}
              className="rounded-md border border-line-strong px-3 py-1.5 text-sm font-medium hover:bg-surface-3 "
            >
              {t("approvals.reject")}
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
