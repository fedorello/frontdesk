// The owner's session context, persisted client-side. SSR-safe.
//
// NOTE: the auth token is NOT here — it lives only in the HttpOnly `tovayo.session` cookie,
// which JavaScript cannot read. This holds only the non-secret business id + display identity
// the UI needs to build request paths and render the topbar.

const KEY = "tovayo.session";

export interface Session {
  businessId: string;
  // Owner identity for the topbar avatar. From Google on social sign-in; email-only otherwise.
  email?: string;
  name?: string;
  avatar?: string;
  // The account role; "admin" unlocks the platform analytics nav (ADR-0012). The backend
  // guard is the real gate — this only decides whether to show the Admin link.
  role?: string;
}

export function isAdmin(session: Session | null): boolean {
  return session?.role === "admin";
}

export function getSession(): Session | null {
  try {
    const raw = window.localStorage?.getItem(KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function setSession(session: Session): void {
  try {
    window.localStorage?.setItem(KEY, JSON.stringify(session));
  } catch {
    // storage unavailable — the in-memory flow still works for this page load
  }
}

export function clearSession(): void {
  try {
    window.localStorage?.removeItem(KEY);
  } catch {
    // nothing to clear
  }
}
