import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";
import { I18nProvider, useI18n } from "./I18nProvider";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { readLocaleCookie } from "./localeCookie";
import { getSession } from "./session";

vi.mock("./session", () => ({ getSession: vi.fn() }));
vi.mock("./api", () => ({ api: { getBusiness: vi.fn(), setLocale: vi.fn() } }));
vi.mock("./localeCookie", () => ({ readLocaleCookie: vi.fn(), writeLocaleCookie: vi.fn() }));

function Probe() {
  const { t } = useI18n();
  return <p>{t("onboarding.signUp")}</p>;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getSession).mockReturnValue(null);
  vi.mocked(readLocaleCookie).mockReturnValue(null);
  vi.mocked(api.setLocale).mockResolvedValue({ locale: "ru" });
});
afterEach(cleanup);

describe("I18nProvider", () => {
  it("provides translations and switches locale at runtime", () => {
    render(
      <I18nProvider>
        <LanguageSwitcher />
        <Probe />
      </I18nProvider>,
    );

    expect(screen.getByText("Create account")).toBeTruthy(); // default English
    fireEvent.click(screen.getByLabelText("Language")); // open the dropdown
    fireEvent.click(screen.getByText("Русский")); // pick Russian
    expect(screen.getByText("Создать аккаунт")).toBeTruthy(); // switched to Russian
  });

  it("throws when useI18n is used outside the provider", () => {
    expect(() => render(<Probe />)).toThrow(/I18nProvider/);
  });

  it("makes the business's saved language the source of truth, overriding the cookie cache", async () => {
    vi.mocked(getSession).mockReturnValue({ businessId: "b" });
    vi.mocked(readLocaleCookie).mockReturnValue("en"); // a stale cache says English
    vi.mocked(api.getBusiness).mockResolvedValue({ name: "X", timezone: "UTC", locale: "ru" });

    render(
      <I18nProvider>
        <Probe />
      </I18nProvider>,
    );

    expect(screen.getByText("Create account")).toBeTruthy(); // fast paint from the cache
    expect(await screen.findByText("Создать аккаунт")).toBeTruthy(); // reconciled to business.locale
  });

  it("persists a switch to the business as a single authoritative write", () => {
    vi.mocked(getSession).mockReturnValue({ businessId: "b" });
    render(
      <I18nProvider>
        <LanguageSwitcher />
        <Probe />
      </I18nProvider>,
    );

    fireEvent.click(screen.getByLabelText("Language"));
    fireEvent.click(screen.getByText("Русский"));

    expect(api.setLocale).toHaveBeenCalledWith("b", "ru");
    expect(api.setLocale).toHaveBeenCalledTimes(1); // one writer, no duplicate
  });
});
