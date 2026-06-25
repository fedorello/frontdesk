import { expect, test } from "@playwright/test";

test("the calendar shows today's appointments", async ({ page }) => {
  await page.goto("/calendar");

  await expect(page.getByRole("heading", { name: "Calendar" })).toBeVisible();
  await expect(page.getByText("Haircut").first()).toBeVisible();
});

test("approving a pending action clears it from the inbox", async ({ page }) => {
  await page.goto("/approvals");
  await expect(page.getByText(/Refund for/)).toBeVisible();

  await page.getByRole("button", { name: "Approve" }).click();

  await expect(page.getByText(/Refund for/)).toHaveCount(0);
  await expect(page.getByText(/Nothing waiting/)).toBeVisible();
});
