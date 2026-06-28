"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, API_URL } from "@/app/lib/api";
import { errorMessageKey } from "@/app/lib/errors";
import { useI18n } from "@/app/lib/I18nProvider";
import { LanguageSwitcher } from "@/app/lib/LanguageSwitcher";
import { setSession } from "@/app/lib/session";
import { Logo } from "@/components/Logo";

const inputClass =
  "w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent";

const GoogleG = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
    <path
      fill="#EA4335"
      d="M12 5.04c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 1.7 14.97.6 12 .6 7.7.6 3.99 3.07 2.18 6.71l3.66 2.84C6.71 6.86 9.14 5.04 12 5.04z"
    />
    <path
      fill="#4285F4"
      d="M23.49 12.27c0-.79-.07-1.54-.19-2.27H12v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58l3.68 2.84c2.15-1.98 3.39-4.9 3.39-8.66z"
    />
    <path
      fill="#FBBC05"
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09L2.18 7.07C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
    />
    <path
      fill="#34A853"
      d="M12 23.4c2.97 0 5.46-.98 7.28-2.66l-3.68-2.84c-1.02.69-2.33 1.09-3.6 1.09-2.86 0-5.29-1.93-6.16-4.53L2.18 17.3C3.99 20.94 7.7 23.4 12 23.4z"
    />
  </svg>
);

export default function LoginPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // The Google callback bounces back here with ?error=google when sign-in didn't complete.
    if (new URLSearchParams(window.location.search).get("error") === "google") {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot read of the URL on mount
      setError(t("login.googleError"));
    }
  }, [t]);

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

          <div className="my-5 flex items-center gap-3 text-xs font-medium text-faint">
            <span className="h-px flex-1 bg-line" />
            {t("login.or")}
            <span className="h-px flex-1 bg-line" />
          </div>

          <a
            href={`${API_URL}/api/auth/google/start`}
            className="flex w-full items-center justify-center gap-2.5 rounded-lg border border-line-strong bg-surface px-4 py-2.5 text-sm font-bold text-ink transition hover:bg-surface-3"
          >
            <GoogleG />
            {t("login.google")}
          </a>
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
