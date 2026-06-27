"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/app/lib/api";
import { errorMessageKey } from "@/app/lib/errors";
import { useI18n } from "@/app/lib/I18nProvider";
import { LanguageSwitcher } from "@/app/lib/LanguageSwitcher";
import { setSession } from "@/app/lib/session";
import { Logo } from "@/components/Logo";

const inputClass =
  "w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent";

export default function LoginPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await api.login({ email, password });
      setSession({ token: result.token, businessId: result.business_id });
      router.push("/");
    } catch (caught) {
      setError(t(errorMessageKey(caught)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-canvas px-6 py-10">
      <div className="mx-auto w-full max-w-sm">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Logo size={30} />
            <span className="text-lg font-extrabold tracking-tight">Tovayo</span>
          </div>
          <LanguageSwitcher />
        </div>

        <div className="rounded-2xl border border-line bg-surface p-7 shadow-card">
          <h1 className="text-2xl font-extrabold tracking-tight">{t("login.title")}</h1>

          {error && (
            <p role="alert" className="mt-4 rounded-lg bg-danger-soft p-3 text-sm text-danger">
              {error}
            </p>
          )}

          <div className="mt-6 space-y-4">
            <label htmlFor="email" className="block space-y-1">
              <span className="text-sm font-medium text-ink">{t("onboarding.email")}</span>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className={inputClass}
              />
            </label>
            <label htmlFor="password" className="block space-y-1">
              <span className="text-sm font-medium text-ink">{t("onboarding.password")}</span>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className={inputClass}
              />
            </label>
            <button
              type="button"
              onClick={submit}
              disabled={busy}
              className="w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-bold text-accent-contrast disabled:opacity-50"
            >
              {busy ? t("common.saving") : t("login.title")}
            </button>
          </div>
        </div>

        <p className="mt-5 text-center text-sm text-muted">
          {t("auth.needAccount")}{" "}
          <Link href="/onboarding" className="font-bold text-accent">
            {t("onboarding.signUp")}
          </Link>
        </p>
      </div>
    </main>
  );
}
