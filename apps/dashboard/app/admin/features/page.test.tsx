import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import AdminFeaturesPage from "./page";

const { adminPendingEntitlements, adminDecideFeature } = vi.hoisted(() => ({
  adminPendingEntitlements: vi.fn(),
  adminDecideFeature: vi.fn(),
}));
vi.mock("@/app/lib/api", () => ({ api: { adminPendingEntitlements, adminDecideFeature } }));

afterEach(() => {
  cleanup();
  adminPendingEntitlements.mockReset();
  adminDecideFeature.mockReset();
});

const PENDING = {
  business_id: "biz",
  feature_key: "voice_receptionist",
  status: "requested",
  requested_at: "2026-07-02T09:00:00+00:00",
  decided_at: null,
};

function renderPage() {
  return render(
    <I18nProvider>
      <AdminFeaturesPage />
    </I18nProvider>,
  );
}

describe("Admin feature requests page", () => {
  it("shows the denied state when the admin API rejects", async () => {
    adminPendingEntitlements.mockRejectedValue(new Error("403"));
    renderPage();
    expect(await screen.findByText("Feature requests")).toBeInTheDocument();
  });

  it("lists a pending request with approve/suspend actions", async () => {
    adminPendingEntitlements.mockResolvedValue([PENDING]);
    renderPage();

    expect(await screen.findByText("voice_receptionist")).toBeInTheDocument();
    expect(screen.getByText("biz")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Suspend" })).toBeInTheDocument();
  });

  it("approves a request and drops it from the queue", async () => {
    adminPendingEntitlements.mockResolvedValue([PENDING]);
    adminDecideFeature.mockResolvedValue({ ...PENDING, status: "active" });
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));

    await waitFor(() =>
      expect(adminDecideFeature).toHaveBeenCalledWith("biz", "voice_receptionist", "active"),
    );
    expect(await screen.findByText("No pending feature requests.")).toBeInTheDocument();
  });
});
