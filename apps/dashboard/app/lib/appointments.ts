import type { MessageKey } from "./i18n";

// Backend AppointmentStatus values (see domain/enums.py).
export const PENDING = "pending";
export const CANCELLED = "cancelled";

// Status value → localized chip label key.
export const STATUS_LABEL: Record<string, MessageKey> = {
  pending: "calendar.statusPending",
  confirmed: "calendar.statusConfirmed",
  completed: "calendar.statusCompleted",
  cancelled: "calendar.statusCancelled",
};

export function isCancelled(status: string): boolean {
  return status === CANCELLED;
}
