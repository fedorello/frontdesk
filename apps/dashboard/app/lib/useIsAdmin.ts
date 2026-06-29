"use client";

import { useEffect, useState } from "react";

import { api } from "@/app/lib/api";
import { getSession, isAdmin } from "@/app/lib/session";

// Whether the signed-in account is an admin (ADR-0012). Reconciles against /api/me so it is
// correct regardless of how the session was created (email/password, Google, or an older
// session that predates the role field). The backend guard is the real gate; this is for the nav.
export function useIsAdmin(): boolean {
  const [admin, setAdmin] = useState(false);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- instant paint from the session
    setAdmin(isAdmin(getSession()));
    let alive = true;
    api
      .me()
      .then((me) => {
        if (alive) setAdmin(me.role === "admin");
      })
      .catch(() => {}); // signed out / not an admin — leave as not-admin
    return () => {
      alive = false;
    };
  }, []);
  return admin;
}
