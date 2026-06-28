"use client";

import { usePathname } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { api, type TelegramStatus } from "@/app/lib/api";
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
      setStatus(await api.telegramStatus(session.businessId, session.token));
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- refresh fetches; the no-session path clears synchronously
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
