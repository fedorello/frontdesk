import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatThread } from "./ChatThread";
import type { ChatMessage } from "./types";

describe("ChatThread", () => {
  it("renders the conversation in order", () => {
    const messages: ChatMessage[] = [
      { role: "user", text: "Can I book a haircut?" },
      { role: "assistant", text: "Sure — you're booked for 3pm!" },
    ];
    render(<ChatThread messages={messages} />);

    expect(screen.getByText("Can I book a haircut?")).toBeInTheDocument();
    expect(screen.getByText("Sure — you're booked for 3pm!")).toBeInTheDocument();
  });

  it("shows a prompt when empty", () => {
    render(<ChatThread messages={[]} />);

    expect(screen.getByText(/Say hi/)).toBeInTheDocument();
  });
});
