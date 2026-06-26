import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";
import { ThemeProvider } from "@/app/lib/ThemeProvider";

import { Sidebar } from "./Sidebar";

vi.mock("next/navigation", () => ({ usePathname: () => "/calendar" }));

describe("Sidebar", () => {
  it("renders the nav, translated, and marks the active route", () => {
    render(
      <ThemeProvider>
        <I18nProvider>
          <Sidebar />
        </I18nProvider>
      </ThemeProvider>,
    );

    const calendar = screen.getByRole("link", { name: "Calendar" });
    expect(calendar).toHaveAttribute("href", "/calendar");
    expect(calendar).toHaveAttribute("aria-current", "page"); // active
    expect(screen.getByRole("link", { name: "Approvals" })).toHaveAttribute("href", "/approvals");
  });
});
