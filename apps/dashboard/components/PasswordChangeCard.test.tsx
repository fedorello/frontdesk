import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";
import { PasswordChangeCard } from "./PasswordChangeCard";

function renderCard(onSubmit: (current: string, next: string) => Promise<void>) {
  return render(
    <I18nProvider>
      <PasswordChangeCard onSubmit={onSubmit} />
    </I18nProvider>,
  );
}

function fill(current: string, next: string) {
  fireEvent.change(screen.getByLabelText("Current password"), { target: { value: current } });
  fireEvent.change(screen.getByLabelText("New password (at least 8 characters)"), {
    target: { value: next },
  });
}

afterEach(cleanup);

describe("PasswordChangeCard", () => {
  it("disables submit until a current password and an 8+ char new password are entered", () => {
    renderCard(async () => {});
    const button = screen.getByRole("button", { name: "Change password" });
    expect(button).toBeDisabled();
    fill("old", "short"); // new password too short
    expect(button).toBeDisabled();
    fill("old", "long-enough-pw");
    expect(button).not.toBeDisabled();
  });

  it("submits the entered passwords and shows success", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderCard(onSubmit);
    fill("old-pw", "new-pw-123");
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("old-pw", "new-pw-123"));
    expect(await screen.findByText("Password changed.")).toBeInTheDocument();
  });

  it("shows an error when the change is rejected (wrong current password)", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("403"));
    renderCard(onSubmit);
    fill("wrong", "new-pw-123");
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/check your current password/i);
  });
});
