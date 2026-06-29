import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AppointmentQuery, AppointmentView } from "@/app/lib/api";
import { I18nProvider } from "@/app/lib/I18nProvider";

import CalendarPage from "./page";

const { appointments, getBusiness, confirmAppointment } = vi.hoisted(() => ({
  appointments: vi.fn(),
  getBusiness: vi.fn(),
  confirmAppointment: vi.fn(),
}));
vi.mock("@/app/lib/api", () => ({ api: { appointments, getBusiness, confirmAppointment } }));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams() }));

afterEach(() => {
  cleanup(); // unmount between tests so the DOM (and its toggle/cards) doesn't leak
  window.localStorage.clear();
  appointments.mockReset();
  getBusiness.mockReset();
  confirmAppointment.mockReset();
});

function renderCalendar() {
  return render(
    <I18nProvider>
      <CalendarPage />
    </I18nProvider>,
  );
}

function signIn() {
  window.localStorage.setItem("tovayo.session", JSON.stringify({ businessId: "b" }));
}

function appt(over: Partial<AppointmentView>): AppointmentView {
  return {
    id: "a1",
    service: "Service",
    starts_at: "2026-06-28T13:00:00+00:00",
    ends_at: "2026-06-28T14:00:00+00:00",
    status: "confirmed",
    ...over,
  };
}

describe("Calendar page", () => {
  it("shows the empty state when there are no bookings", async () => {
    signIn();
    appointments.mockResolvedValue({ items: [], total: 0 });
    getBusiness.mockResolvedValue({ name: "B", timezone: "UTC" });
    renderCalendar();
    expect(await screen.findByText("No bookings yet.")).toBeInTheDocument();
  });

  it("shows the booking code and the time in the business time zone", async () => {
    signIn();
    appointments.mockResolvedValue({
      items: [
        appt({
          id: "c1f39102-167e-4523",
          service: "Manicure",
          starts_at: "2026-06-26T13:30:00+00:00", // 10:30 in Montevideo (UTC-3)
          ends_at: "2026-06-26T14:30:00+00:00",
          intake: [{ name: "Birth date", value: "1990-01-01" }],
        }),
      ],
      total: 1,
    });
    getBusiness.mockResolvedValue({ name: "B", timezone: "America/Montevideo" });
    renderCalendar();

    expect(await screen.findByText("Manicure")).toBeInTheDocument();
    expect(screen.getByText("10:30")).toBeInTheDocument(); // converted to the business zone
    expect(screen.queryByText("13:30")).not.toBeInTheDocument(); // not the raw UTC
    expect(screen.getByText("Code: c1f39102-167e-4523")).toBeInTheDocument();
    expect(screen.getByText("Confirmed")).toBeInTheDocument(); // localized, not raw "confirmed"
    expect(screen.getByText("Birth date:")).toBeInTheDocument();
  });

  it("confirms a pending booking, then refetches the page from the server", async () => {
    signIn();
    appointments
      .mockResolvedValueOnce({
        items: [appt({ id: "apt-1", service: "Reading", status: "pending" })],
        total: 1,
      })
      .mockResolvedValue({
        items: [appt({ id: "apt-1", service: "Reading", status: "confirmed" })],
        total: 1,
      });
    getBusiness.mockResolvedValue({ name: "B", timezone: "UTC" });
    confirmAppointment.mockResolvedValue({ id: "apt-1", status: "confirmed" });
    renderCalendar();

    fireEvent.click(await screen.findByRole("button", { name: "Confirm" }));

    await waitFor(() => expect(screen.getByText("Confirmed")).toBeInTheDocument());
    expect(confirmAppointment).toHaveBeenCalledWith("b", "apt-1");
    expect(screen.queryByRole("button", { name: "Confirm" })).not.toBeInTheDocument();
  });

  it("reveals cancelled bookings by refetching with includeCancelled", async () => {
    signIn();
    const active = appt({ id: "a1", service: "Active" });
    const gone = appt({ id: "a2", service: "Gone", status: "cancelled" });
    appointments.mockImplementation((_bid: string, query: AppointmentQuery) =>
      Promise.resolve(
        query.includeCancelled
          ? { items: [active, gone], total: 2 }
          : { items: [active], total: 1 },
      ),
    );
    getBusiness.mockResolvedValue({ name: "B", timezone: "UTC" });
    renderCalendar();

    expect(await screen.findByText("Active")).toBeInTheDocument();
    expect(screen.queryByText("Gone")).not.toBeInTheDocument(); // cancelled hidden by default

    fireEvent.click(screen.getByRole("switch", { name: "Show cancelled" }));

    expect(await screen.findByText("Gone")).toBeInTheDocument(); // re-fetched, now included
  });

  it("paginates: Next fetches the next page from the server, not the whole list", async () => {
    signIn();
    appointments.mockImplementation((_bid: string, query: AppointmentQuery) =>
      Promise.resolve(
        query.offset === 0
          ? { items: [appt({ id: "p1", service: "First page" })], total: 9 }
          : { items: [appt({ id: "p2", service: "Second page" })], total: 9 },
      ),
    );
    getBusiness.mockResolvedValue({ name: "B", timezone: "UTC" });
    renderCalendar();

    expect(await screen.findByText("First page")).toBeInTheDocument();
    expect(screen.getByText("1 / 2")).toBeInTheDocument(); // 9 total over a page size of 8

    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByText("Second page")).toBeInTheDocument();
    expect(appointments).toHaveBeenLastCalledWith("b", expect.objectContaining({ offset: 8 }));
  });
});
