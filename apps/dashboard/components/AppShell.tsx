"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { BottomNav } from "@/components/BottomNav";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";

// The onboarding wizard is a standalone full-screen flow — no dashboard chrome.
const BARE_ROUTES = ["/onboarding"];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (BARE_ROUTES.some((route) => pathname.startsWith(route))) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col bg-canvas">
        <Topbar />
        <div className="flex-1 overflow-auto">{children}</div>
        <BottomNav />
      </div>
    </div>
  );
}
