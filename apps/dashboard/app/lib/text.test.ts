import { describe, expect, it } from "vitest";

import { plainPreview, stripMarkdown } from "./text";

describe("text helpers", () => {
  it("strips markdown markers but keeps emoji and newlines", () => {
    expect(stripMarkdown("**Готово!** ✅\n*линия*")).toBe("Готово! ✅\nлиния");
  });

  it("unwraps links to their label", () => {
    expect(stripMarkdown("see [docs](https://x.com)")).toBe("see docs");
  });

  it("collapses a preview to one trimmed line", () => {
    expect(plainPreview("**Новая запись:**\n  10:00  ")).toBe("Новая запись: 10:00");
  });
});
