import { expect, test } from "@playwright/test";

test("the calendar shows the business's live bookings", async ({ page }) => {
  await page.route("**/api/businesses/**/appointments", (route) =>
    route.fulfill({
      json: [
        {
          service: "Haircut",
          starts_at: "2026-06-26T13:00:00+00:00",
          ends_at: "2026-06-26T14:00:00+00:00",
          status: "confirmed",
        },
      ],
    }),
  );
  await page.addInitScript(() => {
    window.localStorage.setItem("tovayo.session", JSON.stringify({ token: "t", businessId: "b" }));
  });

  await page.goto("/calendar");

  await expect(page.getByRole("heading", { name: "Calendar" })).toBeVisible();
  await expect(page.getByText("Haircut")).toBeVisible(); // from the live endpoint
  await expect(page.getByText("13:00")).toBeVisible();
});

test("conversations shows the live message feed", async ({ page }) => {
  await page.route("**/api/businesses/**/conversations", (route) =>
    route.fulfill({
      json: [
        {
          customer: "55501",
          role: "customer",
          text: "Can I book?",
          at: "2026-06-26T09:00:00+00:00",
        },
      ],
    }),
  );
  await page.addInitScript(() => {
    window.localStorage.setItem("tovayo.session", JSON.stringify({ token: "t", businessId: "b" }));
  });

  await page.goto("/conversations");

  await expect(page.getByRole("heading", { name: "Conversations" })).toBeVisible();
  await expect(page.getByText("Can I book?")).toBeVisible(); // from the live endpoint
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
