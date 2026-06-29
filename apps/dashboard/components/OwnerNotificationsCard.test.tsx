import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { OwnerTelegram } from "@/app/lib/api";
import { I18nProvider } from "@/app/lib/I18nProvider";
import { OwnerNotificationsCard } from "./OwnerNotificationsCard";

const LINKED: OwnerTelegram = { linked: true, telegram_name: "Fedor", notifications_enabled: true };

function renderCard(props: Partial<Parameters<typeof OwnerNotificationsCard>[0]> = {}) {
  return render(
    <I18nProvider>
      <OwnerNotificationsCard status={LINKED} onToggle={() => {}} onUnlink={() => {}} {...props} />
    </I18nProvider>,
  );
}

afterEach(cleanup);

describe("OwnerNotificationsCard", () => {
  it("shows how to link (with the /connect command) when not linked", () => {
    renderCard({ status: { linked: false, telegram_name: null, notifications_enabled: false } });
    expect(screen.getByText(/\/connect/)).toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
  });

  it("shows the linked account and an enabled toggle", () => {
    renderCard();
    expect(screen.getByText(/Fedor/)).toBeInTheDocument();
    expect(screen.getByRole("switch")).toBeChecked();
  });

  it("toggles notifications off", () => {
    const onToggle = vi.fn();
    renderCard({ onToggle });
    fireEvent.click(screen.getByRole("switch"));
    expect(onToggle).toHaveBeenCalledWith(false);
  });

  it("unlinks", () => {
    const onUnlink = vi.fn();
    renderCard({ status: { ...LINKED, notifications_enabled: false }, onUnlink });
    fireEvent.click(screen.getByText("Unlink"));
    expect(onUnlink).toHaveBeenCalledTimes(1);
  });
});
