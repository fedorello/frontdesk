import type { Metadata } from "next";
import { Manrope } from "next/font/google";

import "./globals.css";

// Manrope covers Latin AND Cyrillic in one geometric sans close to Plus Jakarta Sans,
// so en/es/ru/zh all render in the same typeface (no system fallback for Cyrillic).
const jakarta = Manrope({
  variable: "--font-jakarta",
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Tovayo — a free AI front desk for your small business",
  description:
    "Tovayo answers customers, books appointments, and sends reminders — 24/7, in their language. Free and open source, or hosted for you. Both free.",
};

// Set the theme before paint so there's no flash. Reads the shared `tovayo.theme` cookie
// (set by the app too), else the OS preference. Cookie so the choice spans both sites.
const NO_FLASH = `(()=>{try{const t=(document.cookie.split("; ").find(r=>r.startsWith("tovayo.theme="))||"").split("=")[1];const d=t?t==="dark":matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.setAttribute("data-theme",d?"dark":"light");}catch(e){document.documentElement.setAttribute("data-theme","dark");}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${jakarta.variable} h-full`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: NO_FLASH }} />
      </head>
      <body className="min-h-full bg-canvas text-ink antialiased">
        {children}
      </body>
    </html>
  );
}
