const SECTIONS = [
  { title: "Calendar", blurb: "Today's appointments and what's coming up." },
  { title: "Conversations", blurb: "What customers asked and how the assistant replied." },
  { title: "Settings", blurb: "Services, hours, knowledge base, and channels." },
  { title: "Approvals", blurb: "Sensitive actions waiting for your sign-off." },
] as const;

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Frontdesk — Admin</h1>
      <p className="mt-2 max-w-2xl text-sm text-zinc-500">
        Your AI front desk answers messages, books appointments, and reminds customers. This is
        where you watch what it did and sign off on anything sensitive.
      </p>

      <ul className="mt-10 grid gap-4 sm:grid-cols-2">
        {SECTIONS.map((section) => (
          <li
            key={section.title}
            className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800"
          >
            <h2 className="font-medium">{section.title}</h2>
            <p className="mt-1 text-sm text-zinc-500">{section.blurb}</p>
          </li>
        ))}
      </ul>
    </main>
  );
}
