import { LANDING_URL } from "@/app/lib/links";
import { Logo } from "@/components/Logo";

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
