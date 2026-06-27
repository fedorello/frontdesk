import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import CalendarPage from "./page";

const { appointments, getBusiness } = vi.hoisted(() => ({
  appointments: vi.fn(),
  getBusiness: vi.fn(),
}));
vi.mock("@/app/lib/api", () => ({ api: { appointments, getBusiness } }));

afterEach(() => {
  window.localStorage.clear();
  appointments.mockReset();
  getBusiness.mockReset();
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
    getBusiness.mockResolvedValue({ name: "B", timezone: "UTC" });
    renderCalendar();
    expect(await screen.findByText("No bookings yet.")).toBeInTheDocument();
  });

  it("shows the booking code and the time in the business time zone", async () => {
    signIn();
    appointments.mockResolvedValue([
      {
        id: "c1f39102-167e-4523",
        service: "Manicure",
        starts_at: "2026-06-26T13:30:00+00:00", // 10:30 in Montevideo (UTC-3)
        ends_at: "2026-06-26T14:30:00+00:00",
        status: "confirmed",
        intake: [{ name: "Birth date", value: "1990-01-01" }],
      },
    ]);
    getBusiness.mockResolvedValue({ name: "B", timezone: "America/Montevideo" });
    renderCalendar();

    expect(await screen.findByText("Manicure")).toBeInTheDocument();
    expect(screen.getByText("10:30")).toBeInTheDocument(); // converted to the business zone
    expect(screen.queryByText("13:30")).not.toBeInTheDocument(); // not the raw UTC
    expect(screen.getByText("Code: c1f39102-167e-4523")).toBeInTheDocument();
    expect(screen.getByText("Confirmed")).toBeInTheDocument(); // localized, not raw "confirmed"
    expect(screen.getByText("Birth date:")).toBeInTheDocument();
  });
});
