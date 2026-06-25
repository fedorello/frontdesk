interface Conversation {
  customer: string;
  lastMessage: string;
  reply: string;
  when: string;
}

// TODO(phase-8): fetch from the dashboard API (GET /api/conversations).
const RECENT: Conversation[] = [
  {
    customer: "+59899…",
    lastMessage: "Can I get a haircut at 3pm?",
    reply: "You're booked for 3pm! We'll remind you. ✅",
    when: "2m ago",
  },
  {
    customer: "+59891…",
    lastMessage: "What are your opening hours?",
    reply: "We're open 9 to 17, Monday to Friday.",
    when: "1h ago",
  },
];

export default function ConversationsPage() {
  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Conversations</h1>
      <p className="mt-2 text-sm text-zinc-500">
        What customers asked and how the assistant replied.
      </p>

      <ul className="mt-8 space-y-4">
        {RECENT.map((conversation) => (
          <li
            key={conversation.customer}
            className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800"
          >
            <div className="flex items-center justify-between text-xs text-zinc-500">
              <span>{conversation.customer}</span>
              <span>{conversation.when}</span>
            </div>
            <p className="mt-2 text-sm">
              <span className="text-zinc-500">Them:</span> {conversation.lastMessage}
            </p>
            <p className="mt-1 text-sm">
              <span className="text-zinc-500">Frontdesk:</span> {conversation.reply}
            </p>
          </li>
        ))}
      </ul>
    </main>
  );
}
