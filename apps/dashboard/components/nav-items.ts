import type { MessageKey } from "@/app/lib/i18n";
import type { IconName } from "@/components/icons";

export interface NavItem {
  href: string;
  key: MessageKey;
  icon: IconName;
}

/** The product navigation — shared by the sidebar, the mobile bottom-nav, and the topbar title. */
export const NAV_ITEMS: NavItem[] = [
  { href: "/", key: "nav.overview", icon: "overview" },
  { href: "/conversations", key: "nav.conversations", icon: "conversations" },
  { href: "/calendar", key: "nav.calendar", icon: "calendar" },
  { href: "/calls", key: "nav.calls", icon: "calls" },
  { href: "/approvals", key: "nav.approvals", icon: "approvals" },
  { href: "/settings", key: "nav.settings", icon: "settings" },
];

/** Admin-only entry (ADR-0012), appended to the nav for admin accounts. */
export const ADMIN_NAV_ITEM: NavItem = { href: "/admin", key: "nav.admin", icon: "admin" };

/** The nav for an account: the product items, plus the admin entry for admins. */
export function navItemsFor(admin: boolean): NavItem[] {
  return admin ? [...NAV_ITEMS, ADMIN_NAV_ITEM] : NAV_ITEMS;
}

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}
