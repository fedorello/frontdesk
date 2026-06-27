import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import { CharCount } from "./CharCount";

afterEach(cleanup);

describe("CharCount", () => {
  it("shows how many characters remain", () => {
    render(
      <I18nProvider>
        <CharCount value="abc" max={10} />
      </I18nProvider>,
    );
    expect(screen.getByText("7 characters left")).toBeInTheDocument();
  });

  it("shows the overflow once past the limit", () => {
    render(
      <I18nProvider>
        <CharCount value="abcdef" max={3} />
      </I18nProvider>,
    );
    expect(screen.getByText("3 over the limit")).toBeInTheDocument();
  });
});
