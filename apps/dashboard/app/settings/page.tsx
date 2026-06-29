"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, type BusinessProfile, type Group, type OwnerTelegram } from "@/app/lib/api";
import { clearCache, readCache, writeCache } from "@/app/lib/cache";
import { useBotStatus } from "@/app/lib/BotStatusProvider";
import { errorMessageKey } from "@/app/lib/errors";
import { useI18n } from "@/app/lib/I18nProvider";
import { MAX_BUSINESS_NAME, MAX_DESCRIPTION } from "@/app/lib/limits";
import { clearSession, getSession, type Session } from "@/app/lib/session";
import { TIME_ZONE_OPTIONS } from "@/app/lib/timezones";
import { AutoTextarea } from "@/components/AutoTextarea";
import { CharCount } from "@/components/CharCount";
import { ConfirmModal } from "@/components/ConfirmModal";
import { GroupCard } from "@/components/GroupCard";
import { OwnerNotificationsCard } from "@/components/OwnerNotificationsCard";
import { ServiceCard, type Service } from "@/components/ServiceCard";
import { ToggleSwitch } from "@/components/ToggleSwitch";
import { EmptyState } from "@/components/ui/EmptyState";

const inputClass =
  "w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent ";

export default function SettingsPage() {
  const { t, locale } = useI18n();
  const router = useRouter();
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const deleteAccount = async () => {
    const current = getSession();
    if (current === null) return;
    setDeleting(true);
    try {
      await api.deleteAccount(current.businessId);
      clearSession();
      clearCache();
      router.push("/login");
    } finally {
      setDeleting(false);
    }
  };
  const [session, setSession] = useState<Session | null>(null);
  const [name, setName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");
  const [online, setOnline] = useState(false);
  const [services, setServices] = useState<Service[]>([]);
  const [openServiceId, setOpenServiceId] = useState<string | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [openGroupId, setOpenGroupId] = useState<string | null>(null);
  const [groupError, setGroupError] = useState<string | null>(null);
  const [aiMode, setAiMode] = useState("default");
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const { status: telegram, update: setTelegram } = useBotStatus();
  const [botToken, setBotToken] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [ownerTelegram, setOwnerTelegram] = useState<OwnerTelegram | null>(null);

  const saveOwnerNotifications = async (enabled: boolean) => {
    const current = getSession();
    if (current === null) return;
    setOwnerTelegram(await api.setOwnerNotifications(current.businessId, enabled));
  };
  const unlinkOwnerTelegram = async () => {
    const current = getSession();
    if (current === null) return;
    setOwnerTelegram(await api.unlinkOwnerTelegram(current.businessId));
  };

  useEffect(() => {
    const current = getSession();
    if (current === null) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSession(current);
    const key = `settings.${current.businessId}`;
    const apply = (
      profile: BusinessProfile | null,
      list: Service[],
      aiMode: string,
      groupList: Group[],
      owner: OwnerTelegram | null,
    ) => {
      if (profile) {
        setName(profile.name);
        setOwnerName(profile.owner_name ?? "");
        setTimezone(profile.timezone);
        setDescription(profile.description ?? "");
        setAddress(profile.address ?? "");
        setOnline(profile.online ?? false);
      }
      setServices(list);
      setAiMode(aiMode);
      setGroups(groupList);
      if (owner) setOwnerTelegram(owner);
    };
    // Stale-while-revalidate: fill the form from the last-known values, then refetch.
    const cached = readCache<{
      profile: BusinessProfile | null;
      services: Service[];
      aiMode: string;
      groups: Group[];
      ownerTelegram: OwnerTelegram | null;
    }>(key);
    if (cached)
      apply(
        cached.profile,
        cached.services,
        cached.aiMode,
        cached.groups ?? [],
        cached.ownerTelegram ?? null,
      );
    void (async () => {
      const [profile, list, llm, groupList, owner] = await Promise.all([
        api.getBusiness(current.businessId).catch(() => null),
        api.getServices(current.businessId).catch(() => []),
        api.getLlm(current.businessId).catch(() => ({ mode: "default" })),
        api.getGroups(current.businessId).catch(() => []),
        api.getOwnerTelegram(current.businessId).catch(() => null),
      ]);
      apply(profile, list, llm.mode, groupList, owner);
      writeCache(key, {
        profile,
        services: list,
        aiMode: llm.mode,
        groups: groupList,
        ownerTelegram: owner,
      });
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
      await api.putBusiness(session.businessId, {
        name,
        owner_name: ownerName,
        timezone,
        description,
        address: online ? "" : address,
        online,
        locale,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } catch (caught) {
      setSaveError(t(errorMessageKey(caught)));
    }
  };

  const saveService = async (service: Service) => {
    // The service carries its chosen group in resource_ids (set by the card's group selector).
    await api.putService(session.businessId, service.id, service);
    setServices((current) => current.map((s) => (s.id === service.id ? service : s)));
  };

  const addService = () => {
    const id = `svc-${crypto.randomUUID()}`;
    // New services default to the first group; the owner can reassign in the card.
    const groupId = groups[0]?.id;
    setServices([
      ...services,
      { id, name: "", duration_minutes: 60, resource_ids: groupId ? [groupId] : [] },
    ]);
  };

  // Clone an existing service into a fresh, open card (pre-filled, name + "(copy)") so the
  // owner only tweaks what differs; it persists when they hit Save.
  const duplicateService = (service: Service) => {
    const copy: Service = {
      ...service,
      id: `svc-${crypto.randomUUID()}`,
      name: `${service.name} ${t("settings.copySuffix")}`.trim(),
    };
    setServices((current) => [...current, copy]);
    setOpenServiceId(copy.id);
  };

  const removeService = async (id: string) => {
    await api.deleteService(session.businessId, id);
    setServices((current) => current.filter((service) => service.id !== id));
  };

  const saveGroup = async (group: Group) => {
    await api.putGroup(session.businessId, group.id, {
      name: group.name,
      working_hours: group.working_hours,
    });
    setGroups((current) => current.map((g) => (g.id === group.id ? group : g)));
  };

  const addGroup = () => {
    const id = `grp-${crypto.randomUUID()}`;
    setGroups([...groups, { id, name: "", working_hours: [] }]);
    setOpenGroupId(id);
  };

  const removeGroup = async (id: string) => {
    setGroupError(null);
    try {
      await api.deleteGroup(session.businessId, id);
      setGroups((current) => current.filter((group) => group.id !== id));
    } catch (caught) {
      // The API rejects deleting a group that still has services (409) — surface it.
      setGroupError(t(errorMessageKey(caught)));
    }
  };

  const connectBot = async () => {
    setConnecting(true);
    setConnectError(null);
    try {
      setTelegram(await api.connectTelegram(session.businessId, botToken));
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
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{t("onboarding.businessName")}</span>
              <CharCount value={name} max={MAX_BUSINESS_NAME} />
            </div>
            <input
              aria-label={t("onboarding.businessName")}
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={inputClass}
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("settings.ownerName")}</span>
            <input
              aria-label={t("settings.ownerName")}
              value={ownerName}
              onChange={(event) => setOwnerName(event.target.value)}
              placeholder={t("settings.ownerNamePlaceholder")}
              className={inputClass}
            />
            <span className="text-xs text-muted">{t("settings.ownerNameHint")}</span>
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("onboarding.timezone")}</span>
            <select
              aria-label={t("onboarding.timezone")}
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
              className={inputClass}
            >
              {!TIME_ZONE_OPTIONS.some((option) => option.value === timezone) && (
                <option value={timezone}>{timezone}</option>
              )}
              {TIME_ZONE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{t("settings.address")}</span>
              <label className="flex items-center gap-2 text-sm text-muted">
                {t("settings.online")}
                <ToggleSwitch checked={online} onChange={setOnline} label={t("settings.online")} />
              </label>
            </div>
            {online ? (
              <p className="rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-muted">
                {t("settings.onlineHint")}
              </p>
            ) : (
              <input
                aria-label={t("settings.address")}
                value={address}
                onChange={(event) => setAddress(event.target.value)}
                placeholder={t("settings.addressHint")}
                className={inputClass}
              />
            )}
          </div>
          <label className="block space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{t("settings.businessDescription")}</span>
              <CharCount value={description} max={MAX_DESCRIPTION} />
            </div>
            <AutoTextarea
              ariaLabel={t("settings.businessDescription")}
              value={description}
              onChange={setDescription}
              minRows={3}
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
            disabled={
              name.length === 0 ||
              name.length > MAX_BUSINESS_NAME ||
              description.length > MAX_DESCRIPTION
            }
            className="rounded-lg bg-accent px-4 py-2.5 text-sm font-bold text-accent-contrast disabled:opacity-50"
          >
            {saved ? t("settings.saved") : t("settings.save")}
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
        <div className="flex items-center justify-between">
          <h2 className="font-bold">{t("settings.groupsTitle")}</h2>
          <button
            type="button"
            onClick={addGroup}
            className="rounded-lg bg-accent px-3 py-1.5 text-sm font-bold text-accent-contrast"
          >
            + {t("settings.addGroup")}
          </button>
        </div>
        <p className="mt-1 text-sm text-muted">{t("settings.groupsHint")}</p>
        {groupError && (
          <p role="alert" className="mt-3 rounded-lg bg-danger-soft p-2.5 text-sm text-danger">
            {groupError}
          </p>
        )}
        <div className="mt-4 space-y-3">
          {groups.length === 0 && <p className="text-sm text-muted">{t("settings.noGroups")}</p>}
          {groups.map((group) => (
            <GroupCard
              key={group.id}
              group={group}
              onSave={saveGroup}
              onRemove={removeGroup}
              startOpen={group.name === "" || group.id === openGroupId}
            />
          ))}
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
              groups={groups}
              onSave={saveService}
              onRemove={removeService}
              onDuplicate={duplicateService}
              startOpen={service.name === "" || service.id === openServiceId}
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

      {ownerTelegram && (
        <div className="mt-8">
          <OwnerNotificationsCard
            status={ownerTelegram}
            onToggle={saveOwnerNotifications}
            onUnlink={unlinkOwnerTelegram}
          />
        </div>
      )}

      <section className="mt-8 rounded-2xl border border-danger/40 bg-danger-soft/30 p-5">
        <h2 className="text-base font-bold text-danger">{t("settings.dangerZone")}</h2>
        <p className="mt-1 text-sm text-muted">{t("settings.deleteAccountHint")}</p>
        <button
          type="button"
          onClick={() => setConfirmingDelete(true)}
          className="mt-3 rounded-lg border border-danger px-4 py-2 text-sm font-bold text-danger hover:bg-danger-soft"
        >
          {t("settings.deleteAccount")}
        </button>
      </section>

      {confirmingDelete && (
        <ConfirmModal
          title={t("settings.deleteTitle")}
          body={t("settings.deleteBody")}
          confirmLabel={t("settings.deleteConfirm")}
          cancelLabel={t("common.cancel")}
          danger
          busy={deleting}
          onConfirm={deleteAccount}
          onClose={() => setConfirmingDelete(false)}
        />
      )}
    </main>
  );
}
