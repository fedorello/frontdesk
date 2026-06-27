import Link from "next/link";

import { Markdown } from "@/components/Markdown";

// A simple header + prose + footer wrapper for legal pages.
export function LegalShell({ content }: { content: string }) {
  return (
    <div className="font-sans">
      <header className="sticky top-0 z-40 border-b border-line bg-surface/80 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-3xl items-center gap-3 px-5 py-3 sm:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-[9px] bg-accent text-base font-extrabold text-accent-contrast">
              T
            </span>
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
            Back to home
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl px-5 py-12 sm:px-8">
        <Markdown>{content}</Markdown>
      </main>
      <footer className="border-t border-line">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-4 px-5 py-7 text-sm font-semibold text-muted sm:px-8">
          <span>Tovayo — open-source AI front desk.</span>
          <div className="flex gap-4">
            <Link href="/terms" className="hover:text-ink">
              Terms
            </Link>
            <Link href="/privacy" className="hover:text-ink">
              Privacy
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
