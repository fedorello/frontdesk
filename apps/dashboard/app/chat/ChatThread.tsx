import { Markdown } from "./Markdown";
import { Trace } from "./Trace";
import type { ChatMessage } from "./types";

export function ChatThread({ messages }: { messages: ChatMessage[] }) {
  if (messages.length === 0) {
    return (
      <p className="text-sm text-muted">
        Say hi 👋 — try <span className="font-medium">“Can I book a haircut?”</span>
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {messages.map((message, index) =>
        message.role === "user" ? (
          <div key={index} className="self-end text-right">
            <span className="inline-block whitespace-pre-wrap rounded-2xl bg-accent px-3 py-2 text-sm text-white ">
              {message.text}
            </span>
          </div>
        ) : (
          <div key={index} className="max-w-[85%] self-start">
            <div className="rounded-2xl bg-surface-3 px-3 py-2 text-sm ">
              <Markdown>{message.text}</Markdown>
            </div>
            <Trace steps={message.trace} />
          </div>
        ),
      )}
    </div>
  );
}
