import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import AdminBusinessesPage from "./page";

const { adminBusinesses } = vi.hoisted(() => ({ adminBusinesses: vi.fn() }));
vi.mock("@/app/lib/api", () => ({ api: { adminBusinesses } }));

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  adminBusinesses.mockReset();
});

function renderPage() {
  return render(
    <I18nProvider>
      <AdminBusinessesPage />
    </I18nProvider>,
  );
}

const ROW = {
  business_id: "b1",
  name: "Salon Uno",
  locale: "en",
  timezone: "UTC",
  created_at: "2026-06-01T00:00:00+00:00",
  service_count: 2,
  customer_count: 12,
  appointments: { pending: 0, confirmed: 3, completed: 0, cancelled: 0, no_show: 0, total: 3 },
  agent_reply_count: 20,
  last_activity_at: null,
  bot_connected: true,
  uses_own_llm: false,
  owner_telegram_linked: false,
};

describe("Admin businesses page", () => {
  it("shows the denied state when the admin API rejects", async () => {
    adminBusinesses.mockRejectedValue(new Error("403"));
    renderPage();
    expect(
      await screen.findByText("Sign in with an admin account to view platform analytics."),
    ).toBeInTheDocument();
  });

  it("lists businesses for an admin", async () => {
    adminBusinesses.mockResolvedValue({ items: [ROW], total: 1 });

    renderPage();

    expect(await screen.findByText("Salon Uno")).toBeInTheDocument();
    expect(screen.getByText("Managed")).toBeInTheDocument(); // uses_own_llm === false
  });
});
