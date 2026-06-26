const POINTS = [
  "You're chatting with a real AI agent (a live model) — not a script.",
  "Ask about services, check times, and book a real appointment — it writes to a real database, just like a customer messaging on WhatsApp.",
  "Open 🧠 Agent reasoning under any reply to see the agent's thoughts and the tools it called.",
  "Time is frozen for the demo, so the slots it offers stay bookable.",
];

export function DemoNote() {
  return (
    <aside className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-sm dark:border-zinc-800 dark:bg-zinc-900/50">
      <h2 className="font-medium">What this demo shows</h2>
      <p className="mt-1 text-zinc-500">
        Frontdesk is an open-source AI front desk for small service businesses — it answers
        messages, books appointments, and sends reminders. This is{" "}
        <span className="font-medium">Ana Studio</span>, a demo salon that offers one service
        (Haircut).
      </p>
      <ul className="mt-3 space-y-1.5 text-zinc-600 dark:text-zinc-300">
        {POINTS.map((point) => (
          <li key={point} className="flex gap-2">
            <span aria-hidden>•</span>
            <span>{point}</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
