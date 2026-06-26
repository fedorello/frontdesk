import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import { BottomNav } from "./BottomNav";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

describe("BottomNav", () => {
  it("renders the nav and marks the active route", () => {
    render(
      <I18nProvider>
        <BottomNav />
      </I18nProvider>,
    );
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("href", "/settings");
  });
});
