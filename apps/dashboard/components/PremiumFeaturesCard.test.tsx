import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import { PremiumFeaturesCard } from "./PremiumFeaturesCard";

const { features, requestFeature } = vi.hoisted(() => ({
  features: vi.fn(),
  requestFeature: vi.fn(),
}));
vi.mock("@/app/lib/api", () => ({ api: { features, requestFeature } }));

afterEach(() => {
  cleanup();
  features.mockReset();
  requestFeature.mockReset();
});

const VOICE = {
  key: "voice_receptionist",
  name: "Voice receptionist",
  description: "Answers calls.",
  pricing: "$1 per call",
  status: null,
};

function renderCard() {
  return render(
    <I18nProvider>
      <PremiumFeaturesCard businessId="biz" />
    </I18nProvider>,
  );
}

describe("PremiumFeaturesCard", () => {
  it("lists a catalog feature with a Request-access action", async () => {
    features.mockResolvedValue([VOICE]);
    renderCard();

    expect(await screen.findByText("Voice receptionist")).toBeInTheDocument();
    expect(screen.getByText(/Billing coming soon/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request access" })).toBeInTheDocument();
  });

  it("requests access and reflects the pending status", async () => {
    features.mockResolvedValue([VOICE]);
    requestFeature.mockResolvedValue({ ...VOICE, status: "requested" });
    renderCard();

    fireEvent.click(await screen.findByRole("button", { name: "Request access" }));

    expect(await screen.findByText("Requested — pending review")).toBeInTheDocument();
    expect(requestFeature).toHaveBeenCalledWith("biz", "voice_receptionist");
  });

  it("shows an Active chip for an active entitlement", async () => {
    features.mockResolvedValue([{ ...VOICE, status: "active" }]);
    renderCard();

    expect(await screen.findByText("Active")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Request access" })).not.toBeInTheDocument();
  });
});
