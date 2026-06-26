"use client";

import { useState } from "react";

import { api, ApiError } from "@/app/lib/api";
import type { MessageKey } from "@/app/lib/i18n";
import { useI18n } from "@/app/lib/I18nProvider";
import { setSession } from "@/app/lib/session";

const STEPS: MessageKey[] = [
  "onboarding.step.account",
  "onboarding.step.business",
  "onboarding.step.ai",
  "onboarding.step.telegram",
];

const WEEKDAYS = [0, 1, 2, 3, 4]; // Mon–Fri

export default function OnboardingPage() {
  const { t } = useI18n();
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

  // Session
  const [token, setToken] = useState("");
  const [businessId, setBusinessId] = useState("");

  async function guarded(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("common.error"));
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
      setToken(result.token);
      setBusinessId(result.business_id);
      setSession({ token: result.token, businessId: result.business_id });
      setStep(1);
    });

  const submitService = () =>
    guarded(async () => {
      await api.putResource(
        businessId,
        "main",
        {
          name: "Main",
          working_hours: WEEKDAYS.map((weekday) => ({
            weekday,
            opens: "09:00:00",
            closes: "17:00:00",
          })),
        },
        token,
      );
      await api.putService(
        businessId,
        "svc-1",
        { name: serviceName, duration_minutes: duration, resource_ids: ["main"] },
        token,
      );
      setStep(2);
    });

  const submitAi = () =>
    guarded(async () => {
      await api.putLlm(
        businessId,
        aiMode === "own" ? { mode: "own", provider, model, api_key: apiKey } : { mode: "default" },
        token,
      );
      setStep(3);
    });

  const submitTelegram = () =>
    guarded(async () => {
      const status = await api.connectTelegram(businessId, botToken, token);
      setConnectedAs(status.username ?? null);
    });

  return (
    <main className="mx-auto w-full max-w-lg flex-1 px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">{t("onboarding.title")}</h1>

      <ol className="mt-6 flex gap-2 text-xs" aria-label="steps">
        {STEPS.map((key, index) => (
          <li
            key={key}
            data-active={index === step}
            className={
              index === step
                ? "rounded-full bg-zinc-900 px-3 py-1 text-white dark:bg-white dark:text-zinc-900"
                : "rounded-full bg-zinc-100 px-3 py-1 text-zinc-500 dark:bg-zinc-800"
            }
          >
            {t(key)}
          </li>
        ))}
      </ol>

      {error && (
        <p role="alert" className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
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
              <input
                id="timezone"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className={inputClass}
              />
            </Field>
            <PrimaryButton onClick={submitAccount} busy={busy}>
              {t("onboarding.signUp")}
            </PrimaryButton>
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
            <PrimaryButton onClick={submitAi} busy={busy}>
              {t("common.next")}
            </PrimaryButton>
          </>
        )}

        {step === 3 && (
          <>
            <p className="text-sm font-medium">{t("onboarding.connectTelegram")}</p>
            {connectedAs ? (
              <p role="status" className="rounded-md bg-green-50 p-3 text-sm text-green-700">
                {t("onboarding.connected", { username: connectedAs })}
              </p>
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
              </>
            )}
          </>
        )}
      </div>
    </main>
  );
}

const inputClass =
  "w-full rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm dark:border-zinc-700";

function Field({ label, id, children }: { label: string; id: string; children: React.ReactNode }) {
  return (
    <label htmlFor={id} className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
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
      className="w-full rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-zinc-900"
    >
      {busy ? t("common.saving") : children}
    </button>
  );
}
