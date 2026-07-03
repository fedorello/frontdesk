import type { Metadata } from "next";

import { PRIVACY } from "@/app/lib/legal/privacy";
import { getLocale } from "@/app/lib/serverLocale";
import { LegalShell } from "@/components/LegalShell";

export const metadata: Metadata = { title: "Privacy Policy — Tovayo" };

export default async function PrivacyPage() {
  const locale = await getLocale();
  return <LegalShell content={PRIVACY[locale]} locale={locale} />;
}
