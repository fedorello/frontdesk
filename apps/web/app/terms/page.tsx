import type { Metadata } from "next";

import { TERMS } from "@/app/lib/legal/terms";
import { getLocale } from "@/app/lib/serverLocale";
import { LegalShell } from "@/components/LegalShell";

export const metadata: Metadata = { title: "Terms of Service — Tovayo" };

export default async function TermsPage() {
  const locale = await getLocale();
  return <LegalShell content={TERMS[locale]} locale={locale} />;
}
