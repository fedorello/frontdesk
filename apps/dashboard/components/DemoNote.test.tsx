import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DemoNote } from "./DemoNote";

describe("DemoNote", () => {
  it("explains what the demo shows", () => {
    render(<DemoNote />);

    expect(screen.getByText("What this demo shows")).toBeInTheDocument();
    expect(screen.getByText(/real AI agent/)).toBeInTheDocument();
  });
});
