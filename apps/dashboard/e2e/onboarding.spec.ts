import { expect, test } from "@playwright/test";

// The onboarding wizard, end to end in the browser, with the API mocked at the
// network boundary so the test exercises the real UI flow (M5).

test("a new owner signs up, adds a service, picks AI, and connects Telegram", async ({ page }) => {
  await page.route("**/api/signup", (route) =>
    route.fulfill({ json: { token: "tok-1", business_id: "biz-1" } }),
  );
  await page.route("**/api/businesses/**", (route) => {
    if (route.request().url().includes("/telegram/connect")) {
      return route.fulfill({ json: { connected: true, username: "ana_bot" } });
    }
    return route.fulfill({ json: {} });
  });

  await page.goto("/onboarding");
  await expect(page.getByRole("heading", { name: "Set up your receptionist" })).toBeVisible();

  // Step — account + business
  await page.getByLabel("Email").fill("ana@example.com");
  await page.getByLabel("Password").fill("s3cret");
  await page.getByLabel("Business name").fill("Ana Studio");
  await page.getByRole("button", { name: "Create account" }).click();

  // Step — service
  await page.getByLabel("Service name").fill("Haircut");
  await page.getByRole("button", { name: "Next" }).click();

  // Step — AI (managed default is preselected)
  await page.getByRole("button", { name: "Next" }).click();

  // Step — Telegram
  await page.getByLabel(/Bot token/).fill("123:FAKE");
  await page.getByRole("button", { name: "Connect" }).click();
  await expect(page.getByText("Connected as @ana_bot")).toBeVisible();
});

test("the wizard is internationalized via the language switcher", async ({ page }) => {
  await page.goto("/onboarding");
  await page.getByLabel("Language").selectOption("ru");
  await expect(page.getByRole("heading", { name: "Настройте вашего ресепшиониста" })).toBeVisible();
});
