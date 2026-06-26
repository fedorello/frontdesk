import type { MessageKey } from "@/app/lib/i18n";
import type { IconName } from "@/components/icons";

/** The product navigation — shared by the sidebar, the mobile bottom-nav, and the topbar title. */
export const NAV_ITEMS: { href: string; key: MessageKey; icon: IconName }[] = [
  { href: "/", key: "nav.overview", icon: "overview" },
  { href: "/conversations", key: "nav.conversations", icon: "conversations" },
  { href: "/calendar", key: "nav.calendar", icon: "calendar" },
  { href: "/approvals", key: "nav.approvals", icon: "approvals" },
  { href: "/settings", key: "nav.settings", icon: "settings" },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}
