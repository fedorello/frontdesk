// Appointment statuses mirror the backend AppointmentStatus enum values.
const TONE: Record<string, string> = {
  pending: "bg-warning-soft text-warning",
  confirmed: "bg-success-soft text-success",
  cancelled: "bg-danger-soft text-danger",
};

/** A soft-colored status chip; unknown statuses fall back to neutral. */
export function StatusPill({ status, label }: { status: string; label?: string }) {
  const tone = TONE[status] ?? "bg-surface-3 text-muted";
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${tone}`}>
      {label ?? status}
    </span>
  );
}
