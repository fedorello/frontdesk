"use client";

import { useEffect, useState } from "react";

import { api, type PremiumFeatureItem } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";

const STATUS_TONE = {
  requested: "bg-warning-soft text-warning",
  active: "bg-success-soft text-success",
} as const;

/**
 * Owner view of the premium-feature catalog: each feature with its price, plus a Request-access
 * button (self-serve) or a status chip once requested/active. Billing is not live yet, so the price
 * is labelled "coming soon". Renders nothing when the catalog is empty.
 */
export function PremiumFeaturesCard({ businessId }: { businessId: string }) {
  const { t } = useI18n();
  const [features, setFeatures] = useState<PremiumFeatureItem[]>([]);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  useEffect(() => {
    void api
      .features(businessId)
      .then(setFeatures)
      .catch(() => {});
  }, [businessId]);

  const request = async (key: string) => {
    setBusyKey(key);
    try {
      const updated = await api.requestFeature(businessId, key);
      setFeatures((current) => current.map((feature) => (feature.key === key ? updated : feature)));
    } finally {
      setBusyKey(null);
    }
  };

  if (features.length === 0) return null;

  return (
    <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
      <h2 className="font-bold">{t("settings.premiumTitle")}</h2>
      <p className="mt-1 text-sm text-muted">{t("premium.subtitle")}</p>
      <div className="mt-4 space-y-3">
        {features.map((feature) => (
          <div
            key={feature.key}
            className="flex items-start justify-between gap-4 rounded-xl border border-line bg-canvas p-4"
          >
            <div className="min-w-0">
              <p className="font-semibold">{feature.name}</p>
              <p className="mt-0.5 text-sm text-muted">{feature.description}</p>
              <p className="mt-1 text-xs text-muted">
                {feature.pricing} · {t("premium.comingSoon")}
              </p>
            </div>
            <div className="shrink-0">
              {feature.status === "requested" || feature.status === "active" ? (
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_TONE[feature.status]}`}
                >
                  {t(
                    feature.status === "active"
                      ? "premium.statusActive"
                      : "premium.statusRequested",
                  )}
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => request(feature.key)}
                  disabled={busyKey === feature.key}
                  className="rounded-lg bg-accent px-3 py-1.5 text-sm font-bold text-accent-contrast disabled:opacity-50"
                >
                  {t("premium.requestAccess")}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
