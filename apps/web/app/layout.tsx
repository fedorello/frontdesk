import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import { cookies, headers } from "next/headers";

import "./globals.css";
import { I18nProvider, LOCALES, type Locale } from "./lib/i18n";
import { SITE_DESCRIPTION, SITE_TITLE, SITE_URL } from "./lib/site";

// Manrope covers Latin AND Cyrillic in one geometric sans close to Plus Jakarta Sans,
// so en/es/ru/zh all render in the same typeface (no system fallback for Cyrillic).
const jakarta = Manrope({
  variable: "--font-jakarta",
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: SITE_TITLE,
  description: SITE_DESCRIPTION,
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: "Tovayo",
    url: SITE_URL,
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
  },
};

// Fallback for the first visit only (no theme cookie yet): pick the OS preference before paint,
// so there's no flash. When the cookie IS set, the server already rendered `data-theme` on <html>
// (below), so this leaves it untouched. Cookie so the choice spans tovayo.com + app.tovayo.com.
const NO_FLASH = `(()=>{try{if(document.documentElement.getAttribute("data-theme"))return;const d=matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.setAttribute("data-theme",d?"dark":"light");}catch(e){document.documentElement.setAttribute("data-theme","dark");}})();`;

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [nonce, cookieStore] = await Promise.all([
    headers().then((h) => h.get("x-nonce") ?? undefined),
    cookies(),
  ]);
  // Read the shared preferences server-side so theme + language are correct in the very first HTML
  // on EVERY page (including the static legal pages) — no client flash, no page-to-page reset.
  const rawTheme = cookieStore.get("tovayo.theme")?.value;
  const theme = rawTheme === "dark" || rawTheme === "light" ? rawTheme : undefined;
  const rawLocale = cookieStore.get("tovayo.locale")?.value;
  const locale = (LOCALES as readonly string[]).includes(rawLocale ?? "")
    ? (rawLocale as Locale)
    : undefined;
  return (
    <html
      lang={locale ?? "en"}
      data-theme={theme}
      className={`${jakarta.variable} h-full`}
      suppressHydrationWarning
    >
      <head>
        <script nonce={nonce} dangerouslySetInnerHTML={{ __html: NO_FLASH }} />
      </head>
      <body className="min-h-full bg-canvas text-ink antialiased">
        <I18nProvider initialLocale={locale}>{children}</I18nProvider>
      </body>
    </html>
  );
}
