import { describe, expect, it } from "vitest";

import { ADMIN_NAV_ITEM, isActive, navItemsFor, NAV_ITEMS } from "./nav-items";

describe("navItemsFor", () => {
  it("hides the admin entry for a non-admin", () => {
    const items = navItemsFor(false);
    expect(items).toEqual(NAV_ITEMS);
    expect(items).not.toContainEqual(ADMIN_NAV_ITEM);
  });

  it("appends the admin entry for an admin", () => {
    const items = navItemsFor(true);
    expect(items[items.length - 1]).toEqual(ADMIN_NAV_ITEM);
    expect(items).toHaveLength(NAV_ITEMS.length + 1);
  });
});

describe("isActive", () => {
  it("matches the root only exactly, and sub-routes by prefix", () => {
    expect(isActive("/", "/")).toBe(true);
    expect(isActive("/admin/businesses", "/")).toBe(false);
    expect(isActive("/admin/businesses", "/admin")).toBe(true);
  });
});
