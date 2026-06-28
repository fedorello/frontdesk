"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { readCookie, writeCookie } from "./cookie";

export type Theme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);
const THEME_COOKIE = "tovayo.theme";

function readStoredTheme(): Theme | null {
  const stored = readCookie(THEME_COOKIE);
  return stored === "light" || stored === "dark" ? stored : null;
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
      writeCookie(THEME_COOKIE, next); // shared with the marketing site
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
