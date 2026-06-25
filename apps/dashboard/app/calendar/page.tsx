interface Appointment {
  time: string;
  customer: string;
  service: string;
  status: "confirmed" | "pending" | "cancelled";
}

// TODO(phase-8): fetch from the dashboard API (GET /api/appointments?day=today).
const TODAY: Appointment[] = [
  { time: "13:00", customer: "+59899…", service: "Haircut", status: "confirmed" },
  { time: "15:00", customer: "+59891…", service: "Haircut", status: "pending" },
  { time: "16:30", customer: "+59897…", service: "Colour", status: "confirmed" },
];

const STATUS_STYLES: Record<Appointment["status"], string> = {
  confirmed: "text-emerald-600",
  pending: "text-amber-600",
  cancelled: "text-zinc-400 line-through",
};

export default function CalendarPage() {
  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Calendar</h1>
      <p className="mt-2 text-sm text-zinc-500">
        Today&apos;s appointments, booked by the assistant.
      </p>

      <ul className="mt-8 divide-y divide-zinc-200 dark:divide-zinc-800">
        {TODAY.map((appointment) => (
          <li key={appointment.time} className="flex items-center justify-between py-3">
            <div>
              <span className="font-medium tabular-nums">{appointment.time}</span>
              <span className="text-zinc-500"> · {appointment.service}</span>
            </div>
            <div className="text-sm text-zinc-500">
              {appointment.customer} ·{" "}
              <span className={STATUS_STYLES[appointment.status]}>{appointment.status}</span>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
