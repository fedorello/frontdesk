// A tiny localStorage cache for read data, so a page can show the last-known values
// immediately (stale) while it refetches fresh ones in the background — no empty flash.
// Keys are namespaced and scoped per business by the caller.

const PREFIX = "tovayo.cache.";

export function readCache<T>(key: string): T | null {
  try {
    const raw = window.localStorage?.getItem(PREFIX + key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function writeCache<T>(key: string, value: T): void {
  try {
    window.localStorage?.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // storage full or unavailable — the live fetch still populates the page
  }
}

// Drop every cached entry — call on logout / account delete so the next owner on this
// browser never sees the previous account's data.
export function clearCache(): void {
  try {
    const storage = window.localStorage;
    if (!storage) return;
    for (const key of Object.keys(storage)) {
      if (key.startsWith(PREFIX)) storage.removeItem(key);
    }
  } catch {
    // nothing to clear
  }
}
