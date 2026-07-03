import Link from "next/link";

import type { Locale } from "@/app/lib/locales";
import { Logo } from "@/components/Logo";
import { Markdown } from "@/components/Markdown";

// Header/footer labels per language (the page body is already localized Markdown).
const LABELS: Record<Locale, { back: string; terms: string; privacy: string; tagline: string }> = {
  en: {
    back: "Back to home",
    terms: "Terms",
    privacy: "Privacy",
    tagline: "Tovayo — open-source AI front desk.",
  },
  ru: {
    back: "На главную",
    terms: "Условия",
    privacy: "Конфиденциальность",
    tagline: "Tovayo — ИИ-ресепшн с открытым кодом.",
  },
  es: {
    back: "Volver al inicio",
    terms: "Términos",
    privacy: "Privacidad",
    tagline: "Tovayo — recepción con IA de código abierto.",
  },
  zh: {
    back: "返回首页",
    terms: "条款",
    privacy: "隐私",
    tagline: "Tovayo——开源 AI 前台。",
  },
};

// A simple header + prose + footer wrapper for legal pages.
export function LegalShell({ content, locale }: { content: string; locale: Locale }) {
  const l = LABELS[locale];
  return (
    <div className="font-sans">
      <header className="sticky top-0 z-40 border-b border-line bg-surface/80 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-3xl items-center gap-3 px-5 py-3 sm:px-8">
          <Link href="/" className="flex items-center gap-2">
            <Logo size={32} />
            <span className="text-lg font-extrabold tracking-tight">
              Tovayo
            </span>
          </Link>
          <Link
            href="/"
            className="ml-auto flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M19 12H5M11 18l-6-6 6-6" />
            </svg>
            {l.back}
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl px-5 py-12 sm:px-8">
        <Markdown>{content}</Markdown>
      </main>
      <footer className="border-t border-line">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-4 px-5 py-7 text-sm font-semibold text-muted sm:px-8">
          <span>{l.tagline}</span>
          <div className="flex gap-4">
            <Link href="/terms" className="hover:text-ink">
              {l.terms}
            </Link>
            <Link href="/privacy" className="hover:text-ink">
              {l.privacy}
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
