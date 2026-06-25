import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Nav } from "./Nav";

describe("Nav", () => {
  it("links to every section", () => {
    render(<Nav />);

    expect(screen.getByRole("link", { name: "Calendar" })).toHaveAttribute("href", "/calendar");
    expect(screen.getByRole("link", { name: "Approvals" })).toHaveAttribute("href", "/approvals");
  });
});
