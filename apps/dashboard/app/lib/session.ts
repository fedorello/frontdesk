// The owner's session (token + business id), persisted client-side. SSR-safe.

const KEY = "tovayo.session";

export interface Session {
  token: string;
  businessId: string;
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
