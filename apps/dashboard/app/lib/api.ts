// Typed client for the tovayo API (M5). One place that knows the endpoints and
// shapes, reused by every screen regardless of how it looks.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  token: string;
  business_id: string;
}

export interface WorkingHours {
  weekday: number; // Monday = 0
  opens: string; // "HH:MM:SS"
  closes: string;
}

export interface BusinessProfile {
  name: string;
  timezone: string;
  lead_time_minutes?: number;
  buffer_minutes?: number;
  knowledge?: { question: string; answer: string }[];
  description?: string;
  address?: string;
}

export interface ServiceInput {
  name: string;
  duration_minutes: number;
  price_cents?: number | null;
  currency?: string | null;
  resource_ids?: string[];
  description?: string;
  working_hours?: WorkingHours[];
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

export interface AppointmentView {
  service: string;
  starts_at: string;
  ends_at: string;
  status: string;
}

export interface MessageView {
  customer: string;
  role: string;
  text: string;
  at: string;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  token?: string,
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "content-type": "application/json",
      ...(token ? { authorization: `Bearer ${token}` } : {}),
    },
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

export const api = {
  signup: (body: {
    email: string;
    password: string;
    business_name: string;
    timezone?: string;
  }): Promise<AuthResult> => request("POST", "/api/signup", body),

  login: (body: { email: string; password: string }): Promise<AuthResult> =>
    request("POST", "/api/login", body),

  getBusiness: (id: string, token: string): Promise<BusinessProfile> =>
    request("GET", `/api/businesses/${id}`, undefined, token),

  putBusiness: (id: string, body: BusinessProfile, token: string): Promise<BusinessProfile> =>
    request("PUT", `/api/businesses/${id}`, body, token),

  getServices: (id: string, token: string): Promise<(ServiceInput & { id: string })[]> =>
    request("GET", `/api/businesses/${id}/services`, undefined, token),

  deleteService: (id: string, serviceId: string, token: string): Promise<unknown> =>
    request("DELETE", `/api/businesses/${id}/services/${serviceId}`, undefined, token),

  getLlm: (id: string, token: string): Promise<{ mode: string; api_key_hint?: string | null }> =>
    request("GET", `/api/businesses/${id}/llm`, undefined, token),

  putService: (
    id: string,
    serviceId: string,
    body: ServiceInput,
    token: string,
  ): Promise<unknown> => request("PUT", `/api/businesses/${id}/services/${serviceId}`, body, token),

  putResource: (
    id: string,
    resourceId: string,
    body: { name: string; working_hours: WorkingHours[] },
    token: string,
  ): Promise<unknown> =>
    request("PUT", `/api/businesses/${id}/resources/${resourceId}`, body, token),

  putLlm: (id: string, body: LlmConfigInput, token: string): Promise<unknown> =>
    request("PUT", `/api/businesses/${id}/llm`, body, token),

  connectTelegram: (id: string, botToken: string, token: string): Promise<TelegramStatus> =>
    request("POST", `/api/businesses/${id}/telegram/connect`, { bot_token: botToken }, token),

  telegramStatus: (id: string, token: string): Promise<TelegramStatus> =>
    request("GET", `/api/businesses/${id}/telegram`, undefined, token),

  appointments: (id: string, token: string): Promise<AppointmentView[]> =>
    request("GET", `/api/businesses/${id}/appointments`, undefined, token),

  conversations: (id: string, token: string): Promise<MessageView[]> =>
    request("GET", `/api/businesses/${id}/conversations`, undefined, token),
};
