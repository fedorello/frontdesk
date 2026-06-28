import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { I18nProvider, useI18n } from "./I18nProvider";
import { LanguageSwitcher } from "./LanguageSwitcher";

function Probe() {
  const { t } = useI18n();
  return <p>{t("onboarding.signUp")}</p>;
}

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
});
