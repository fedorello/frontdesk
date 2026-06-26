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

export interface BusinessProfile {
  name: string;
  timezone: string;
  lead_time_minutes?: number;
  buffer_minutes?: number;
  knowledge?: { question: string; answer: string }[];
}

export interface ServiceInput {
  name: string;
  duration_minutes: number;
  price_cents?: number | null;
  currency?: string | null;
  resource_ids?: string[];
}

export interface WorkingHours {
  weekday: number;
  opens: string;
  closes: string;
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
    throw new ApiError(response.status, await response.text());
  }
  return (await response.json()) as T;
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

  putBusiness: (id: string, body: BusinessProfile, token: string): Promise<BusinessProfile> =>
    request("PUT", `/api/businesses/${id}`, body, token),

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
};
