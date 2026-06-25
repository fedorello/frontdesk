const SETTINGS = [
  {
    title: "Services",
    blurb: "What you offer, how long each takes, and the price.",
    items: ["Haircut · 60 min · $25", "Colour · 120 min · $70"],
  },
  {
    title: "Working hours",
    blurb: "When the assistant is allowed to book.",
    items: ["Mon–Fri · 09:00–17:00", "Sat–Sun · closed"],
  },
  {
    title: "Knowledge base",
    blurb: "Facts the assistant may answer from — and nothing it can't.",
    items: ["Opening hours", "Parking", "Cancellation policy"],
  },
  {
    title: "Channels",
    blurb: "Where customers reach you.",
    items: ["WhatsApp · +598…", "Telegram · @ana_studio_bot"],
  },
] as const;

export default function SettingsPage() {
  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      <p className="mt-2 text-sm text-zinc-500">
        How the assistant represents your business. Editing lands with the dashboard API.
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {SETTINGS.map((section) => (
          <section
            key={section.title}
            className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800"
          >
            <h2 className="font-medium">{section.title}</h2>
            <p className="mt-1 text-sm text-zinc-500">{section.blurb}</p>
            <ul className="mt-3 space-y-1 text-sm">
              {section.items.map((item) => (
                <li key={item} className="text-zinc-600 dark:text-zinc-300">
                  {item}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </main>
  );
}
