import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

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

describe("ApprovalsList", () => {
  it("lists pending approvals and fires the decision on click", () => {
    const onDecide = vi.fn();
    render(<ApprovalsList approvals={APPROVALS} onDecide={onDecide} />);

    expect(screen.getByText("Refund for +59899…")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    expect(onDecide).toHaveBeenCalledWith("apr-1", "approve");
  });

  it("shows an empty state when nothing is pending", () => {
    render(<ApprovalsList approvals={[]} onDecide={vi.fn()} />);

    expect(screen.getByText(/Nothing waiting/)).toBeInTheDocument();
  });
});
