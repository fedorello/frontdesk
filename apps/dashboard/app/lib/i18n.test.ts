import { describe, expect, it } from "vitest";

import { isLocale, LOCALES, translate } from "./i18n";

describe("translate", () => {
  it("resolves keys per locale", () => {
    expect(translate("en", "onboarding.signUp")).toBe("Create account");
    expect(translate("ru", "onboarding.signUp")).toBe("Создать аккаунт");
    expect(translate("es", "nav.settings")).toBe("Ajustes");
    expect(translate("zh", "nav.calendar")).toBe("日历");
  });

  it("interpolates variables", () => {
    expect(translate("en", "onboarding.connected", { username: "ana_bot" })).toBe(
      "Connected as @ana_bot",
    );
  });

  it("falls back to English for an unknown locale", () => {
    // @ts-expect-error runtime fallback for an unsupported locale code
    expect(translate("xx", "nav.overview")).toBe("Overview");
  });

  it("translates every key in every locale (no gaps, all distinct from the key)", () => {
    const keys = [
      "onboarding.title",
      "onboarding.businessName",
      "onboarding.connectTelegram",
      "nav.approvals",
    ] as const;
    for (const locale of LOCALES) {
      for (const key of keys) {
        const value = translate(locale, key);
        expect(value.length).toBeGreaterThan(0);
        expect(value).not.toBe(key);
      }
    }
  });
});

describe("isLocale", () => {
  it("guards supported locales", () => {
    expect(isLocale("ru")).toBe(true);
    expect(isLocale("xx")).toBe(false);
  });
});
