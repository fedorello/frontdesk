"use client";

import { usePathname } from "next/navigation";
import { Suspense, type ReactNode } from "react";

import { BottomNav } from "@/components/BottomNav";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";

// Auth screens are standalone full-screen flows — no dashboard chrome.
const BARE_ROUTES = ["/onboarding", "/login"];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (BARE_ROUTES.some((route) => pathname.startsWith(route))) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col bg-canvas">
        {/* Suspense isolates Topbar's useSearchParams so static pages still prerender. */}
        <Suspense fallback={<div className="h-[57px] shrink-0 border-b border-line bg-surface" />}>
          <Topbar />
        </Suspense>
        <div className="flex-1 overflow-auto">{children}</div>
        <BottomNav />
      </div>
    </div>
  );
}
