import type { Metadata } from "next";
import { Manrope } from "next/font/google";

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
  title: "tovayo",
  description: "The dashboard for your tovayo AI receptionist.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${jakarta.variable} h-full`} suppressHydrationWarning>
      <body className="min-h-full">
        <ThemeProvider>
          <I18nProvider>
            <AppShell>{children}</AppShell>
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
