import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import ConversationsPage from "./page";

const { conversations } = vi.hoisted(() => ({ conversations: vi.fn() }));
vi.mock("@/app/lib/api", () => ({ api: { conversations } }));

afterEach(() => {
  window.localStorage.clear();
  conversations.mockReset();
});

function renderPage() {
  return render(
    <I18nProvider>
      <ConversationsPage />
    </I18nProvider>,
  );
}

function signIn() {
  window.localStorage.setItem("tovayo.session", JSON.stringify({ token: "t", businessId: "b" }));
}

// Newest-first feed (as the API returns it), two messages from one customer.
const FEED = [
  {
    customer: "Mara",
    role: "assistant",
    text: "Booked for 3pm 👍",
    at: "2026-06-26T15:00:00+00:00",
  },
  {
    customer: "Mara",
    role: "customer",
    text: "Can I book today?",
    at: "2026-06-26T14:58:00+00:00",
  },
];

describe("Conversations page", () => {
  it("shows the empty state when there are no conversations", async () => {
    signIn();
    conversations.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText("No conversations yet.")).toBeInTheDocument();
  });

  it("prompts to sign in when signed out", async () => {
    conversations.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText("Sign in to see your conversations.")).toBeInTheDocument();
  });

  it("opens a thread to show its messages oldest-first, then goes back", async () => {
    signIn();
    conversations.mockResolvedValue(FEED);
    renderPage();

    // The list shows the customer with their latest message.
    const row = await screen.findByText("Mara");
    expect(screen.getByText("Booked for 3pm 👍")).toBeInTheDocument();

    fireEvent.click(row);

    // The thread now shows both messages and their times.
    expect(screen.getByText("Can I book today?")).toBeInTheDocument();
    expect(screen.getByText("14:58")).toBeInTheDocument();
    expect(screen.getByText("15:00")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /All conversations/ }));
    expect(screen.queryByText("Can I book today?")).not.toBeInTheDocument(); // back to the list
  });
});
