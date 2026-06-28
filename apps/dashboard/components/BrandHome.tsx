import { Logo } from "@/components/Logo";

// The marketing site. Overridable for self-hosters; defaults to the public landing.
const LANDING_URL = process.env.NEXT_PUBLIC_LANDING_URL ?? "https://tovayo.com";

// The Tovayo wordmark, linking back to the marketing site (used on the auth screens).
export function BrandHome() {
  return (
    <a
      href={LANDING_URL}
      aria-label="Tovayo"
      className="flex items-center gap-2 transition hover:opacity-80"
    >
      <Logo size={30} />
      <span className="text-lg font-extrabold tracking-tight">Tovayo</span>
    </a>
  );
}
