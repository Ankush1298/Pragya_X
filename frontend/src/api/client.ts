import type {
  AssessmentResult,
  AttemptSummary,
  AuthResponse,
  ChallengeResult,
  ChatHistory,
  ChatMessage,
  DailyChallenge,
  Dashboard,
  Health,
  Option,
  Question,
  Subject,
  SubjectList,
  User,
} from "./types";

// Empty base = same origin; Vite proxies /api to FastAPI in dev.
const BASE = import.meta.env.VITE_API_URL ?? "";
const TOKEN_KEY = "pragyax_token";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

let onUnauthorized: () => void = () => {};
export const setUnauthorizedHandler = (fn: () => void) => (onUnauthorized = fn);

function errorMessage(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  // FastAPI 422 validation errors: [{loc, msg}, ...]
  if (Array.isArray(detail) && detail.length) {
    return detail.map((d: { loc?: string[]; msg?: string }) => `${d.loc?.at(-1) ?? "field"}: ${d.msg}`).join("; ");
  }
  return `Request failed (${status})`;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = tokenStore.get();
  let res: Response;
  try {
    res = await fetch(`${BASE}/api${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(0, "Cannot reach PragyaX. Please check your connection and try again.");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized();
    throw new ApiError(res.status, errorMessage(body, res.status));
  }
  return body as T;
}

export const post = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });
export const put = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "PUT", body: data === undefined ? undefined : JSON.stringify(data) });
export const patch = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "PATCH", body: data === undefined ? undefined : JSON.stringify(data) });
export const get = <T>(path: string) => request<T>(path);

export const api = {
  health: () => request<Health>("/health"),

  register: (name: string, email: string, password: string, referral_code?: string) =>
    post<AuthResponse>("/auth/register", { name, email, password, referral_code }),
  login: (email: string, password: string) => post<AuthResponse>("/auth/login", { email, password }),
  me: () => request<User>("/auth/me"),
  logout: () => post<{ message: string }>("/auth/logout"),

  subjects: () => request<SubjectList>("/subjects"),
  selectSubject: (subject_id: string) => post<Subject>("/subjects/select", { subject_id }),

  chatHistory: () => request<ChatHistory>("/chat/history"),
  sendChat: (message: string, subject: string) => post<ChatMessage>("/chat/message", { message, subject }),

  questions: (subjectId: string) =>
    request<Question[]>(`/assessments/questions?subject_id=${encodeURIComponent(subjectId)}`),
  submitAssessment: (subject_id: string, answers: Record<string, Option>) =>
    post<AssessmentResult>("/assessments/submit", { subject_id, answers }),
  history: () => request<{ attempts: AttemptSummary[] }>("/assessments/history"),
  attempt: (id: string) => request<AssessmentResult>(`/assessments/${encodeURIComponent(id)}`),

  dashboard: () => request<Dashboard>("/dashboard"),

  dailyChallenge: () => request<DailyChallenge>(`/challenges/daily?date_str=${new Date().toISOString().slice(0,10)}`),
  submitChallenge: (challenge_id: string, selected_option: Option) =>
    post<ChallengeResult>("/challenges/submit", { challenge_id, selected_option }),
};
