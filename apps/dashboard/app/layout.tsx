import type { Metadata } from "next";
import { Manrope } from "next/font/google";

import { BotStatusProvider } from "@/app/lib/BotStatusProvider";
import { I18nProvider } from "@/app/lib/I18nProvider";
import { ThemeProvider } from "@/app/lib/ThemeProvider";
import { AppShell } from "@/components/AppShell";
import "./globals.css";

// Manrope covers Latin AND Cyrillic in one geometric sans close to Plus Jakarta Sans,
// so the Russian UI matches the Latin one instead of falling back to a system font.
const jakarta = Manrope({
  variable: "--font-jakarta",
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Tovayo",
  description: "The dashboard for your tovayo AI receptionist.",
};

// Set the theme before paint so there's no flash: honor a saved choice, else the OS
// (defaulting to dark) — same behavior as the marketing site.
const NO_FLASH = `(()=>{try{const s=localStorage.getItem("tovayo.theme");const d=s?s==="dark":matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.setAttribute("data-theme",d?"dark":"light");}catch(e){document.documentElement.setAttribute("data-theme","dark");}})();`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${jakarta.variable} h-full`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: NO_FLASH }} />
      </head>
      <body className="min-h-full">
        <ThemeProvider>
          <I18nProvider>
            <BotStatusProvider>
              <AppShell>{children}</AppShell>
            </BotStatusProvider>
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
