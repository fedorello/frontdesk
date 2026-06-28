import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AppointmentView } from "@/app/lib/api";
import { I18nProvider } from "@/app/lib/I18nProvider";

import { AppointmentModal } from "./AppointmentModal";

const { cancelAppointment, rescheduleAppointment, confirmAppointment } = vi.hoisted(() => ({
  cancelAppointment: vi.fn(),
  rescheduleAppointment: vi.fn(),
  confirmAppointment: vi.fn(),
}));
vi.mock("@/app/lib/api", () => ({
  api: { cancelAppointment, rescheduleAppointment, confirmAppointment },
}));

afterEach(() => {
  cleanup();
  cancelAppointment.mockReset();
  rescheduleAppointment.mockReset();
  confirmAppointment.mockReset();
});

const APPOINTMENT: AppointmentView = {
  id: "apt-1",
  service: "Reading",
  starts_at: "2026-06-28T13:00:00+00:00",
  ends_at: "2026-06-28T14:00:00+00:00",
  status: "confirmed",
};

function renderModal(onChanged = vi.fn(), appointment: AppointmentView = APPOINTMENT) {
  render(
    <I18nProvider>
      <AppointmentModal
        appointment={appointment}
        timeZone="America/Montevideo"
        locale="en"
        businessId="b"
        onClose={vi.fn()}
        onChanged={onChanged}
      />
    </I18nProvider>,
  );
  return onChanged;
}

describe("AppointmentModal", () => {
  it("cancels with a reason and reports the result", async () => {
    cancelAppointment.mockResolvedValue({
      id: "apt-1",
      status: "cancelled",
      starts_at: APPOINTMENT.starts_at,
      ends_at: APPOINTMENT.ends_at,
    });
    const onChanged = renderModal();

    fireEvent.change(screen.getByLabelText("Cancellation reason"), {
      target: { value: "Specialist away" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Cancel booking" }));

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(cancelAppointment).toHaveBeenCalledWith("b", "apt-1", "Specialist away");
  });

  it("confirms a pending booking", async () => {
    confirmAppointment.mockResolvedValue({
      id: "apt-1",
      status: "confirmed",
      starts_at: APPOINTMENT.starts_at,
      ends_at: APPOINTMENT.ends_at,
    });
    const onChanged = renderModal(vi.fn(), { ...APPOINTMENT, status: "pending" });

    fireEvent.click(screen.getByRole("button", { name: "Confirm booking" }));

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(confirmAppointment).toHaveBeenCalledWith("b", "apt-1");
  });

  it("hides the confirm action for a non-pending booking", () => {
    renderModal(); // status: confirmed
    expect(screen.queryByRole("button", { name: "Confirm booking" })).toBeNull();
  });

  it("reschedules using the business-zone time converted to UTC", async () => {
    rescheduleAppointment.mockResolvedValue({
      id: "apt-1",
      status: "confirmed",
      starts_at: "2026-06-28T19:00:00.000Z",
      ends_at: "2026-06-28T20:00:00.000Z",
    });
    renderModal();

    fireEvent.change(screen.getByLabelText("New date & time"), {
      target: { value: "2026-06-28T16:00" }, // 16:00 Montevideo
    });
    fireEvent.click(screen.getByRole("button", { name: "Move" }));

    await waitFor(() =>
      expect(rescheduleAppointment).toHaveBeenCalledWith(
        "b",
        "apt-1",
        "2026-06-28T19:00:00.000Z", // converted to UTC
      ),
    );
  });
});
