"use client";

import { useState } from "react";

import { ApprovalsList } from "./ApprovalsList";
import type { Approval } from "./types";

// TODO(phase-8): replace the seed with a fetch to the dashboard API
// (GET /api/approvals), and POST the decision back to run or drop the action.
const SEED: Approval[] = [
  {
    id: "apr-1",
    business: "Ana's Studio",
    summary: "Refund for +59899… (appointment ap-9)",
    requestedAt: "just now",
  },
];

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>(SEED);

  function removeApproval(id: string) {
    setApprovals((current) => current.filter((approval) => approval.id !== id));
  }

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Approvals</h1>
      <p className="mt-2 max-w-2xl text-sm text-zinc-500">
        Sensitive actions the assistant flagged. Nothing happens until you approve — that&apos;s the
        whole point of the gate.
      </p>
      <div className="mt-8">
        <ApprovalsList approvals={approvals} onDecide={(id) => removeApproval(id)} />
      </div>
    </main>
  );
}
