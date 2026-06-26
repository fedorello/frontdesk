import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import { ServiceCard, type Service } from "./ServiceCard";

const service: Service = {
  id: "s1",
  name: "Haircut",
  duration_minutes: 60,
  price_cents: 80000,
  currency: "UYU",
  working_hours: [],
};

function renderCard(props: Partial<Parameters<typeof ServiceCard>[0]> = {}) {
  return render(
    <I18nProvider>
      <ServiceCard service={service} onSave={async () => {}} onRemove={() => {}} {...props} />
    </I18nProvider>,
  );
}

afterEach(cleanup);

describe("ServiceCard", () => {
  it("shows a summary and expands to reveal the schedule editor", () => {
    renderCard();
    expect(screen.getByText("Haircut")).toBeInTheDocument();
    expect(screen.queryByText("Bookable hours")).not.toBeInTheDocument(); // collapsed

    fireEvent.click(screen.getByText("Edit"));
    expect(screen.getByText("Bookable hours")).toBeInTheDocument();
    expect(screen.getByLabelText("Currency")).toBeInTheDocument();
  });

  it("saves the edited service with price in cents", () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    renderCard({ onSave, startOpen: true });

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(onSave).toHaveBeenCalledTimes(1);
    const saved = onSave.mock.calls[0][0] as Service;
    expect(saved.id).toBe("s1");
    expect(saved.price_cents).toBe(80000); // amount 800 → 80000 cents
    expect(saved.currency).toBe("UYU");
  });

  it("removes the service", () => {
    const onRemove = vi.fn();
    renderCard({ onRemove });
    fireEvent.click(screen.getByText("Remove"));
    expect(onRemove).toHaveBeenCalledWith("s1");
  });
});
