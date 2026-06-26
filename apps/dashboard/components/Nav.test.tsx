import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import { Nav } from "./Nav";

describe("Nav", () => {
  it("links to every section, translated", () => {
    render(
      <I18nProvider>
        <Nav />
      </I18nProvider>,
    );

    expect(screen.getByRole("link", { name: "Calendar" })).toHaveAttribute("href", "/calendar");
    expect(screen.getByRole("link", { name: "Approvals" })).toHaveAttribute("href", "/approvals");

    // the language switcher re-labels the nav in place
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "ru" } });
    expect(screen.getByRole("link", { name: "Календарь" })).toHaveAttribute("href", "/calendar");
  });
});
