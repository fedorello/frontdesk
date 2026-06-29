"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useI18n } from "@/app/lib/I18nProvider";
import { getSession, isAdmin } from "@/app/lib/session";
import { Icon } from "@/components/icons";
import { isActive, navItemsFor } from "@/components/nav-items";

/** Mobile navigation: a bottom bar that mirrors the sidebar (shown below `sm`). */
export function BottomNav() {
  const { t } = useI18n();
  const pathname = usePathname();
  const [admin, setAdmin] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAdmin(isAdmin(getSession()));
  }, [pathname]);

  return (
    <nav className="flex border-t border-line bg-surface px-1 py-1.5 sm:hidden">
      {navItemsFor(admin).map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`flex flex-1 flex-col items-center gap-1 rounded-lg py-1.5 text-[10px] font-semibold ${
              active ? "text-accent" : "text-faint"
            }`}
          >
            <Icon name={item.icon} size={20} />
            {t(item.key)}
          </Link>
        );
      })}
    </nav>
  );
}
