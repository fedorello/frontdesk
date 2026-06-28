"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { setSession } from "@/app/lib/session";

// The API's Google callback bounces here with ?token & ?business_id. Store the session
// and drop the owner into the dashboard (or back to login if something went wrong).
export default function AuthCallback() {
  const router = useRouter();
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const businessId = params.get("business_id");
    if (token && businessId) {
      setSession({
        token,
        businessId,
        name: params.get("name") ?? undefined,
        email: params.get("email") ?? undefined,
        avatar: params.get("avatar") ?? undefined,
      });
      router.replace("/");
    } else {
      router.replace("/login?error=google");
    }
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas">
      <span
        className="h-6 w-6 animate-spin rounded-full border-2 border-line border-t-accent"
        aria-label="Loading"
      />
    </main>
  );
}
