import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";
import { I18nProvider } from "./I18nProvider";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { getSession } from "./session";

vi.mock("./api", () => ({ api: { setLocale: vi.fn().mockResolvedValue({ locale: "ru" }) } }));
vi.mock("./session", () => ({ getSession: vi.fn() }));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function pickRussian() {
  render(
    <I18nProvider>
      <LanguageSwitcher />
    </I18nProvider>,
  );
  fireEvent.click(screen.getByLabelText("Language"));
  fireEvent.click(screen.getByText("Русский"));
}

describe("LanguageSwitcher", () => {
  it("persists the chosen language to the business when signed in", () => {
    vi.mocked(getSession).mockReturnValue({ businessId: "b" });
    pickRussian();
    expect(api.setLocale).toHaveBeenCalledWith("b", "ru");
  });

  it("does not call the API when signed out", () => {
    vi.mocked(getSession).mockReturnValue(null);
    pickRussian();
    expect(api.setLocale).not.toHaveBeenCalled();
  });
});
