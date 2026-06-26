import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Card } from "./Card";
import { EmptyState } from "./EmptyState";
import { Skeleton } from "./Skeleton";
import { StatCard } from "./StatCard";
import { StatusPill } from "./StatusPill";

describe("Card", () => {
  it("renders children inside a surface panel", () => {
    render(<Card className="x">hi</Card>);
    const panel = screen.getByText("hi");
    expect(panel).toBeInTheDocument();
    expect(panel.className).toContain("bg-surface");
  });
});

describe("StatCard", () => {
  it("shows the value and label", () => {
    render(<StatCard icon="calendar" tone="accent" label="Bookings" value={7} />);
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("Bookings")).toBeInTheDocument();
  });
});

describe("StatusPill", () => {
  it("colors a known status and falls back for an unknown one", () => {
    const { rerender } = render(<StatusPill status="confirmed" />);
    expect(screen.getByText("confirmed").className).toContain("text-success");

    rerender(<StatusPill status="weird" label="Weird" />);
    const pill = screen.getByText("Weird");
    expect(pill.className).toContain("text-muted"); // neutral fallback
  });
});

describe("EmptyState", () => {
  it("renders the title, and body/action only when given", () => {
    const { rerender } = render(<EmptyState icon="calendar" title="Nothing here" />);
    expect(screen.getByRole("heading", { name: "Nothing here" })).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();

    rerender(
      <EmptyState
        icon="calendar"
        title="Nothing here"
        body="Add one"
        action={<button type="button">Go</button>}
      />,
    );
    expect(screen.getByText("Add one")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go" })).toBeInTheDocument();
  });
});

describe("Skeleton", () => {
  it("renders a decorative pulsing block", () => {
    const { container } = render(<Skeleton className="h-8" />);
    const block = container.firstElementChild;
    expect(block?.className).toContain("animate-pulse");
    expect(block?.getAttribute("aria-hidden")).toBe("true");
  });
});
