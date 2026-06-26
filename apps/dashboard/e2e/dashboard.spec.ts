import { expect, test } from "@playwright/test";

test("the calendar shows today's appointments", async ({ page }) => {
  await page.goto("/calendar");

  await expect(page.getByRole("heading", { name: "Calendar" })).toBeVisible();
  await expect(page.getByText("Haircut").first()).toBeVisible();
});

test("approving a pending action clears it from the inbox", async ({ page }) => {
  // Mock the approvals API: one pending request until it's approved.
  let approved = false;
  await page.route("**/api/approvals**", async (route) => {
    if (route.request().method() === "POST") {
      approved = true;
      await route.fulfill({ json: { status: "approved" } });
    } else {
      await route.fulfill({
        json: approved
          ? []
          : [
              {
                id: "a1",
                summary: "Refund for +59899",
                tool: "issue_refund",
                args: { appointment_id: "ap-1" },
                risk: "sensitive",
              },
            ],
      });
    }
  });

  await page.goto("/approvals");
  await expect(page.getByText(/Refund for/)).toBeVisible();

  await page.getByRole("button", { name: "Approve" }).click();

  await expect(page.getByText(/Nothing waiting/)).toBeVisible();
});
