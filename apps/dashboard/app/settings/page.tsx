"use client";

import { useEffect, useState } from "react";

import { api, type TelegramStatus } from "@/app/lib/api";
import { errorMessageKey } from "@/app/lib/errors";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";
import { TIME_ZONES } from "@/app/lib/timezones";
import { ServiceCard, type Service } from "@/components/ServiceCard";
import { EmptyState } from "@/components/ui/EmptyState";

const inputClass =
  "w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent ";

export default function SettingsPage() {
  const { t } = useI18n();
  const [session, setSession] = useState<{ token: string; businessId: string } | null>(null);
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");
  const [services, setServices] = useState<Service[]>([]);
  const [aiMode, setAiMode] = useState("default");
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [telegram, setTelegram] = useState<TelegramStatus | null>(null);
  const [botToken, setBotToken] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  useEffect(() => {
    const current = getSession();
    if (current === null) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSession(current);
    void (async () => {
      const [profile, list, llm, tg] = await Promise.all([
        api.getBusiness(current.businessId, current.token).catch(() => null),
        api.getServices(current.businessId, current.token).catch(() => []),
        api.getLlm(current.businessId, current.token).catch(() => ({ mode: "default" })),
        api.telegramStatus(current.businessId, current.token).catch(() => null),
      ]);
      if (profile) {
        setName(profile.name);
        setTimezone(profile.timezone);
        setDescription(profile.description ?? "");
        setAddress(profile.address ?? "");
      }
      setServices(list);
      setAiMode(llm.mode);
      setTelegram(tg);
    })();
  }, []);

  if (session === null) {
    return (
      <main className="mx-auto w-full max-w-4xl px-6 py-8 sm:px-8">
        <EmptyState icon="settings" title={t("calendar.connectFirst")} />
      </main>
    );
  }

  const saveProfile = async () => {
    setSaveError(null);
    try {
      await api.putBusiness(
        session.businessId,
        { name, timezone, description, address },
        session.token,
      );
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } catch (caught) {
      setSaveError(t(errorMessageKey(caught)));
    }
  };

  const saveService = async (service: Service) => {
    await api.putService(
      session.businessId,
      service.id,
      { ...service, resource_ids: ["main"] },
      session.token,
    );
    setServices((current) => current.map((s) => (s.id === service.id ? service : s)));
  };

  const addService = () => {
    const id = `svc-${crypto.randomUUID()}`;
    setServices([...services, { id, name: "", duration_minutes: 60, working_hours: [] }]);
  };

  const removeService = async (id: string) => {
    await api.deleteService(session.businessId, id, session.token);
    setServices((current) => current.filter((service) => service.id !== id));
  };

  const connectBot = async () => {
    setConnecting(true);
    setConnectError(null);
    try {
      setTelegram(await api.connectTelegram(session.businessId, botToken, session.token));
      setBotToken("");
    } catch (caught) {
      setConnectError(t(errorMessageKey(caught)));
    } finally {
      setConnecting(false);
    }
  };

  return (
    <main className="mx-auto w-full max-w-4xl space-y-5 px-6 py-8 sm:px-8">
      <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
        <h2 className="font-bold">{t("settings.profile")}</h2>
        <div className="mt-3 space-y-3">
          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("onboarding.businessName")}</span>
            <input
              aria-label={t("onboarding.businessName")}
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={inputClass}
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("onboarding.timezone")}</span>
            <select
              aria-label={t("onboarding.timezone")}
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
              className={inputClass}
            >
              {!TIME_ZONES.includes(timezone) && <option value={timezone}>{timezone}</option>}
              {TIME_ZONES.map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("settings.address")}</span>
            <input
              aria-label={t("settings.address")}
              value={address}
              onChange={(event) => setAddress(event.target.value)}
              placeholder={t("settings.addressHint")}
              className={inputClass}
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("settings.businessDescription")}</span>
            <textarea
              aria-label={t("settings.businessDescription")}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={4}
              placeholder={t("settings.businessDescriptionHint")}
              className={inputClass}
            />
            <span className="text-xs text-muted">{t("settings.businessDescriptionHint")}</span>
          </label>
          {saveError && (
            <p role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-danger">
              {saveError}
            </p>
          )}
          <button
            type="button"
            onClick={saveProfile}
            className="rounded-lg bg-accent px-4 py-2.5 text-sm font-bold text-accent-contrast"
          >
            {saved ? t("settings.saved") : t("settings.save")}
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
        <div className="flex items-center justify-between">
          <h2 className="font-bold">{t("settings.servicesTitle")}</h2>
          <button
            type="button"
            onClick={addService}
            className="rounded-lg bg-accent px-3 py-1.5 text-sm font-bold text-accent-contrast"
          >
            + {t("onboarding.addService")}
          </button>
        </div>
        <p className="mt-1 text-sm text-muted">{t("settings.servicesHint")}</p>
        <div className="mt-4 space-y-3">
          {services.length === 0 && (
            <p className="text-sm text-muted">{t("settings.noServices")}</p>
          )}
          {services.map((service) => (
            <ServiceCard
              key={service.id}
              service={service}
              onSave={saveService}
              onRemove={removeService}
              startOpen={service.name === ""}
            />
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
        <h2 className="font-bold">{t("settings.aiTitle")}</h2>
        <p className="mt-2 text-sm text-muted">
          {aiMode === "own" ? t("onboarding.ownAi") : t("onboarding.defaultAi")}
        </p>
      </section>

      <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
        <h2 className="font-bold">{t("onboarding.connectTelegram")}</h2>
        <p
          className={`mt-2 flex items-center gap-2 text-sm font-semibold ${
            telegram?.connected ? "text-success" : "text-muted"
          }`}
        >
          <span className="h-2 w-2 rounded-full bg-current" />
          {telegram?.connected
            ? t("onboarding.connected", { username: telegram.username ?? "" })
            : t("bot.offline")}
        </p>
        {connectError && (
          <p role="alert" className="mt-3 rounded-lg bg-danger-soft p-3 text-sm text-danger">
            {connectError}
          </p>
        )}
        <div className="mt-3 flex gap-2">
          <input
            aria-label={t("onboarding.botToken")}
            value={botToken}
            onChange={(event) => setBotToken(event.target.value)}
            placeholder={t("onboarding.botToken")}
            className={inputClass}
          />
          <button
            type="button"
            onClick={connectBot}
            disabled={connecting || botToken === ""}
            className="shrink-0 rounded-lg bg-accent px-4 py-2.5 text-sm font-bold text-accent-contrast disabled:opacity-50"
          >
            {connecting ? t("common.saving") : t("onboarding.connect")}
          </button>
        </div>
      </section>
    </main>
  );
}
