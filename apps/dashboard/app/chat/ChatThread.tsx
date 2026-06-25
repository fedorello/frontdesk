import type { ChatMessage } from "./types";

export function ChatThread({ messages }: { messages: ChatMessage[] }) {
  if (messages.length === 0) {
    return (
      <p className="text-sm text-zinc-500">
        Say hi 👋 — try <span className="font-medium">“Can I book a haircut?”</span>
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {messages.map((message, index) => (
        <div key={index} className={message.role === "user" ? "self-end text-right" : "self-start"}>
          <span
            className={
              message.role === "user"
                ? "inline-block whitespace-pre-wrap rounded-2xl bg-zinc-900 px-3 py-2 text-sm text-white dark:bg-white dark:text-zinc-900"
                : "inline-block whitespace-pre-wrap rounded-2xl bg-zinc-100 px-3 py-2 text-sm dark:bg-zinc-800"
            }
          >
            {message.text}
          </span>
        </div>
      ))}
    </div>
  );
}
