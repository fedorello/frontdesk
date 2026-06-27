import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import { DemoNote } from "./DemoNote";

describe("DemoNote", () => {
  it("explains what the demo shows, localized", () => {
    render(
      <I18nProvider>
        <DemoNote />
      </I18nProvider>,
    );

    expect(screen.getByText("What this demo shows")).toBeInTheDocument();
    expect(screen.getByText(/real AI agent/)).toBeInTheDocument();
    expect(screen.getByText(/Ana Studio/)).toBeInTheDocument(); // studio name interpolated
  });
});
