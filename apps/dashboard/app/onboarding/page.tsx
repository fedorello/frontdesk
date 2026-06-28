"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/app/lib/api";
import { errorMessageKey } from "@/app/lib/errors";
import type { MessageKey } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { LanguageSwitcher } from "@/app/lib/LanguageSwitcher";
import { setSession } from "@/app/lib/session";
import { TIME_ZONE_OPTIONS } from "@/app/lib/timezones";
import { BrandHome } from "@/components/BrandHome";
import { StepIndicator } from "@/components/StepIndicator";

const STEPS: MessageKey[] = [
  "onboarding.step.account",
  "onboarding.step.business",
  "onboarding.step.ai",
  "onboarding.step.telegram",
];

const WEEKDAYS = [0, 1, 2, 3, 4]; // Mon–Fri

// Bringing your own LLM provider/key isn't launched yet — hide it until the flag is on.
// (The API also rejects "own" mode unless FRONTDESK_ALLOW_OWN_LLM is set.)
const ALLOW_OWN_LLM = process.env.NEXT_PUBLIC_ALLOW_OWN_LLM === "true";

export default function OnboardingPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 0 — account + business
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [timezone, setTimezone] = useState("UTC");

  // Step 1 — service
  const [serviceName, setServiceName] = useState("");
  const [duration, setDuration] = useState(60);

  // Step 2 — AI
  const [aiMode, setAiMode] = useState<"default" | "own">("default");
  const [provider, setProvider] = useState("openrouter");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");

  // Step 3 — Telegram
  const [botToken, setBotToken] = useState("");
  const [connectedAs, setConnectedAs] = useState<string | null>(null);

  // Session — the auth token lives in the HttpOnly cookie the API sets on signup.
  const [businessId, setBusinessId] = useState("");
  // The default group the API auto-creates on signup; the service goes into it.
  const [groupId, setGroupId] = useState("");

  async function guarded(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(t(errorMessageKey(caught)));
    } finally {
      setBusy(false);
    }
  }

  const submitAccount = () =>
    guarded(async () => {
      const result = await api.signup({
        email,
        password,
        business_name: businessName,
        timezone,
      });
      setBusinessId(result.business_id);
      setSession({ businessId: result.business_id, email: result.email });
      // Use the group the API created on signup, so the business has exactly one.
      const groups = await api.getGroups(result.business_id).catch(() => []);
      setGroupId(groups[0]?.id ?? "");
      setStep(1);
    });

  const submitService = () =>
    guarded(async () => {
      // Set the default group's schedule, then put the service into it.
      await api.putGroup(businessId, groupId, {
        name: "Main",
        working_hours: WEEKDAYS.map((weekday) => ({
          weekday,
          opens: "09:00:00",
          closes: "17:00:00",
        })),
      });
      await api.putService(businessId, "svc-1", {
        name: serviceName,
        duration_minutes: duration,
        resource_ids: [groupId],
      });
      setStep(2);
    });

  const submitAi = () =>
    guarded(async () => {
      // "own" is only possible when the feature is enabled; otherwise always the default.
      const useOwn = ALLOW_OWN_LLM && aiMode === "own";
      await api.putLlm(
        businessId,
        useOwn ? { mode: "own", provider, model, api_key: apiKey } : { mode: "default" },
      );
      setStep(3);
    });

  const submitTelegram = () =>
    guarded(async () => {
      const status = await api.connectTelegram(businessId, botToken);
      setConnectedAs(status.username ?? null);
    });

  // Telegram is optional — the owner can connect a bot later from Settings.
  const finish = () => router.push("/");

  return (
    <main className="min-h-screen bg-canvas px-6 py-10">
      <div className="mx-auto w-full max-w-lg">
        <div className="mb-6 flex items-center justify-between">
          <BrandHome />
          <LanguageSwitcher />
        </div>

        <div className="rounded-2xl border border-line bg-surface p-7 shadow-card">
          <h1 className="text-2xl font-extrabold tracking-tight">{t("onboarding.title")}</h1>

          <div className="mt-6">
            <StepIndicator labels={STEPS.map((key) => t(key))} current={step} />
          </div>

          {error && (
            <p role="alert" className="mt-4 rounded-lg bg-danger-soft p-3 text-sm text-danger">
              {error}
            </p>
          )}

          <div className="mt-6 space-y-4">
            {step === 0 && (
              <>
                <Field label={t("onboarding.email")} id="email">
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <Field label={t("onboarding.password")} id="password">
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <Field label={t("onboarding.businessName")} id="businessName">
                  <input
                    id="businessName"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <Field label={t("onboarding.timezone")} id="timezone">
                  <select
                    id="timezone"
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    className={inputClass}
                  >
                    {TIME_ZONE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <PrimaryButton onClick={submitAccount} busy={busy}>
                  {t("onboarding.signUp")}
                </PrimaryButton>
                <p className="text-center text-sm text-muted">
                  {t("auth.haveAccount")}{" "}
                  <Link href="/login" className="font-bold text-accent">
                    {t("onboarding.logIn")}
                  </Link>
                </p>
              </>
            )}

            {step === 1 && (
              <>
                <Field label={t("onboarding.serviceName")} id="serviceName">
                  <input
                    id="serviceName"
                    value={serviceName}
                    onChange={(e) => setServiceName(e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <Field label={t("onboarding.duration")} id="duration">
                  <input
                    id="duration"
                    type="number"
                    value={duration}
                    onChange={(e) => setDuration(Number(e.target.value))}
                    className={inputClass}
                  />
                </Field>
                <PrimaryButton onClick={submitService} busy={busy}>
                  {t("common.next")}
                </PrimaryButton>
              </>
            )}

            {step === 2 && (
              <>
                <p className="text-sm font-medium">{t("onboarding.chooseAi")}</p>
                {ALLOW_OWN_LLM ? (
                  <>
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="radio"
                        name="ai"
                        checked={aiMode === "default"}
                        onChange={() => setAiMode("default")}
                      />
                      {t("onboarding.defaultAi")}
                    </label>
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="radio"
                        name="ai"
                        checked={aiMode === "own"}
                        onChange={() => setAiMode("own")}
                      />
                      {t("onboarding.ownAi")}
                    </label>
                    {aiMode === "own" && (
                      <>
                        <Field label="Provider" id="provider">
                          <input
                            id="provider"
                            value={provider}
                            onChange={(e) => setProvider(e.target.value)}
                            className={inputClass}
                          />
                        </Field>
                        <Field label="Model" id="model">
                          <input
                            id="model"
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            className={inputClass}
                          />
                        </Field>
                        <Field label={t("onboarding.apiKey")} id="apiKey">
                          <input
                            id="apiKey"
                            type="password"
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            className={inputClass}
                          />
                        </Field>
                      </>
                    )}
                  </>
                ) : (
                  // Only the managed default for now; "own" is hidden until launched.
                  <p className="text-sm text-muted">{t("onboarding.defaultAiOnly")}</p>
                )}
                <PrimaryButton onClick={submitAi} busy={busy}>
                  {t("common.next")}
                </PrimaryButton>
              </>
            )}

            {step === 3 && (
              <>
                <p className="text-sm font-medium">{t("onboarding.connectTelegram")}</p>
                {connectedAs ? (
                  <>
                    <p
                      role="status"
                      className="rounded-lg bg-success-soft p-3 text-sm text-success"
                    >
                      {t("onboarding.connected", { username: connectedAs })}
                    </p>
                    <PrimaryButton onClick={finish} busy={false}>
                      {t("onboarding.goToDashboard")}
                    </PrimaryButton>
                  </>
                ) : (
                  <>
                    <Field label={t("onboarding.botToken")} id="botToken">
                      <input
                        id="botToken"
                        value={botToken}
                        onChange={(e) => setBotToken(e.target.value)}
                        className={inputClass}
                      />
                    </Field>
                    <PrimaryButton onClick={submitTelegram} busy={busy}>
                      {t("onboarding.connect")}
                    </PrimaryButton>
                    <button
                      type="button"
                      onClick={finish}
                      className="w-full text-center text-sm font-semibold text-muted hover:text-ink"
                    >
                      {t("onboarding.skip")}
                    </button>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

const inputClass =
  "w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent";

function Field({ label, id, children }: { label: string; id: string; children: React.ReactNode }) {
  return (
    <label htmlFor={id} className="block space-y-1">
      <span className="text-sm font-medium text-ink">{label}</span>
      {children}
    </label>
  );
}

function PrimaryButton({
  onClick,
  busy,
  children,
}: {
  onClick: () => void;
  busy: boolean;
  children: React.ReactNode;
}) {
  const { t } = useI18n();
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className="w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-bold text-accent-contrast disabled:opacity-50"
    >
      {busy ? t("common.saving") : children}
    </button>
  );
}
