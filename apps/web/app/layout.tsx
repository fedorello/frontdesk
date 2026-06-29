import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import { headers } from "next/headers";

import "./globals.css";
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

// Set the theme before paint so there's no flash. Reads the shared `tovayo.theme` cookie
// (set by the app too), else the OS preference. Cookie so the choice spans both sites.
const NO_FLASH = `(()=>{try{const t=(document.cookie.split("; ").find(r=>r.startsWith("tovayo.theme="))||"").split("=")[1];const d=t?t==="dark":matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.setAttribute("data-theme",d?"dark":"light");}catch(e){document.documentElement.setAttribute("data-theme","dark");}})();`;

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  return (
    <html
      lang="en"
      className={`${jakarta.variable} h-full`}
      suppressHydrationWarning
    >
      <head>
        <script nonce={nonce} dangerouslySetInnerHTML={{ __html: NO_FLASH }} />
      </head>
      <body className="min-h-full bg-canvas text-ink antialiased">
        {children}
      </body>
    </html>
  );
}
