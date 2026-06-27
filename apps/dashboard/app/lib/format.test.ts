import { describe, expect, it } from "vitest";

import { formatDay, formatTime, utcIsoToZonedInput, zonedToUtcIso } from "./format";

describe("zoned time helpers", () => {
  it("reads a datetime-local input as business-zone wall-clock and returns UTC", () => {
    // 16:00 in Montevideo (UTC-3) is 19:00 UTC.
    expect(zonedToUtcIso("2026-06-28T16:00", "America/Montevideo")).toBe(
      "2026-06-28T19:00:00.000Z",
    );
  });

  it("formats a UTC instant as the business-zone input value", () => {
    expect(utcIsoToZonedInput("2026-06-28T19:00:00Z", "America/Montevideo")).toBe(
      "2026-06-28T16:00",
    );
  });
});

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
