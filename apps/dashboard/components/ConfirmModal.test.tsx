import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ConfirmModal } from "./ConfirmModal";

afterEach(cleanup);

function renderModal(overrides: Partial<Parameters<typeof ConfirmModal>[0]> = {}) {
  const onConfirm = vi.fn();
  const onClose = vi.fn();
  render(
    <ConfirmModal
      title="Delete?"
      body="This cannot be undone."
      confirmLabel="Yes"
      cancelLabel="No"
      onConfirm={onConfirm}
      onClose={onClose}
      {...overrides}
    />,
  );
  return { onConfirm, onClose };
}

describe("ConfirmModal", () => {
  it("calls onConfirm and onClose for the two actions", () => {
    const { onConfirm, onClose } = renderModal();
    expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Yes" }));
    expect(onConfirm).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "No" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("disables both actions while busy", () => {
    renderModal({ busy: true });
    expect(screen.getByRole("button", { name: "Yes" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "No" })).toBeDisabled();
  });
});
