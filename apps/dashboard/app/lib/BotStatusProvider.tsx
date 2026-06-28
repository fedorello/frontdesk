"use client";

import { usePathname } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { api, type TelegramStatus } from "@/app/lib/api";
import { readCache, writeCache } from "@/app/lib/cache";
import { getSession } from "@/app/lib/session";

interface BotStatusValue {
  status: TelegramStatus | null;
  refresh: () => Promise<void>;
  update: (status: TelegramStatus) => void;
}

const BotStatusContext = createContext<BotStatusValue>({
  status: null,
  refresh: async () => {},
  update: () => {},
});

// The single source of truth for the connected Telegram bot. The sidebar badge and the
// Settings panel both read it, so connecting a bot updates everywhere at once.
export function BotStatusProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<TelegramStatus | null>(null);
  const pathname = usePathname();

  const refresh = useCallback(async () => {
    const session = getSession();
    if (session === null) {
      setStatus(null);
      return;
    }
    try {
      const fresh = await api.telegramStatus(session.businessId);
      setStatus(fresh);
      writeCache(`botstatus.${session.businessId}`, fresh);
    } catch {
      // Keep showing the last-known status on a transient error — don't flash "offline".
    }
  }, []);

  useEffect(() => {
    const session = getSession();
    if (session !== null) {
      const cached = readCache<TelegramStatus>(`botstatus.${session.businessId}`);
      // eslint-disable-next-line react-hooks/set-state-in-effect -- paint last-known immediately
      if (cached) setStatus(cached);
    }
    void refresh();
  }, [refresh, pathname]);

  return (
    <BotStatusContext.Provider value={{ status, refresh, update: setStatus }}>
      {children}
    </BotStatusContext.Provider>
  );
}

export function useBotStatus(): BotStatusValue {
  return useContext(BotStatusContext);
}
