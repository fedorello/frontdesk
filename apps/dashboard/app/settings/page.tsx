"use client";

import { useEffect, useState } from "react";

import { api, type ServiceInput } from "@/app/lib/api";
import { useI18n } from "@/app/lib/I18nProvider";
import { getSession } from "@/app/lib/session";

type Service = ServiceInput & { id: string };

const inputClass =
  "w-full rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm dark:border-zinc-700";

export default function SettingsPage() {
  const { t } = useI18n();
  const [session, setSession] = useState<{ token: string; businessId: string } | null>(null);
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [services, setServices] = useState<Service[]>([]);
  const [aiMode, setAiMode] = useState("default");
  const [newService, setNewService] = useState("");
  const [newDuration, setNewDuration] = useState(60);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const current = getSession();
    if (current === null) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSession(current);
    void (async () => {
      const [profile, list, llm] = await Promise.all([
        api.getBusiness(current.businessId, current.token).catch(() => null),
        api.getServices(current.businessId, current.token).catch(() => []),
        api.getLlm(current.businessId, current.token).catch(() => ({ mode: "default" })),
      ]);
      if (profile) {
        setName(profile.name);
        setTimezone(profile.timezone);
      }
      setServices(list);
      setAiMode(llm.mode);
    })();
  }, []);

  if (session === null) {
    return (
      <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
        <h1 className="text-2xl font-semibold tracking-tight">{t("nav.settings")}</h1>
        <p className="mt-4 text-sm text-zinc-500">{t("calendar.connectFirst")}</p>
      </main>
    );
  }

  const saveProfile = async () => {
    await api.putBusiness(session.businessId, { name, timezone }, session.token);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  const addService = async () => {
    const id = `svc-${services.length + 1}-${newService.toLowerCase().replace(/\s+/g, "-")}`;
    await api.putService(
      session.businessId,
      id,
      { name: newService, duration_minutes: newDuration, resource_ids: ["main"] },
      session.token,
    );
    setServices([...services, { id, name: newService, duration_minutes: newDuration }]);
    setNewService("");
  };

  const removeService = async (id: string) => {
    await api.deleteService(session.businessId, id, session.token);
    setServices(services.filter((service) => service.id !== id));
  };

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">{t("nav.settings")}</h1>

      <section className="mt-8 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
        <h2 className="font-medium">{t("settings.profile")}</h2>
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
            <input
              aria-label={t("onboarding.timezone")}
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
              className={inputClass}
            />
          </label>
          <button
            type="button"
            onClick={saveProfile}
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-zinc-900"
          >
            {saved ? t("settings.saved") : t("settings.save")}
          </button>
        </div>
      </section>

      <section className="mt-6 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
        <h2 className="font-medium">{t("settings.servicesTitle")}</h2>
        <ul className="mt-3 space-y-2">
          {services.map((service) => (
            <li key={service.id} className="flex items-center justify-between text-sm">
              <span>
                {service.name} · {service.duration_minutes} min
              </span>
              <button
                type="button"
                onClick={() => removeService(service.id)}
                className="text-xs text-red-600 hover:underline"
              >
                {t("settings.remove")}
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-4 flex gap-2">
          <input
            aria-label={t("onboarding.serviceName")}
            value={newService}
            onChange={(event) => setNewService(event.target.value)}
            placeholder={t("onboarding.serviceName")}
            className={inputClass}
          />
          <input
            aria-label={t("onboarding.duration")}
            type="number"
            value={newDuration}
            onChange={(event) => setNewDuration(Number(event.target.value))}
            className="w-24 rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
          />
          <button
            type="button"
            onClick={addService}
            disabled={newService === ""}
            className="shrink-0 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium disabled:opacity-50 dark:border-zinc-700"
          >
            {t("onboarding.addService")}
          </button>
        </div>
      </section>

      <section className="mt-6 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
        <h2 className="font-medium">{t("settings.aiTitle")}</h2>
        <p className="mt-2 text-sm text-zinc-500">
          {aiMode === "own" ? t("onboarding.ownAi") : t("onboarding.defaultAi")}
        </p>
      </section>
    </main>
  );
}
