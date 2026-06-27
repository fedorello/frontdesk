import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import ConversationsPage from "./page";

const { conversations, getBusiness, sendOwnerMessage, setHandoff, q } = vi.hoisted(() => ({
  conversations: vi.fn(),
  getBusiness: vi.fn(),
  sendOwnerMessage: vi.fn(),
  setHandoff: vi.fn(),
  q: { value: "" },
}));
vi.mock("@/app/lib/api", () => ({
  api: { conversations, getBusiness, sendOwnerMessage, setHandoff },
}));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(q.value ? `q=${q.value}` : ""),
}));

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  conversations.mockReset();
  getBusiness.mockReset();
  sendOwnerMessage.mockReset();
  setHandoff.mockReset();
  q.value = "";
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
    getBusiness.mockResolvedValue({ name: "B", timezone: "UTC" });
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
    getBusiness.mockResolvedValue({ name: "B", timezone: "UTC" });
    renderPage();

    // The list shows the customer (no message content — just who + when).
    const row = await screen.findByText("Mara");
    expect(screen.queryByText("Booked for 3pm 👍")).not.toBeInTheDocument(); // no preview in the list

    fireEvent.click(row);

    // The thread now shows both messages and their times.
    expect(screen.getByText("Can I book today?")).toBeInTheDocument();
    expect(screen.getByText("14:58")).toBeInTheDocument();
    expect(screen.getByText("15:00")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /All conversations/ }));
    expect(screen.queryByText("Can I book today?")).not.toBeInTheDocument(); // back to the list
  });

  it("lets the owner reply, calling the takeover API with the customer id", async () => {
    signIn();
    conversations.mockResolvedValue([
      {
        customer: "Mara",
        customer_id: "c1",
        handled: false,
        role: "customer",
        text: "Can I book?",
        at: "2026-06-26T14:58:00+00:00",
      },
    ]);
    getBusiness.mockResolvedValue({ name: "B", timezone: "UTC" });
    sendOwnerMessage.mockResolvedValue({ handled: true });
    renderPage();

    fireEvent.click(await screen.findByText("Mara"));
    fireEvent.change(screen.getByLabelText("Reply"), { target: { value: "On my way" } });
    fireEvent.click(screen.getByRole("button", { name: /Send/ }));

    await waitFor(() => expect(sendOwnerMessage).toHaveBeenCalledWith("b", "c1", "On my way", "t"));
  });

  it("sends on Cmd/Ctrl+Enter from the composer", async () => {
    signIn();
    conversations.mockResolvedValue([
      {
        customer: "Mara",
        customer_id: "c1",
        handled: false,
        role: "customer",
        text: "Can I book?",
        at: "2026-06-26T14:58:00+00:00",
      },
    ]);
    getBusiness.mockResolvedValue({ name: "B", timezone: "UTC" });
    sendOwnerMessage.mockResolvedValue({ handled: true });
    renderPage();

    fireEvent.click(await screen.findByText("Mara"));
    const composer = screen.getByLabelText("Reply");
    fireEvent.change(composer, { target: { value: "Two minutes" } });
    fireEvent.keyDown(composer, { key: "Enter", metaKey: true });

    await waitFor(() =>
      expect(sendOwnerMessage).toHaveBeenCalledWith("b", "c1", "Two minutes", "t"),
    );
  });

  it("filters the thread list by the ?q search param", async () => {
    signIn();
    conversations.mockResolvedValue([
      { customer: "Mara", role: "customer", text: "hi", at: "2026-06-26T15:00:00+00:00" },
      { customer: "Bob", role: "customer", text: "yo", at: "2026-06-26T15:00:00+00:00" },
    ]);
    getBusiness.mockResolvedValue({ name: "B", timezone: "UTC" });
    q.value = "mar";
    renderPage();

    expect(await screen.findByText("Mara")).toBeInTheDocument();
    expect(screen.queryByText("Bob")).not.toBeInTheDocument(); // filtered out
  });
});
