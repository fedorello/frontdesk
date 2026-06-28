import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import Home from "./page";

const { appointments, conversations, getBusiness } = vi.hoisted(() => ({
  appointments: vi.fn(),
  conversations: vi.fn(),
  getBusiness: vi.fn(),
}));
vi.mock("@/app/lib/api", () => ({ api: { appointments, conversations, getBusiness } }));

afterEach(() => {
  window.localStorage.clear();
  appointments.mockReset();
  conversations.mockReset();
  getBusiness.mockReset();
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
    window.localStorage.setItem("tovayo.session", JSON.stringify({ businessId: "b" }));
    appointments.mockResolvedValue([
      {
        id: "apt-1",
        service: "Haircut",
        starts_at: "2026-06-26T09:00:00+00:00",
        ends_at: "2026-06-26T10:00:00+00:00",
        status: "pending",
      },
      {
        id: "apt-2",
        service: "Old",
        starts_at: "2026-06-20T09:00:00+00:00",
        ends_at: "2026-06-20T10:00:00+00:00",
        status: "cancelled",
      },
    ]);
    conversations.mockResolvedValue([
      {
        customer: "55501",
        customer_name: "Mara",
        role: "assistant",
        text: "**Готово!** ✅",
        at: "2026-06-26T09:05:00+00:00",
      },
      { customer: "55501", role: "customer", text: "hi", at: "2026-06-26T09:00:00+00:00" },
    ]);
    getBusiness.mockResolvedValue({ name: "B", timezone: "UTC" });
    renderHome();
    expect(await screen.findByText("Haircut")).toBeInTheDocument();
    expect(screen.getByText("09:00")).toBeInTheDocument();
    expect(screen.getByText("Scheduled")).toBeInTheDocument(); // localized status
    expect(screen.queryByText("Old")).not.toBeInTheDocument(); // cancelled is hidden
    // Recent conversations: one row per customer (by name), linking into the thread.
    expect(screen.queryByText("Готово! ✅")).not.toBeInTheDocument(); // no message content
    const chat = screen.getByText("Mara");
    expect(chat.closest("a")).toHaveAttribute("href", "/conversations?open=55501");
  });
});
