import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import Home from "./page";

const { appointments, conversations } = vi.hoisted(() => ({
  appointments: vi.fn(),
  conversations: vi.fn(),
}));
vi.mock("@/app/lib/api", () => ({ api: { appointments, conversations } }));

afterEach(() => {
  window.localStorage.clear();
  appointments.mockReset();
  conversations.mockReset();
});

function renderHome() {
  return render(
    <I18nProvider>
      <Home />
    </I18nProvider>,
  );
}

describe("Overview page", () => {
  it("prompts to sign in when there is no session", async () => {
    renderHome();
    expect(await screen.findByText("Welcome to tovayo")).toBeInTheDocument();
  });

  it("shows real bookings + messages when signed in", async () => {
    window.localStorage.setItem("tovayo.session", JSON.stringify({ token: "t", businessId: "b" }));
    appointments.mockResolvedValue([
      {
        service: "Haircut",
        starts_at: "2026-06-26T09:00:00+00:00",
        ends_at: "2026-06-26T10:00:00+00:00",
        status: "pending",
      },
    ]);
    conversations.mockResolvedValue([
      { customer: "55501", role: "customer", text: "hi", at: "2026-06-26T09:00:00+00:00" },
    ]);
    renderHome();
    expect(await screen.findByText("Haircut")).toBeInTheDocument();
    expect(screen.getByText("09:00")).toBeInTheDocument();
  });
});
