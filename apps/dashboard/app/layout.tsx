import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { Nav } from "@/components/Nav";
import { I18nProvider } from "@/app/lib/I18nProvider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
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
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <I18nProvider>
          <Nav />
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}
