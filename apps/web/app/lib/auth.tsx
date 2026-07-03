"use client";

import { createContext, useContext, useEffect, useState } from "react";

// The session cookie is host-only on the API, so the marketing site can't read it. Instead we ask
// the API (with credentials) whether this browser is signed in, and flip the CTAs to "Open app".
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://api.tovayo.com";

const AuthContext = createContext<boolean>(false);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authed, setAuthed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/me`, { credentials: "include", signal: controller.signal })
      .then((r) => {
        if (r.ok) setAuthed(true);
      })
      .catch(() => {}); // not signed in / offline — leave the default "Start free" CTAs
    return () => controller.abort();
  }, []);
  return <AuthContext.Provider value={authed}>{children}</AuthContext.Provider>;
}

export function useAuthed(): boolean {
  return useContext(AuthContext);
}
