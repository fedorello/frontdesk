import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import CallsPage from "./page";

const { voiceDemoNumbers, features, requestFeature } = vi.hoisted(() => ({
  voiceDemoNumbers: vi.fn(),
  features: vi.fn(),
  requestFeature: vi.fn(),
}));
vi.mock("@/app/lib/api", () => ({ api: { voiceDemoNumbers, features, requestFeature } }));
vi.mock("@/app/lib/session", () => ({
  getSession: () => ({ businessId: "biz", email: "a@b.c" }),
}));

const VOICE = {
  key: "voice_receptionist",
  name: "Voice receptionist",
  description: "Answers calls.",
  pricing: "$1 per call",
  status: null,
};

afterEach(() => {
  cleanup();
  voiceDemoNumbers.mockReset();
  features.mockReset();
  requestFeature.mockReset();
});

function renderPage() {
  return render(
    <I18nProvider>
      <CallsPage />
    </I18nProvider>,
  );
}

describe("Calls page", () => {
  it("lists the demo numbers and a connect request button", async () => {
    voiceDemoNumbers.mockResolvedValue([
      { language: "ru", e164: "+19306001900", label: "Русский" },
    ]);
    features.mockResolvedValue([VOICE]);
    renderPage();

    const link = await screen.findByText("+19306001900");
    expect(link.closest("a")).toHaveAttribute("href", "tel:+19306001900");
    expect(screen.getByRole("button", { name: "Request to connect" })).toBeInTheDocument();
  });

  it("sends a connect request and shows the pending status", async () => {
    voiceDemoNumbers.mockResolvedValue([]);
    features.mockResolvedValue([VOICE]);
    requestFeature.mockResolvedValue({ ...VOICE, status: "requested" });
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Request to connect" }));

    expect(await screen.findByText("Requested — pending review")).toBeInTheDocument();
    expect(requestFeature).toHaveBeenCalledWith("biz", "voice_receptionist");
  });
});
