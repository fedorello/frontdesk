import { expect, type Page, test } from "@playwright/test";

// The onboarding wizard, end to end in the browser, with the API mocked at the
// network boundary so the test exercises the real UI flow (M5).

async function mockApi(page: Page): Promise<void> {
  // Generic catch-all first; specific routes registered after take priority.
  await page.route("**/api/businesses/**", (route) => route.fulfill({ json: {} }));
  await page.route("**/api/signup", (route) =>
    route.fulfill({ json: { token: "tok-1", business_id: "biz-1" } }),
  );
  await page.route("**/api/businesses/*/appointments*", (route) =>
    route.fulfill({ json: { items: [], total: 0 } }),
  );
  await page.route("**/api/businesses/*/conversations", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/businesses/*/telegram", (route) =>
    route.fulfill({ json: { connected: false } }),
  );
  await page.route("**/api/businesses/*/telegram/connect", (route) =>
    route.fulfill({ json: { connected: true, username: "ana_bot" } }),
  );
}

async function fillWizardToTelegram(page: Page): Promise<void> {
  await page.getByLabel("Email").fill("ana@example.com");
  await page.getByLabel("Password").fill("s3cret");
  await page.getByLabel("Business name").fill("Ana Studio");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByLabel("Service name").fill("Haircut");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click(); // AI: managed default
}

test("signs up, configures, connects Telegram, and lands on the dashboard", async ({ page }) => {
  await mockApi(page);
  await page.goto("/onboarding");
  await expect(page.getByRole("heading", { name: "Set up your receptionist" })).toBeVisible();

  await fillWizardToTelegram(page);

  await page.getByLabel(/Bot token/).fill("123:FAKE");
  await page.getByRole("button", { name: "Connect" }).click();
  await expect(page.getByText("Connected as @ana_bot")).toBeVisible();

  await page.getByRole("button", { name: "Go to dashboard" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
});

test("can skip Telegram and still finish onboarding", async ({ page }) => {
  await mockApi(page);
  await page.goto("/onboarding");
  await fillWizardToTelegram(page);

  await page.getByRole("button", { name: "Skip for now" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
});

test("the wizard is internationalized via the language switcher", async ({ page }) => {
  await page.goto("/onboarding");
  // The switcher is a dropdown button (not a native <select>): open it, then pick Russian.
  await page.getByLabel("Language").click();
  await page.getByRole("button", { name: "Русский" }).click();
  await expect(page.getByRole("heading", { name: "Настройте вашего ресепшиониста" })).toBeVisible();
});
