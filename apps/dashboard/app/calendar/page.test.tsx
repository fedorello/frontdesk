import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import CalendarPage from "./page";

const { appointments } = vi.hoisted(() => ({ appointments: vi.fn() }));
vi.mock("@/app/lib/api", () => ({ api: { appointments } }));

afterEach(() => {
  window.localStorage.clear();
  appointments.mockReset();
});

function renderCalendar() {
  return render(
    <I18nProvider>
      <CalendarPage />
    </I18nProvider>,
  );
}

function signIn() {
  window.localStorage.setItem("tovayo.session", JSON.stringify({ token: "t", businessId: "b" }));
}

describe("Calendar page", () => {
  it("shows the empty state when there are no bookings", async () => {
    signIn();
    appointments.mockResolvedValue([]);
    renderCalendar();
    expect(await screen.findByText("No bookings yet.")).toBeInTheDocument();
  });

  it("renders an appointment card with time, service and status", async () => {
    signIn();
    appointments.mockResolvedValue([
      {
        service: "Manicure",
        starts_at: "2026-06-26T13:30:00+00:00",
        ends_at: "2026-06-26T14:00:00+00:00",
        status: "confirmed",
      },
    ]);
    renderCalendar();
    expect(await screen.findByText("Manicure")).toBeInTheDocument();
    expect(screen.getByText("13:30")).toBeInTheDocument();
    expect(screen.getByText("confirmed")).toBeInTheDocument();
  });
});
