import { expect, test } from "@playwright/test";

test("an existing owner logs in and reaches the dashboard", async ({ page }) => {
  await page.route("**/api/businesses/**", (route) => route.fulfill({ json: {} }));
  await page.route("**/api/businesses/*/appointments", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/businesses/*/conversations", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/login", (route) =>
    route.fulfill({ json: { token: "t", business_id: "b" } }),
  );

  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
  await page.getByLabel("Email").fill("ana@example.com");
  await page.getByLabel("Password").fill("s3cret");
  await page.getByRole("button", { name: "Log in" }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
});

test("a wrong password shows an error, not a crash", async ({ page }) => {
  await page.route("**/api/login", (route) =>
    route.fulfill({ status: 401, body: "invalid email or password" }),
  );

  await page.goto("/login");
  await page.getByLabel("Email").fill("ana@example.com");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: "Log in" }).click();

  // A clean, localized message — not the raw backend JSON.
  await expect(page.getByText("Invalid email or password.")).toBeVisible();
  await expect(page.getByText(/detail/)).toHaveCount(0);
});

test("a signed-out visitor reaches login from the dashboard button", async ({ page }) => {
  await page.route("**/api/businesses/**", (route) => route.fulfill({ json: [] }));
  await page.goto("/");
  await page.getByRole("link", { name: "Log in" }).first().click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
});
