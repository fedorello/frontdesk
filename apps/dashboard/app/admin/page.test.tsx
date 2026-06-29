import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import AdminPage from "./page";

const { adminOverview, adminTimeseries } = vi.hoisted(() => ({
  adminOverview: vi.fn(),
  adminTimeseries: vi.fn(),
}));
vi.mock("@/app/lib/api", () => ({ api: { adminOverview, adminTimeseries } }));

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  adminOverview.mockReset();
  adminTimeseries.mockReset();
});

function asAdmin() {
  window.localStorage.setItem("tovayo.session", JSON.stringify({ businessId: "", role: "admin" }));
}

function renderAdmin() {
  return render(
    <I18nProvider>
      <AdminPage />
    </I18nProvider>,
  );
}

const OVERVIEW = {
  totals: {
    total_businesses: 7,
    signups: { today: 1, last_7_days: 2, last_30_days: 5 },
    active_businesses_30d: 3,
    total_customers: 40,
    total_agent_replies: 123,
    appointments: { pending: 0, confirmed: 4, completed: 4, cancelled: 1, no_show: 1, total: 10 },
    telegram_bots_connected: 2,
    owner_telegram_links: 1,
    llm_modes: { default: 6, own: 1 },
    pending_approvals: 0,
  },
  funnel: { signed_up: 7, connected_channel: 4, received_message: 3, booked_appointment: 2 },
  funnel_conversion: { connected_pct: 0.57, received_message_pct: 0.43, booked_pct: 0.29 },
  no_show_rate: 0.1,
  cancellation_rate: 0.1,
};

describe("Admin overview page", () => {
  it("prompts to sign in as admin when the session is not an admin", async () => {
    window.localStorage.setItem("tovayo.session", JSON.stringify({ businessId: "b" }));
    renderAdmin();
    expect(
      await screen.findByText("Sign in with an admin account to view platform analytics."),
    ).toBeInTheDocument();
  });

  it("shows platform totals and the funnel for an admin", async () => {
    asAdmin();
    adminOverview.mockResolvedValue(OVERVIEW);
    adminTimeseries.mockResolvedValue([{ day: "2026-06-01", count: 3 }]);

    renderAdmin();

    expect(await screen.findByText("7")).toBeInTheDocument(); // total businesses
    expect(screen.getByText("123")).toBeInTheDocument(); // agent replies
    expect(screen.getByText("Activation funnel")).toBeInTheDocument();
    expect(screen.getAllByText("No-show rate").length).toBeGreaterThan(0);
  });
});
