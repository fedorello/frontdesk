"use client";

import { useEffect, useState } from "react";

import { api, type PremiumFeatureItem, type VoiceDemoNumber } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { EmptyState } from "@/components/ui/EmptyState";

const VOICE_KEY = "voice_receptionist";

export default function CallsPage() {
  const { t } = useI18n();
  const [businessId, setBusinessId] = useState<string | null>(null);
  const [numbers, setNumbers] = useState<VoiceDemoNumber[]>([]);
  const [voice, setVoice] = useState<PremiumFeatureItem | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const session = getSession();
    if (session === null) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setBusinessId(session.businessId);
    void api
      .voiceDemoNumbers(session.businessId)
      .then(setNumbers)
      .catch(() => {});
    void api
      .features(session.businessId)
      .then((items) => setVoice(items.find((feature) => feature.key === VOICE_KEY) ?? null))
      .catch(() => {});
  }, []);

  const request = async () => {
    if (businessId === null) return;
    setBusy(true);
    try {
      setVoice(await api.requestFeature(businessId, VOICE_KEY));
    } finally {
      setBusy(false);
    }
  };

  if (businessId === null)
    return (
      <main className="mx-auto w-full max-w-4xl px-6 py-8 sm:px-8">
        <EmptyState icon="calls" title={t("calendar.connectFirst")} />
      </main>
    );

  const status = voice?.status ?? null;

  return (
    <main className="mx-auto w-full max-w-4xl space-y-5 px-6 py-8 sm:px-8">
      <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
        <h2 className="font-bold">{t("calls.tryTitle")}</h2>
        <p className="mt-1 text-sm text-muted">{t("calls.tryHint")}</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {numbers.map((number) => (
            <a
              key={number.language}
              href={`tel:${number.e164}`}
              className="flex flex-col items-center rounded-xl border border-line bg-canvas px-4 py-3 text-center transition hover:bg-surface-3"
            >
              <span className="text-xs font-semibold text-muted">{number.label}</span>
              <span className="mt-1 font-bold">{number.e164}</span>
            </a>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
        <h2 className="font-bold">{t("calls.connectTitle")}</h2>
        {voice && (
          <p className="mt-1 text-sm text-muted">
            {voice.pricing} · {t("premium.comingSoon")}
          </p>
        )}
        <div className="mt-4">
          {status === "active" ? (
            <span className="rounded-full bg-success-soft px-3 py-1 text-sm font-semibold text-success">
              {t("premium.statusActive")}
            </span>
          ) : status === "requested" ? (
            <span className="rounded-full bg-warning-soft px-3 py-1 text-sm font-semibold text-warning">
              {t("premium.statusRequested")}
            </span>
          ) : (
            <button
              type="button"
              onClick={request}
              disabled={busy}
              className="rounded-lg bg-accent px-4 py-2.5 text-sm font-bold text-accent-contrast disabled:opacity-50"
            >
              {t("calls.request")}
            </button>
          )}
        </div>
      </section>
    </main>
  );
}
