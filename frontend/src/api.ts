let csrf = "";
export function setCsrf(value: string) {
  csrf = value;
}
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function api<T = any>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch("/api" + path, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(options.method && options.method !== "GET"
        ? { "X-CSRF-Token": csrf }
        : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const data = await response
      .json()
      .catch(() => ({ detail: "Unable to reach SENTINEL" }));
    if (
      response.status === 401 &&
      path !== "/auth/login" &&
      path !== "/auth/me"
    )
      window.dispatchEvent(new Event("session-expired"));
    throw new ApiError(data.detail || "Request failed", response.status);
  }
  if (path.startsWith("/reports/export")) return (await response.blob()) as T;
  return response.status === 204 ? (undefined as T) : response.json();
}
export type User = {
  id: number;
  username: string;
  role: "admin" | "analyst";
  is_active: boolean;
};
export type SecurityEvent = {
  id: number;
  event_type: string;
  source_ip: string;
  user_id: number | null;
  occurred_at: string;
  metadata: Record<string, any>;
  severity: string;
  is_demo: boolean;
};
export type Alert = {
  id: number;
  rule_id: string;
  severity: string;
  status: string;
  description: string;
  created_at: string;
  updated_at: string;
  subject: string;
  is_demo: boolean;
  events?: SecurityEvent[];
  history?: {
    id: number;
    new_status: string;
    old_status: string | null;
    note: string;
    actor_id: number | null;
    created_at: string;
  }[];
};
export type Summary = {
  scope: string;
  days: number;
  generated_at: string;
  total_events: number;
  active_alerts: number;
  high_risk_events: number;
  login_success: number;
  login_failed: number;
  total_alerts: number;
  resolved_alerts: number;
  resolution_rate: number;
  severity: Record<string, number>;
  status: Record<string, number>;
  event_types: Record<string, number>;
  timeline: { date: string; success: number; failed: number; other: number }[];
  recommendations: string[];
};
