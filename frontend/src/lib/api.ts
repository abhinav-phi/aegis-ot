/** Typed API client (R31). Access token in memory only; refresh via cookie. */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
}

export interface ApiEnvelope<T> {
  ok: boolean;
  data: T;
  code?: string;
  detail?: string;
}

let accessToken = "";

function headers(): Record<string, string> {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

async function request<T>(method: string, path: string, body?: unknown): Promise<ApiEnvelope<T>> {
  let res = await fetch(`/api${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...headers() },
    credentials: "include",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401) {
    const refreshed = await fetch("/api/auth/refresh", {
      method: "POST",
      credentials: "include",
    });
    if (refreshed.ok) {
      const data = (await refreshed.json()) as ApiEnvelope<LoginResponse>;
      accessToken = data.data.access_token;
      res = await fetch(`/api${path}`, {
        method,
        headers: { "Content-Type": "application/json", ...headers() },
        credentials: "include",
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    }
  }
  const json = (await res.json()) as ApiEnvelope<T>;
  if (!res.ok) throw new Error(json.code || `HTTP ${res.status}`);
  return json;
}

export const api = {
  setToken: (t: string) => (accessToken = t),
  login: (email: string, password: string) =>
    request<LoginResponse>("POST", "/auth/login", { email, password }),
  logout: () => request("POST", "/auth/logout"),
  me: () => request<{ user_id: string; role: string }>("GET", "/auth/me"),
  incidents: (status?: string) =>
    request<Array<{ id: string; severity: string; status: string; title: string; start_ts: string }>>(
      "GET", `/incidents${status ? `?status=${status}` : ""}`),
  incident: (id: string) =>
    request<{
      id: string; status: string; severity: string; title: string;
      anomalies: Array<{ anomaly_id: string; hypothesis: string | null; top_sensors: Array<{ sensor: string; contribution_pct: number }>; invariant_checks: Array<{ rule_id: string; pass: boolean }>; low_confidence: boolean }>;
      threat_mappings: Array<{ technique_id: string; confidence: number }>;
    }>("GET", `/incidents/${id}`),
  telemetry: () =>
    request<Array<{ window_start: string; score: number; is_anomaly: boolean }>>("GET", "/telemetry/latest"),
  agentRun: (id: string) =>
    request<{ id: string; variant: string; status: string; steps: number; messages: Array<{ role: string; tool_name: string | null; payload: Record<string, unknown> }> }>(
      "GET", `/agent/${id}`),
  approvals: () =>
    request<Array<{ id: string; plan_id: string; revision: number | null; hash_suffix: string | null; expires_at: string; requested_by: string }>>(
      "GET", "/approvals"),
  approve: (id: string) => request("POST", `/approvals/${id}/approve`),
  deny: (id: string, reason: string) =>
    request("POST", `/approvals/${id}/deny`, { reason }),
  amend: (id: string, steps_patch: unknown[]) =>
    request<{ new_plan_id: string; new_revision: number }>(
      "POST", `/approvals/${id}/amend`, { steps_patch }),
  executeSandbox: (planId: string) =>
    request("POST", "/sandbox/execute", { plan_id: planId }),
  validator: (planId: string) =>
    request<{ verdict: string | null; checks: unknown[]; hash_suffix: string }>(
      "GET", `/validator/${planId}`),
  evalMetrics: (exp?: string) =>
    request<Array<{ metric: string; value: number; source: string }>>(
      "GET", `/eval/metrics${exp ? `?exp=${exp}` : ""}`),
  demoLatest: () => request<Record<string, number>>("GET", "/demo/attack/latest"),
};
