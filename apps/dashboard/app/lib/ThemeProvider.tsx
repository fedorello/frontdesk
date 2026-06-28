"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Theme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = "tovayo.theme";

function readStoredTheme(): Theme | null {
  try {
    const stored = window.localStorage?.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : null;
  } catch {
    return null;
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  // SSR renders dark; the no-flash script in <head> has already set the real theme
  // (saved choice, else the OS) on <html> before paint — sync to it on mount.
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const attr = document.documentElement.getAttribute("data-theme");
    const initial = attr === "light" || attr === "dark" ? attr : (readStoredTheme() ?? "dark");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(initial);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const toggle = () => {
    setTheme((current) => {
      const next = current === "light" ? "dark" : "light";
      try {
        window.localStorage?.setItem(STORAGE_KEY, next);
      } catch {
        // storage unavailable — keep the in-memory choice
      }
      return next;
    });
  };

  return <ThemeContext.Provider value={{ theme, toggle }}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (context === null) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
