import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BotStatusProvider } from "@/app/lib/BotStatusProvider";
import { I18nProvider } from "@/app/lib/I18nProvider";

import { BotStatus } from "./BotStatus";

const { telegramStatus } = vi.hoisted(() => ({ telegramStatus: vi.fn() }));
vi.mock("@/app/lib/api", () => ({ api: { telegramStatus } }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(() => {
  window.localStorage.clear();
  telegramStatus.mockReset();
});

function renderBot() {
  return render(
    <I18nProvider>
      <BotStatusProvider>
        <BotStatus />
      </BotStatusProvider>
    </I18nProvider>,
  );
}

function signIn() {
  window.localStorage.setItem("tovayo.session", JSON.stringify({ businessId: "b" }));
}

describe("BotStatus", () => {
  it("renders nothing without a session", () => {
    const { container } = renderBot();
    expect(container.textContent).toBe("");
  });

  it("shows the bot online with its username", async () => {
    signIn();
    telegramStatus.mockResolvedValue({ connected: true, username: "ana_bot" });
    renderBot();
    expect(await screen.findByText("Bot online")).toBeInTheDocument();
    expect(screen.getByText("@ana_bot")).toBeInTheDocument();
  });

  it("shows the bot offline when not connected", async () => {
    signIn();
    telegramStatus.mockResolvedValue({ connected: false });
    renderBot();
    expect(await screen.findByText("Bot offline")).toBeInTheDocument();
  });
});
