import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import { ApprovalsList } from "./ApprovalsList";
import type { Approval } from "./types";

const APPROVALS: Approval[] = [
  {
    id: "apr-1",
    summary: "Refund for +59899…",
    tool: "issue_refund",
    args: { appointment_id: "ap-9" },
    risk: "sensitive",
  },
];

const withI18n = (node: ReactNode) => render(<I18nProvider>{node}</I18nProvider>);

describe("ApprovalsList", () => {
  it("lists pending approvals and fires the decision on click", () => {
    const onDecide = vi.fn();
    withI18n(<ApprovalsList approvals={APPROVALS} onDecide={onDecide} />);

    expect(screen.getByText("Refund for +59899…")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    expect(onDecide).toHaveBeenCalledWith("apr-1", "approve");
  });

  it("shows an empty state when nothing is pending", () => {
    withI18n(<ApprovalsList approvals={[]} onDecide={vi.fn()} />);

    expect(screen.getByText(/Nothing waiting/)).toBeInTheDocument();
  });
});
