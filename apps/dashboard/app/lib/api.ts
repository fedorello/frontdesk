// Typed client for the tovayo API (M5). One place that knows the endpoints and
// shapes, reused by every screen regardless of how it looks.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface AuthResult {
  business_id: string;
  email: string;
  role: string;
}

export interface MeResult {
  email: string;
  business_id: string | null;
  role: string;
}

// Platform analytics (admin only, ADR-0012) — aggregate counts, never customer PII.
export interface SignupCounts {
  today: number;
  last_7_days: number;
  last_30_days: number;
}

export interface AppointmentStatusCounts {
  pending: number;
  confirmed: number;
  completed: number;
  cancelled: number;
  no_show: number;
  total: number;
}

export interface PlatformTotals {
  total_businesses: number;
  signups: SignupCounts;
  active_businesses_30d: number;
  total_customers: number;
  total_agent_replies: number;
  appointments: AppointmentStatusCounts;
  telegram_bots_connected: number;
  owner_telegram_links: number;
  llm_modes: { default: number; own: number };
  pending_approvals: number;
}

export interface ActivationFunnel {
  signed_up: number;
  connected_channel: number;
  received_message: number;
  booked_appointment: number;
}

export interface AdminOverview {
  totals: PlatformTotals;
  funnel: ActivationFunnel;
  funnel_conversion: {
    connected_pct: number;
    received_message_pct: number;
    booked_pct: number;
  };
  no_show_rate: number;
  cancellation_rate: number;
}

export type TimeseriesMetric = "signups" | "bookings" | "replies" | "new_customers" | "llm_usage";

export interface DailyCount {
  day: string; // ISO date "YYYY-MM-DD"
  count: number;
}

export type DirectorySort =
  | "name"
  | "signup_date"
  | "appointments"
  | "customers"
  | "replies"
  | "last_activity";

export interface BusinessSummary {
  business_id: string;
  name: string;
  locale: string;
  timezone: string;
  created_at: string;
  service_count: number;
  customer_count: number;
  appointments: AppointmentStatusCounts;
  agent_reply_count: number;
  last_activity_at: string | null;
  bot_connected: boolean;
  uses_own_llm: boolean;
  owner_telegram_linked: boolean;
}

export interface BusinessPage {
  items: BusinessSummary[];
  total: number;
}

export interface BusinessDirectoryQuery {
  limit: number;
  offset: number;
  sort: DirectorySort;
  descending: boolean;
  q?: string;
}

export interface WorkingHours {
  weekday: number; // Monday = 0
  opens: string; // "HH:MM:SS"
  closes: string;
}

export interface IntakeField {
  name: string;
  description?: string;
  ask?: string;
  normalize?: string;
}

export interface IntakeAnswer {
  name: string;
  value: string;
}

export interface BusinessProfile {
  name: string;
  timezone: string;
  lead_time_minutes?: number;
  buffer_minutes?: number;
  knowledge?: { question: string; answer: string }[];
  description?: string;
  address?: string;
  online?: boolean;
  locale?: string;
  owner_name?: string;
}

export interface ServiceInput {
  name: string;
  duration_minutes: number;
  price_cents?: number | null;
  currency?: string | null;
  resource_ids?: string[]; // the single group this service belongs to
  description?: string;
  max_advance_days?: number;
  intake_fields?: IntakeField[];
  requires_confirmation?: boolean;
}

// A service group: one specialist/calendar with a shared weekly schedule.
export interface Group {
  id: string;
  name: string;
  working_hours: WorkingHours[];
}

export interface LlmConfigInput {
  mode: "default" | "own";
  provider?: string;
  model?: string;
  api_key?: string;
}

export interface TelegramStatus {
  connected: boolean;
  username?: string | null;
}

export interface OwnerTelegram {
  linked: boolean;
  telegram_name: string | null;
  notifications_enabled: boolean;
}

export interface AppointmentView {
  id: string;
  service: string;
  starts_at: string;
  ends_at: string;
  status: string;
  intake?: IntakeAnswer[];
}

export interface AppointmentPage {
  items: AppointmentView[];
  total: number; // matching appointments across all pages, for the page count
}

export interface AppointmentQuery {
  limit: number;
  offset: number;
  includeCancelled?: boolean;
  q?: string;
}

export interface AppointmentResult {
  id: string;
  status: string;
  starts_at: string;
  ends_at: string;
}

export interface MessageView {
  customer: string;
  customer_id: string;
  customer_name?: string | null;
  role: string;
  text: string;
  at: string;
  handled: boolean;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method,
    // Send the HttpOnly session cookie cross-subdomain (app.tovayo.com → api.tovayo.com).
    credentials: "include",
    headers: { "content-type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readDetail(response));
  }
  return (await response.json()) as T;
}

// FastAPI errors come as {"detail": "..."}; surface the plain detail, never raw JSON.
async function readDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (
      body &&
      typeof body === "object" &&
      typeof (body as { detail?: unknown }).detail === "string"
    ) {
      return (body as { detail: string }).detail;
    }
  } catch {
    // not JSON — fall through to a generic message
  }
  return response.statusText;
}

// A premium feature in the catalog, with this business's status (null = never requested).
export interface PremiumFeatureItem {
  key: string;
  name: string;
  description: string;
  pricing: string;
  status: "requested" | "active" | "suspended" | null;
}

// A demo phone number to try the voice assistant, per language.
export interface VoiceDemoNumber {
  language: string;
  e164: string;
  label: string;
}

// One thing the assistant has remembered about a customer.
export interface CustomerFact {
  key: string;
  value: string;
}

// One business's entitlement, as the operator sees it (ADR-0013).
export interface AdminEntitlement {
  business_id: string;
  feature_key: string;
  status: "requested" | "active" | "suspended";
  requested_at: string;
  decided_at: string | null;
}

// Auth rides the HttpOnly session cookie (set by the API on login/signup/OAuth), so no
// method takes a token — the browser attaches the cookie automatically (credentials: include).
export const api = {
  signup: (body: {
    email: string;
    password: string;
    business_name: string;
    timezone?: string;
  }): Promise<AuthResult> => request("POST", "/api/signup", body),

  login: (body: { email: string; password: string }): Promise<AuthResult> =>
    request("POST", "/api/login", body),

  logout: (): Promise<{ ok: boolean }> => request("POST", "/api/logout"),

  changePassword: (currentPassword: string, newPassword: string): Promise<{ ok: boolean }> =>
    request("POST", "/api/account/password", {
      current_password: currentPassword,
      new_password: newPassword,
    }),

  getBusiness: (id: string): Promise<BusinessProfile> => request("GET", `/api/businesses/${id}`),

  features: (id: string): Promise<PremiumFeatureItem[]> =>
    request("GET", `/api/businesses/${id}/features`),

  requestFeature: (id: string, key: string): Promise<PremiumFeatureItem> =>
    request("POST", `/api/businesses/${id}/features/${key}/request`),

  voiceDemoNumbers: (id: string): Promise<VoiceDemoNumber[]> =>
    request("GET", `/api/businesses/${id}/voice-demo-numbers`),

  customerFacts: (id: string, customerId: string): Promise<CustomerFact[]> =>
    request("GET", `/api/businesses/${id}/customers/${customerId}/facts`),

  putBusiness: (id: string, body: BusinessProfile): Promise<BusinessProfile> =>
    request("PUT", `/api/businesses/${id}`, body),

  deleteAccount: (id: string): Promise<unknown> => request("DELETE", `/api/businesses/${id}`),

  setLocale: (id: string, locale: string): Promise<{ locale: string }> =>
    request("PUT", `/api/businesses/${id}/locale`, { locale }),

  getServices: (id: string): Promise<(ServiceInput & { id: string })[]> =>
    request("GET", `/api/businesses/${id}/services`),

  deleteService: (id: string, serviceId: string): Promise<unknown> =>
    request("DELETE", `/api/businesses/${id}/services/${serviceId}`),

  getLlm: (id: string): Promise<{ mode: string; api_key_hint?: string | null }> =>
    request("GET", `/api/businesses/${id}/llm`),

  putService: (id: string, serviceId: string, body: ServiceInput): Promise<unknown> =>
    request("PUT", `/api/businesses/${id}/services/${serviceId}`, body),

  // Groups (the API's "resources"): a specialist/calendar that owns a schedule.
  getGroups: (id: string): Promise<Group[]> => request("GET", `/api/businesses/${id}/resources`),

  putGroup: (
    id: string,
    groupId: string,
    body: { name: string; working_hours: WorkingHours[] },
  ): Promise<unknown> => request("PUT", `/api/businesses/${id}/resources/${groupId}`, body),

  deleteGroup: (id: string, groupId: string): Promise<unknown> =>
    request("DELETE", `/api/businesses/${id}/resources/${groupId}`),

  putLlm: (id: string, body: LlmConfigInput): Promise<unknown> =>
    request("PUT", `/api/businesses/${id}/llm`, body),

  connectTelegram: (id: string, botToken: string): Promise<TelegramStatus> =>
    request("POST", `/api/businesses/${id}/telegram/connect`, { bot_token: botToken }),

  telegramStatus: (id: string): Promise<TelegramStatus> =>
    request("GET", `/api/businesses/${id}/telegram`),

  getOwnerTelegram: (id: string): Promise<OwnerTelegram> =>
    request("GET", `/api/businesses/${id}/telegram-owner`),

  confirmOwnerTelegram: (id: string, code: string): Promise<OwnerTelegram> =>
    request("POST", `/api/businesses/${id}/telegram-owner/confirm`, { code }),

  setOwnerNotifications: (id: string, enabled: boolean): Promise<OwnerTelegram> =>
    request("PUT", `/api/businesses/${id}/telegram-owner/notifications`, { enabled }),

  unlinkOwnerTelegram: (id: string): Promise<OwnerTelegram> =>
    request("DELETE", `/api/businesses/${id}/telegram-owner`),

  appointments: (id: string, query: AppointmentQuery): Promise<AppointmentPage> => {
    const params = new URLSearchParams({
      limit: String(query.limit),
      offset: String(query.offset),
      include_cancelled: String(query.includeCancelled ?? false),
      q: query.q ?? "",
    });
    return request("GET", `/api/businesses/${id}/appointments?${params.toString()}`);
  },

  confirmAppointment: (
    id: string,
    appointmentId: string,
  ): Promise<{ id: string; status: string }> =>
    request("POST", `/api/businesses/${id}/appointments/${appointmentId}/confirm`),

  cancelAppointment: (
    id: string,
    appointmentId: string,
    reason: string,
  ): Promise<AppointmentResult> =>
    request("POST", `/api/businesses/${id}/appointments/${appointmentId}/cancel`, { reason }),

  rescheduleAppointment: (
    id: string,
    appointmentId: string,
    start: string,
  ): Promise<AppointmentResult> =>
    request("POST", `/api/businesses/${id}/appointments/${appointmentId}/reschedule`, { start }),

  conversations: (id: string): Promise<MessageView[]> =>
    request("GET", `/api/businesses/${id}/conversations`),

  sendOwnerMessage: (id: string, customerId: string, text: string): Promise<{ handled: boolean }> =>
    request("POST", `/api/businesses/${id}/conversations/${customerId}/messages`, { text }),

  setHandoff: (id: string, customerId: string, handled: boolean): Promise<{ handled: boolean }> =>
    request("POST", `/api/businesses/${id}/conversations/${customerId}/handoff`, { handled }),

  // The signed-in identity + role (the source of truth for showing the Admin area).
  me: (): Promise<MeResult> => request("GET", "/api/me"),

  // Admin analytics (ADR-0012). The admin guard enforces access server-side.
  adminOverview: (): Promise<AdminOverview> => request("GET", "/api/admin/overview"),

  adminTimeseries: (metric: TimeseriesMetric, from: string, to: string): Promise<DailyCount[]> => {
    const params = new URLSearchParams({ metric, from, to });
    return request("GET", `/api/admin/timeseries?${params.toString()}`);
  },

  adminBusinesses: (query: BusinessDirectoryQuery): Promise<BusinessPage> => {
    const params = new URLSearchParams({
      limit: String(query.limit),
      offset: String(query.offset),
      sort: query.sort,
      descending: String(query.descending),
      q: query.q ?? "",
    });
    return request("GET", `/api/admin/businesses?${params.toString()}`);
  },

  // Admin entitlement management (ADR-0013). Behind the admin guard, server-side.
  adminPendingEntitlements: (): Promise<AdminEntitlement[]> =>
    request("GET", "/api/admin/entitlements"),

  adminDecideFeature: (
    businessId: string,
    key: string,
    status: "active" | "suspended",
  ): Promise<AdminEntitlement> =>
    request("PUT", `/api/admin/businesses/${businessId}/features/${key}`, { status }),
};
