"use client";

import { useState } from "react";

import { useI18n } from "@/app/lib/I18nProvider";

// Mirrors the backend minimum so the button stays disabled until the new password is long enough.
const MIN_PASSWORD_LENGTH = 8;

type Status = "idle" | "saving" | "saved" | "error";

const inputClass =
  "w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent";

export function PasswordChangeCard({
  onSubmit,
}: {
  onSubmit: (currentPassword: string, newPassword: string) => Promise<void>;
}) {
  const { t } = useI18n();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [status, setStatus] = useState<Status>("idle");

  const submit = async () => {
    setStatus("saving");
    try {
      await onSubmit(current, next);
      setCurrent("");
      setNext("");
      setStatus("saved");
    } catch {
      setStatus("error"); // wrong current password or a transient failure
    }
  };

  const canSubmit = current.length > 0 && next.length >= MIN_PASSWORD_LENGTH && status !== "saving";

  return (
    <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
      <h2 className="font-bold">{t("settings.passwordTitle")}</h2>
      <p className="mt-2 text-sm text-muted">{t("settings.passwordHint")}</p>
      <div className="mt-3 flex flex-col gap-2">
        <input
          type="password"
          aria-label={t("settings.currentPassword")}
          placeholder={t("settings.currentPassword")}
          autoComplete="current-password"
          value={current}
          onChange={(event) => setCurrent(event.target.value)}
          className={inputClass}
        />
        <input
          type="password"
          aria-label={t("settings.newPassword")}
          placeholder={t("settings.newPassword")}
          autoComplete="new-password"
          value={next}
          onChange={(event) => setNext(event.target.value)}
          className={inputClass}
        />
        {status === "error" && (
          <p role="alert" className="text-sm text-danger">
            {t("settings.passwordError")}
          </p>
        )}
        {status === "saved" && (
          <p className="text-sm text-success">{t("settings.passwordSaved")}</p>
        )}
        <button
          type="button"
          onClick={submit}
          disabled={!canSubmit}
          className="self-start rounded-lg bg-accent px-4 py-2.5 text-sm font-bold text-accent-contrast disabled:opacity-50"
        >
          {status === "saving" ? t("common.saving") : t("settings.passwordSubmit")}
        </button>
      </div>
    </section>
  );
}
