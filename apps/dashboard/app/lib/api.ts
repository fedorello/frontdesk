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
};
