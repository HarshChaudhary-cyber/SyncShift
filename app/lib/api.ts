export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(message: string, status: number, code: string = 'api_error', details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export interface UserProfile {
  user_id: number;
  email: string;
  timezone: string;
  weekly_work_hour_limit: number;
}

export interface BlockOut {
  id: number;
  user_id?: number;
  type: 'class' | 'shift';
  title: string;
  location?: string | null;
  day_of_week: number; // 0 = Sun, 1 = Mon ... 6 = Sat
  start_time: string;
  end_time: string;
  duration_minutes?: number | null;
  is_overnight?: boolean;
  effective_from?: string | null;
  effective_until?: string | null;
  is_flexible?: boolean;
  hourly_wage?: number | null;
  course_id?: number | null;
  deleted?: boolean;
  isSaving?: boolean;
}

export interface ConflictItem {
  id: number;
  block_a_id: number;
  block_b_id: number;
  overlap_minutes: number;
  severity: 'hard' | 'warning' | 'info' | string;
  overlap_start: string;
  overlap_end: string;
  day_of_week?: number | null;
  description?: string | null;
}

export interface WeeklyTotals {
  shift_hours: number;
  class_hours: number;
  expected_earnings: number;
  over_limit: boolean;
}

export interface WeekViewData {
  week_start: string;
  blocks: BlockOut[];
  conflicts: ConflictItem[];
  totals: WeeklyTotals;
}

export interface BlockCreatePayload {
  type: 'class' | 'shift';
  title: string;
  location?: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string;
  effective_from?: string | null;
  effective_until?: string | null;
  is_flexible?: boolean;
  hourly_wage?: number | null;
  course_id?: number | null;
}

export interface BlockUpdatePayload {
  title?: string;
  location?: string | null;
  day_of_week?: number;
  start_time?: string;
  end_time?: string;
  effective_from?: string | null;
  effective_until?: string | null;
  is_flexible?: boolean;
  hourly_wage?: number | null;
}

export interface CourseOut {
  id: number;
  code: string;
  name: string;
  color: string;
}

export interface CourseCreatePayload {
  code: string;
  name: string;
  color: string;
}

export interface IcsPreviewItem {
  temp_id?: string;
  title: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  location?: string | null;
  course_code?: string;
  recurring?: boolean;
  notes?: string;
}

export interface IcsPreviewResponse {
  preview: IcsPreviewItem[];
  unmatched: unknown[];
}

export interface IcsConfirmPayload {
  preview_blocks: {
    title: string;
    day_of_week: number;
    start_time: string;
    end_time: string;
    location?: string | null;
    course_id?: number;
    effective_from?: string;
    effective_until?: string;
  }[];
}

export interface IcsConfirmResponse {
  created_count: number;
  conflicts_detected: number;
}

export interface AuthResponseData {
  user_id: number;
  email: string;
  token: string;
}

export const AUTH_TOKEN_KEY = 'syncshift_jwt';

/** Write a JWT to localStorage. No-op in SSR. */
export function setAuthToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  }
}

/** Read JWT from localStorage. Returns empty string in SSR or if absent. */
export function getAuthToken(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem(AUTH_TOKEN_KEY) ?? '';
}

/** Remove JWT from localStorage (logout / 401 expiry). No-op in SSR. */
export function clearAuthToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`;
  const headers = new Headers(options.headers || {});
  
  if (!headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${getAuthToken()}`);
  }
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, { ...options, headers });
  const rawText = await response.text();
  let json: Record<string, unknown> = {};
  try {
    json = rawText ? JSON.parse(rawText) : {};
  } catch {
    json = { raw: rawText };
  }

  if (!response.ok) {
    const errorObj = (json.error as Record<string, unknown>) || {};
    const message = (errorObj.message as string) || (json.detail as string) || `Request failed with status ${response.status}`;
    const code = (errorObj.code as string) || (response.status === 422 ? 'validation_error' : 'request_failed');
    throw new ApiError(message, response.status, code, errorObj);
  }

  return json.data as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthResponseData>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (email: string, password: string, timezone = 'Europe/London', weekly_work_hour_limit = 20.0) =>
    request<AuthResponseData>('/auth/register', { method: 'POST', body: JSON.stringify({ email, password, timezone, weekly_work_hour_limit }) }),
  getAuthMe: () => request<UserProfile>('/auth/me'),
  getWeekView: (weekStart: string) => request<WeekViewData>(`/week?start=${encodeURIComponent(weekStart)}`),
  getConflicts: (weekStart: string) => request<{ conflicts: ConflictItem[]; weekly_totals: WeeklyTotals }>(`/conflicts?week_start=${encodeURIComponent(weekStart)}`),
  createBlock: (payload: BlockCreatePayload) => request<BlockOut>('/blocks', { method: 'POST', body: JSON.stringify(payload) }),
  updateBlock: (id: number, payload: BlockUpdatePayload) => request<BlockOut>(`/blocks/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteBlock: (id: number) => request<{ deleted: boolean }>(`/blocks/${id}`, { method: 'DELETE' }),
  duplicateBlock: (id: number, daysOffset = 0) => request<BlockOut>(`/blocks/${id}/duplicate`, { method: 'POST', body: JSON.stringify({ days_offset: daysOffset }) }),
  getCourses: () => request<CourseOut[]>('/courses'),
  createCourse: (payload: CourseCreatePayload) => request<CourseOut>('/courses', { method: 'POST', body: JSON.stringify(payload) }),
  previewIcs: async (file: File): Promise<IcsPreviewResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    return request<IcsPreviewResponse>('/import/ics', { method: 'POST', body: formData });
  },
  confirmIcs: (payload: IcsConfirmPayload): Promise<IcsConfirmResponse> => {
    return request<IcsConfirmResponse>('/import/ics/confirm', { method: 'POST', body: JSON.stringify(payload) });
  },
};
