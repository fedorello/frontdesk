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

test("settings loads the live business config for editing", async ({ page }) => {
  await page.route("**/api/businesses/*/services", (route) =>
    route.fulfill({ json: [{ id: "svc1", name: "Haircut", duration_minutes: 60 }] }),
  );
  await page.route("**/api/businesses/*/resources", (route) =>
    route.fulfill({ json: [{ id: "g1", name: "Ana", working_hours: [] }] }),
  );
  await page.route("**/api/businesses/*/llm", (route) =>
    route.fulfill({ json: { mode: "default" } }),
  );
  await page.route("**/api/businesses/*/telegram-owner", (route) =>
    route.fulfill({
      json: { linked: true, telegram_name: "Fedor", notifications_enabled: true },
    }),
  );
  await page.route("**/api/businesses/*", (route) =>
    route.request().method() === "GET"
      ? route.fulfill({ json: { name: "Ana Studio", timezone: "UTC", knowledge: [] } })
      : route.fulfill({ json: {} }),
  );
  await page.addInitScript(() => {
    window.localStorage.setItem("tovayo.session", JSON.stringify({ businessId: "b" }));
  });

  await page.goto("/settings");

  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByLabel("Business name")).toHaveValue("Ana Studio"); // live profile
  await expect(page.getByText("Haircut", { exact: true })).toBeVisible(); // live services
  await expect(page.getByRole("heading", { name: "Groups" })).toBeVisible(); // groups section
  await expect(page.getByText("Ana", { exact: true })).toBeVisible(); // the live group
  await expect(page.getByText("Linked: Fedor")).toBeVisible(); // owner notifications section
});

test("the connect-telegram page confirms an owner link code", async ({ page }) => {
  let confirmedCode: string | null = null;
  await page.route("**/api/businesses/*/telegram-owner/confirm", async (route) => {
    confirmedCode = JSON.parse(route.request().postData() ?? "{}").code;
    await route.fulfill({
      json: { linked: true, telegram_name: "Fedor", notifications_enabled: true },
    });
  });
  await page.addInitScript(() => {
    window.localStorage.setItem("tovayo.session", JSON.stringify({ businessId: "b" }));
  });

  await page.goto("/connect-telegram?code=abc-123");

  await expect(page.getByText(/schedule notifications in Telegram/)).toBeVisible();
  expect(confirmedCode).toBe("abc-123");
});

test("a service's group is chosen from the group selector, not a per-service schedule", async ({
  page,
}) => {
  await page.route("**/api/businesses/*/services", (route) =>
    route.fulfill({
      json: [{ id: "svc1", name: "Haircut", duration_minutes: 60, resource_ids: ["g1"] }],
    }),
  );
  await page.route("**/api/businesses/*/resources", (route) =>
    route.fulfill({
      json: [
        { id: "g1", name: "Ana", working_hours: [] },
        { id: "g2", name: "Bob", working_hours: [] },
      ],
    }),
  );
  await page.route("**/api/businesses/*/llm", (route) =>
    route.fulfill({ json: { mode: "default" } }),
  );
  await page.route("**/api/businesses/*", (route) =>
    route.request().method() === "GET"
      ? route.fulfill({ json: { name: "Ana Studio", timezone: "UTC", knowledge: [] } })
      : route.fulfill({ json: {} }),
  );
  await page.addInitScript(() => {
    window.localStorage.setItem("tovayo.session", JSON.stringify({ businessId: "b" }));
  });

  await page.goto("/settings");
  // Expand the service card; it offers a Group selector (the schedule lives on the group).
  await page.getByText("Haircut", { exact: true }).click();
  const group = page.getByLabel("Group (schedule)");
  await expect(group).toBeVisible();
  await expect(group).toHaveValue("g1"); // pre-selected to its group
  await expect(group.getByRole("option", { name: "Bob" })).toBeAttached(); // can move to another
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
    window.localStorage.setItem("tovayo.session", JSON.stringify({ businessId: "b" }));
  });

  await page.goto("/conversations");

  await expect(page.getByRole("heading", { name: "Conversations" })).toBeVisible();
  await expect(page.getByText("55501")).toBeVisible(); // the thread from the live feed
});

test("approving a pending action clears it from the inbox", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("tovayo.session", JSON.stringify({ businessId: "b" }));
  });
  // Mock the approvals API (now scoped per business): one pending request until approved.
  // Scope the glob to the API path so it doesn't also intercept the /approvals page nav.
  let approved = false;
  await page.route("**/api/businesses/**/approvals**", async (route) => {
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

test("the overview surfaces a 'Show all' footer with the count when the calendar is truncated", async ({
  page,
}) => {
  const many = Array.from({ length: 8 }, (_, i) => ({
    id: `ap${i}`,
    service: "Haircut",
    starts_at: `2026-06-29T1${i % 6}:00:00+00:00`,
    ends_at: `2026-06-29T1${i % 6}:30:00+00:00`,
    status: "confirmed",
  }));
  await page.route("**/api/businesses/*/appointments", (route) => route.fulfill({ json: many }));
  await page.route("**/api/businesses/*/conversations", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/businesses/*", (route) =>
    route.request().method() === "GET"
      ? route.fulfill({ json: { name: "Ana", timezone: "UTC" } })
      : route.fulfill({ json: {} }),
  );
  await page.addInitScript(() => {
    window.localStorage.setItem("tovayo.session", JSON.stringify({ businessId: "b" }));
  });

  await page.goto("/");

  const showAll = page.getByRole("link", { name: /Show all \(8\)/ });
  await expect(showAll).toBeVisible(); // the hidden 2 are now obvious via the count
  await expect(showAll).toHaveAttribute("href", "/calendar");
});
