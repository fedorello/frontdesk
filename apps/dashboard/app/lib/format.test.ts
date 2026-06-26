import { describe, expect, it } from "vitest";

import { formatDay, formatTime } from "./format";

describe("formatTime", () => {
  it("renders the stored UTC wall-clock time", () => {
    expect(formatTime("2026-06-26T09:05:00+00:00", "en")).toBe("09:05");
  });

  it("returns the input unchanged when it is not a date", () => {
    expect(formatTime("not-a-date", "en")).toBe("not-a-date");
  });
});

describe("formatDay", () => {
  it("renders a localized day", () => {
    expect(formatDay("2026-06-26T09:00:00+00:00", "en")).toMatch(/Jun/);
  });

  it("returns the input unchanged when it is not a date", () => {
    expect(formatDay("nope", "en")).toBe("nope");
  });
});
