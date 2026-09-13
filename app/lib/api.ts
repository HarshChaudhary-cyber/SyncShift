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
  minimum_transition_minutes?: number;
  display_name?: string | null;
  avatar_url?: string | null;
  currency?: string;
  language?: string;
  theme?: string;
  oauth_provider?: string | null;
  has_password?: boolean;
  created_at?: string | null;
}

export interface UserProfileUpdatePayload {
  display_name?: string | null;
  timezone?: string | null;
  weekly_work_hour_limit?: number | null;
  minimum_transition_minutes?: number | null;
  currency?: string | null;
  language?: string | null;
  theme?: string | null;
  avatar_url?: string | null;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface DeleteAccountPayload {
  password?: string;
  confirm?: string;
}

export interface ExportDataResponse {
  user: Record<string, any>;
  courses: Record<string, any>[];
  time_blocks: Record<string, any>[];
  study_tasks: Record<string, any>[];
  notification_prefs?: Record<string, any> | null;
  exported_at: string;
}

export interface BlockOut {
  id: number;
  user_id?: number;
  type: 'class' | 'shift' | 'study';
  title: string;
  location?: string | null;
  day_of_week: number; // 0 = Sun, 1 = Mon ... 6 = Sat
  start_time: string;
  end_time: string;
  duration_minutes?: number | null;
  is_overnight?: boolean;
  is_recurring?: boolean;
  recurrence_interval?: number;
  specific_date?: string | null;
  occurrence_date?: string | null;
  is_exception?: boolean;
  original_date?: string | null;
  override_id?: number | null;
  effective_from?: string | null;
  effective_until?: string | null;
  is_flexible?: boolean;
  hourly_wage?: number | null;
  course_id?: number | null;
  study_task_id?: number | null;
  color?: string | null;
  deleted?: boolean;
  isSaving?: boolean;
}

export interface TodayViewData {
  date: string;
  day_of_week: number;
  blocks: BlockOut[];
  conflicts: ConflictItem[];
  shift_hours: number;
  expected_earnings: number;
  class_hours: number;
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
  message?: string | null;
  conflict_type?: string;
  available_transition_minutes?: number | null;
  required_transition_minutes?: number | null;
  location_a?: string | null;
  location_b?: string | null;
}

export interface ActionCheckItem {
  label: string;
  passed: boolean;
  warning?: boolean;
}

export interface ActionPreview {
  action_type: string;
  block_id: number;
  title: string;
  original: Record<string, any>;
  target: Record<string, any>;
  checks: ActionCheckItem[];
}

export interface AssistantChatResponse {
  message: string;
  intent: string;
  requires_confirmation: boolean;
  action?: ActionPreview | null;
  choices?: Record<string, any>[] | null;
  suggestions: string[];
}

export interface AssistantConfirmResponse {
  success: boolean;
  message: string;
  updated_block?: Record<string, any> | null;
  conflicts?: Record<string, any>[];
  health_score?: number | null;
}

export interface AuditLogItem {
  id: number;
  user_id: number;
  action: string;
  entity_type?: string | null;
  entity_id?: string | null;
  description: string;
  metadata?: Record<string, any> | null;
  ip_address?: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
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

export interface DashboardUser {
  display_name: string;
  email: string;
  avatar_url?: string | null;
  timezone: string;
  weekly_work_hour_limit: number;
  currency?: string;
}

export interface DashboardBlock {
  id: number;
  type: 'class' | 'shift' | 'personal' | 'study' | 'other' | string;
  title: string;
  start_time: string;
  end_time: string;
  location?: string | null;
  color?: string | null;
  is_now: boolean;
  day_of_week?: number | null;
  occurrence_date?: string | null;
  is_exception?: boolean;
  is_recurring?: boolean;
}

export interface NextUpBlock {
  id: number;
  title: string;
  start_time: string;
  end_time?: string | null;
  location?: string | null;
  type: string;
  color?: string | null;
  occurrence_date?: string | null;
}

export interface DashboardNextUp {
  block: NextUpBlock;
  minutes_until: number;
  label: string;
}

export interface DashboardToday {
  date: string;
  day_name: string;
  blocks: DashboardBlock[];
  conflicts: ConflictItem[];
  shift_hours: number;
  class_hours: number;
  expected_earnings: number;
}

export interface DashboardWeek {
  start: string;
  end: string;
  total_shift_hours: number;
  total_class_hours: number;
  expected_earnings: number;
  conflict_count: number;
  over_work_limit: boolean;
  work_limit: number;
}

export interface DashboardAlert {
  id: string;
  type: 'conflict' | 'work_limit' | string;
  severity: 'hard' | 'warning' | 'info' | string;
  message: string;
  block_ids?: number[] | null;
}

export interface DashboardData {
  user: DashboardUser;
  today: DashboardToday;
  next_up: DashboardNextUp | null;
  week: DashboardWeek;
  alerts: DashboardAlert[];
  health?: ScheduleHealthData;
  work?: WorkLimitAnalytics;
  study?: {
    planned_hours: number;
    target_hours: number;
    remaining_hours: number;
    pending_tasks_count: number;
    upcoming_task: {
      id: number;
      title: string;
      deadline: string;
      priority: string;
    } | null;
  };
  analytics?: {
    class_hours: number;
    work_hours: number;
    study_hours: number;
    conflicts: number;
    earnings: number;
    currency: string;
  };
  recommendations?: string[];
  adaptive_state?: 'new_user' | 'academic_only' | 'conflicts' | 'over_work_limit' | 'near_work_limit' | 'on_track';
  academics?: StudentAcademicSummary | null;
}

export interface CourseBrief {
  id: number;
  code: string;
  name: string;
  color: string;
}

export interface HealthFactor {
  type: 'positive' | 'warning' | 'info';
  text: string;
  impact?: number;
}

export interface ScheduleHealthData {
  score: number;
  category: 'Excellent' | 'Healthy' | 'Moderate' | 'Needs attention' | 'Overloaded' | string;
  summary: string;
  factors: HealthFactor[];
  improvements: string[];
}

export interface DailyWorkloadItem {
  day: string;
  date: string;
  day_of_week: number;
  class_hours: number;
  work_hours: number;
  study_hours: number;
  total_hours: number;
  is_heavy: boolean;
  label: string;
}

export interface HoursBreakdown {
  class_hours: number;
  work_hours: number;
  study_hours: number;
  total_hours: number;
  free_hours: number;
}

export interface WorkLimitAnalytics {
  configured: number;
  used: number;
  remaining: number;
  percentage: number;
  over_limit: boolean;
  over_hours: number;
}

export interface ConflictsAnalytics {
  hard: number;
  warning: number;
  total: number;
  trend?: string | null;
}

export interface EarningsAnalytics {
  currency: string;
  currency_symbol: string;
  estimated_week: number;
  estimated_month: number;
  missing_wage_shifts: number;
}

export interface TimeDistributionData {
  class_percentage: number;
  work_percentage: number;
  study_percentage: number;
  free_percentage: number;
}

export interface AnalyticsData {
  period: { start: string; end: string };
  hours: HoursBreakdown;
  work_limit: WorkLimitAnalytics;
  conflicts: ConflictsAnalytics;
  earnings: EarningsAnalytics;
  daily_workload: DailyWorkloadItem[];
  time_distribution: TimeDistributionData;
  health: ScheduleHealthData;
}

export interface StudyTask {
  id: number;
  user_id: number;
  title: string;
  course_id?: number | null;
  course?: CourseBrief | null;
  total_hours_required: number;
  deadline: string; // YYYY-MM-DD
  status: 'pending' | 'scheduled' | 'done' | string;
  priority?: 'high' | 'medium' | 'low' | string;
  preferred_duration?: number;
  completed_hours?: number;
  hours_scheduled: number;
  hours_done: number;
  created_at?: string | null;
}

export interface StudyTaskCreatePayload {
  title: string;
  course_id?: number | null;
  total_hours_required: number;
  deadline: string; // YYYY-MM-DD
  priority?: 'high' | 'medium' | 'low';
  preferred_duration?: number;
}

export interface StudyTaskUpdatePayload {
  title?: string;
  course_id?: number | null;
  total_hours_required?: number;
  deadline?: string;
  status?: string;
  priority?: string;
  preferred_duration?: number;
  completed_hours?: number;
}

export interface PlanSessionSuggested {
  temp_id: string;
  day_of_week: number;
  day_name: string;
  date: string;
  start_time: string;
  end_time: string;
  duration_hours: number;
  task_id: number;
  type: string;
  score?: number;
  reasons?: string[];
  is_healthy?: boolean;
}

export interface PlanPreviewResponse {
  suggested: PlanSessionSuggested[];
  hours_scheduled: number;
  short_by_hours?: number | null;
  gaps_considered: number;
}

export interface PlanConfirmBlock {
  temp_id?: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  date?: string;
}

export interface PlanConfirmPayload {
  approved_blocks: PlanConfirmBlock[];
}

export interface BlockCreatePayload {
  type: 'class' | 'shift' | 'study';
  title: string;
  location?: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_recurring?: boolean;
  recurrence_interval?: number;
  specific_date?: string | null;
  effective_from?: string | null;
  effective_until?: string | null;
  is_flexible?: boolean;
  hourly_wage?: number | null;
  course_id?: number | null;
  study_task_id?: number | null;
}

export interface BlockUpdatePayload {
  type?: 'class' | 'shift' | 'study';
  title?: string;
  location?: string | null;
  day_of_week?: number;
  start_time?: string;
  end_time?: string;
  is_recurring?: boolean;
  recurrence_interval?: number;
  specific_date?: string | null;
  occurrence_date?: string | null;
  scope?: 'this' | 'future' | 'all';
  effective_from?: string | null;
  effective_until?: string | null;
  is_flexible?: boolean;
  hourly_wage?: number | null;
  course_id?: number | null;
  study_task_id?: number | null;
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

/** Extended preview item returned by /import/file for multi-format imports. */
export interface FilePreviewItem {
  temp_id?: string;
  title: string;
  day_of_week: number; // 0=Mon … 6=Sun; -1 if unparseable
  day_name?: string;
  start_time: string;  // "HH:MM" or "" if unparseable
  end_time: string;    // "HH:MM" or ""
  location?: string | null;
  confidence: 'high' | 'low';
  source_line?: string;
  course_code?: string | null;
  is_recurring?: boolean;
  notes?: string;
  status?: 'valid' | 'needs_review' | 'duplicate' | 'conflict';
  is_duplicate?: boolean;
  duplicate_reason?: string | null;
  has_conflict?: boolean;
  conflict_description?: string | null;
  issues?: string[];
}

export interface FilePreviewResponse {
  preview: FilePreviewItem[];
  total_found?: number;
  valid_count?: number;
  review_count?: number;
  duplicate_count?: number;
  conflict_count?: number;
  file_type?: string;
  message?: string; // summary or guidance message
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
  timezone?: string | null;
  display_name?: string | null;
  avatar_url?: string | null;
}

export interface NotificationPrefs {
  user_id: number;
  push_enabled: boolean;
  email_enabled: boolean;
  class_reminder_min: number;
  shift_reminder_min: number;
  study_reminder_min: number;
  deadline_reminder: boolean;
  conflict_alerts: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
}

export interface NotificationPrefsUpdatePayload {
  push_enabled?: boolean;
  email_enabled?: boolean;
  class_reminder_min?: number;
  shift_reminder_min?: number;
  study_reminder_min?: number;
  deadline_reminder?: boolean;
  conflict_alerts?: boolean;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
}

export interface PushSubscriptionKeys {
  p256dh: string;
  auth: string;
}

export interface PushSubscriptionPayload {
  endpoint: string;
  expirationTime?: number | null;
  keys: PushSubscriptionKeys;
}

export interface NotificationLogItem {
  id: number;
  user_id: number;
  type: 'class' | 'shift' | 'study' | 'deadline' | 'conflict' | 'test' | string;
  title: string;
  body: string;
  sent_at: string;
  channel: 'push' | 'email' | string;
}

export const AUTH_TOKEN_KEY = 'syncshift_jwt';


/** Write a JWT to localStorage. Sets both 'syncshift_jwt' and 'token'. No-op in SSR. */
export function setAuthToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    localStorage.setItem('token', token);
  }
}

/** Read JWT from localStorage. Returns empty string in SSR or if absent. */
export function getAuthToken(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem(AUTH_TOKEN_KEY) || localStorage.getItem('token') || '';
}

/** Remove JWT from localStorage (logout / 401 expiry). No-op in SSR. */
export function clearAuthToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem('token');
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
    const errorObj = typeof json.error === 'object' && json.error !== null ? (json.error as Record<string, unknown>) : {};
    const message =
      (errorObj.message as string) ||
      (typeof json.error === 'string' ? json.error : null) ||
      (json.detail as string) ||
      `Request failed with status ${response.status}`;
    const code = (errorObj.code as string) || (response.status === 422 ? 'validation_error' : 'request_failed');
    throw new ApiError(message, response.status, code, errorObj);
  }

  return (json.data !== undefined ? json.data : json) as T;
}


export const api = {
  login: (email: string, password: string) =>
    request<AuthResponseData>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (email: string, password: string, timezone = 'Europe/London', weekly_work_hour_limit = 20.0) =>
    request<AuthResponseData>('/auth/register', { method: 'POST', body: JSON.stringify({ email, password, timezone, weekly_work_hour_limit }) }),
  oauthGoogle: (id_token: string) =>
    request<AuthResponseData>('/auth/oauth/google', { method: 'POST', body: JSON.stringify({ id_token }) }),
  oauthFacebook: (access_token: string, user_id: string) =>
    request<AuthResponseData>('/auth/oauth/facebook', { method: 'POST', body: JSON.stringify({ access_token, user_id }) }),
  oauthApple: (id_token: string, display_name?: string) =>
    request<AuthResponseData>('/auth/oauth/apple', { method: 'POST', body: JSON.stringify({ id_token, display_name }) }),
  getAuthMe: () => request<UserProfile>('/auth/me'),
  updateProfile: (payload: UserProfileUpdatePayload) =>
    request<UserProfile>('/auth/me', { method: 'PATCH', body: JSON.stringify(payload) }),
  updateMe: (payload: UserProfileUpdatePayload) =>
    request<UserProfile>('/auth/me', { method: 'PATCH', body: JSON.stringify(payload) }),
  changePassword: (payload: ChangePasswordPayload) =>
    request<{ message: string }>('/auth/change-password', { method: 'POST', body: JSON.stringify(payload) }),
  deleteAccount: (payload: DeleteAccountPayload) =>
    request<{ message: string }>('/auth/delete-account', { method: 'POST', body: JSON.stringify(payload) }),
  exportData: () =>
    request<ExportDataResponse>('/auth/export'),
  getToday: (date?: string) => request<TodayViewData>(date ? `/today?date=${encodeURIComponent(date)}` : '/today'),
  getDashboard: (date?: string) =>
    request<DashboardData>(date ? `/dashboard?date=${encodeURIComponent(date)}` : '/dashboard'),
  getWeekView: (weekStart: string) => request<WeekViewData>(`/week?start=${encodeURIComponent(weekStart)}`),
  getConflicts: (weekStart: string) => request<{ conflicts: ConflictItem[]; weekly_totals: WeeklyTotals }>(`/conflicts?week_start=${encodeURIComponent(weekStart)}`),
  createBlock: (payload: BlockCreatePayload) => request<BlockOut>('/blocks', { method: 'POST', body: JSON.stringify(payload) }),
  updateBlock: (id: number, payload: BlockUpdatePayload) => request<BlockOut>(`/blocks/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteBlock: (id: number, scope: 'this' | 'future' | 'all' = 'all', occurrenceDate?: string) =>
    request<{ deleted: boolean }>(`/blocks/${id}`, {
      method: 'DELETE',
      body: JSON.stringify({ scope, occurrence_date: occurrenceDate }),
    }),
  createBlockException: (id: number, payload: {
    occurrence_date: string;
    is_cancelled?: boolean;
    start_time?: string;
    end_time?: string;
    title?: string;
    location?: string;
  }) => request<BlockOut>(`/blocks/${id}/exceptions`, { method: 'POST', body: JSON.stringify(payload) }),
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
  /** Upload any supported file (PDF/DOCX/PPTX/TXT/CSV/image/ICS) for timetable parsing. */
  previewFile: async (file: File): Promise<FilePreviewResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    return request<FilePreviewResponse>('/import/file', { method: 'POST', body: formData });
  },
  /** Confirm and save blocks returned by previewFile. */
  confirmFile: (payload: IcsConfirmPayload): Promise<IcsConfirmResponse> => {
    return request<IcsConfirmResponse>('/import/file/confirm', { method: 'POST', body: JSON.stringify(payload) });
  },
  // ── Analytics & Schedule Health Endpoints ─────────────────────────────────
  getAnalytics: (weekStart?: string) =>
    request<AnalyticsData>(weekStart ? `/analytics/week?start_date=${encodeURIComponent(weekStart)}` : '/analytics/week'),
  getScheduleHealth: (weekStart?: string) =>
    request<ScheduleHealthData>(weekStart ? `/analytics/health?start_date=${encodeURIComponent(weekStart)}` : '/analytics/health'),
  // ── Study Planner Endpoints ───────────────────────────────────────────────
  getTasks: () => request<StudyTask[]>('/tasks'),
  createTask: (payload: StudyTaskCreatePayload) =>
    request<StudyTask>('/tasks', { method: 'POST', body: JSON.stringify(payload) }),
  updateTask: (id: number, payload: StudyTaskUpdatePayload) =>
    request<StudyTask>(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteTask: (id: number) =>
    request<{ deleted: boolean }>(`/tasks/${id}`, { method: 'DELETE' }),
  planTask: (id: number) =>
    request<PlanPreviewResponse>(`/tasks/${id}/plan`, { method: 'POST' }),
  confirmTaskPlan: (id: number, payload: PlanConfirmPayload) =>
    request<StudyTask>(`/tasks/${id}/plan/confirm`, { method: 'POST', body: JSON.stringify(payload) }),
  replanTask: (id: number) =>
    request<PlanPreviewResponse>(`/tasks/${id}/replan`, { method: 'POST' }),
  addPlanSlot: (taskId: number, payload: PlanConfirmBlock) =>
    request<StudyTask>(`/tasks/${taskId}/plan/add-slot`, { method: 'POST', body: JSON.stringify(payload) }),
  completeTask: (taskId: number) =>
    request<StudyTask>(`/tasks/${taskId}/complete`, { method: 'POST' }),
  // ── Notifications Endpoints ───────────────────────────────────────────────
  getNotificationPrefs: () => request<NotificationPrefs>('/notifications/prefs'),
  updateNotificationPrefs: (payload: NotificationPrefsUpdatePayload) =>
    request<NotificationPrefs>('/notifications/prefs', { method: 'PUT', body: JSON.stringify(payload) }),
  subscribePush: (payload: PushSubscriptionPayload) =>
    request<{ ok: boolean }>('/notifications/subscribe', { method: 'POST', body: JSON.stringify(payload) }),
  unsubscribePush: (endpoint: string) =>
    request<{ ok: boolean }>('/notifications/subscribe', { method: 'DELETE', body: JSON.stringify({ endpoint }) }),
  sendTestNotification: () =>
    request<{ ok: boolean; message: string; sent_count?: number }>('/notifications/test', { method: 'POST' }),
  getBlocks: (type?: string, weekStart?: string) => {
    const params = new URLSearchParams();
    if (type) params.append('type', type);
    if (weekStart) params.append('week_start', weekStart);
    const qs = params.toString();
    return request<BlockOut[]>(qs ? `/blocks?${qs}` : '/blocks');
  },
  getMyDebugData: () => request<MyDebugData>('/debug/my-data'),
  getNotificationLog: (today: boolean = false) =>
    request<NotificationLogItem[]>(`/notifications/log${today ? '?today=true' : ''}`),
  // ── SyncShift Assistant Endpoints ─────────────────────────────────────────
  chatAssistant: (message: string, context?: Record<string, any>) =>
    request<AssistantChatResponse>('/assistant/chat', { method: 'POST', body: JSON.stringify({ message, context }) }),
  confirmAssistantAction: (action: ActionPreview) =>
    request<AssistantConfirmResponse>('/assistant/confirm', { method: 'POST', body: JSON.stringify({ action }) }),
  // ── Audit Logs Endpoints ──────────────────────────────────────────────────
  getAuditLogs: (limit = 50, offset = 0) =>
    request<AuditLogListResponse>(`/audit-logs?limit=${limit}&offset=${offset}`),
  // ── Privacy & Account Endpoints ───────────────────────────────────────────
  exportPrivacyData: () =>
    request<ExportDataResponse>('/privacy/export'),
  deleteAccountPermanent: (payload: DeleteAccountPayload) =>
    request<{ message: string }>('/privacy/delete-account', { method: 'POST', body: JSON.stringify(payload) }),
  // ── University Foundation Endpoints ─────────────────────────────────────
  getMyInstitutionStatus: () =>
    request<UserInstitutionStatus>('/institutions/me'),
  createInstitution: (payload: InstitutionCreatePayload) =>
    request<Institution>('/institutions', { method: 'POST', body: JSON.stringify(payload) }),
  getInstitution: (institutionId: number) =>
    request<Institution>(`/institutions/${institutionId}`),
  updateInstitution: (institutionId: number, payload: InstitutionUpdatePayload) =>
    request<Institution>(`/institutions/${institutionId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  getUniversityDashboard: (institutionId: number) =>
    request<UniversityDashboardData>(`/institutions/${institutionId}/dashboard`),
  getInstitutionMembers: (institutionId: number) =>
    request<InstitutionMembership[]>(`/institutions/${institutionId}/members`),
  addInstitutionMember: (institutionId: number, payload: { user_id?: number; email?: string; role?: string }) =>
    request<InstitutionMembership>(`/institutions/${institutionId}/members`, { method: 'POST', body: JSON.stringify(payload) }),
  getDepartments: (institutionId: number) =>
    request<Department[]>(`/institutions/${institutionId}/departments`),
  createDepartment: (institutionId: number, payload: DepartmentCreatePayload) =>
    request<Department>(`/institutions/${institutionId}/departments`, { method: 'POST', body: JSON.stringify(payload) }),
  updateDepartment: (institutionId: number, departmentId: number, payload: DepartmentUpdatePayload) =>
    request<Department>(`/institutions/${institutionId}/departments/${departmentId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteDepartment: (institutionId: number, departmentId: number) =>
    request<{ deleted: boolean }>(`/institutions/${institutionId}/departments/${departmentId}`, { method: 'DELETE' }),
  getAcademicTerms: (institutionId: number) =>
    request<AcademicTerm[]>(`/institutions/${institutionId}/terms`),
  createAcademicTerm: (institutionId: number, payload: AcademicTermCreatePayload) =>
    request<AcademicTerm>(`/institutions/${institutionId}/terms`, { method: 'POST', body: JSON.stringify(payload) }),
  updateAcademicTerm: (institutionId: number, termId: number, payload: AcademicTermUpdatePayload) =>
    request<AcademicTerm>(`/institutions/${institutionId}/terms/${termId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteAcademicTerm: (institutionId: number, termId: number) =>
    request<{ deleted: boolean }>(`/institutions/${institutionId}/terms/${termId}`, { method: 'DELETE' }),

  // ── Task N2 Academic Resources Endpoints ─────────────────────────────────
  getAcademicCourses: (institutionId: number, params?: { department_id?: number; status?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.department_id) q.append('department_id', String(params.department_id));
    if (params?.status) q.append('status', params.status);
    if (params?.search) q.append('search', params.search);
    const qs = q.toString();
    return request<AcademicCourse[]>(`/institutions/${institutionId}/courses${qs ? `?${qs}` : ''}`);
  },
  createAcademicCourse: (institutionId: number, payload: AcademicCourseCreatePayload) =>
    request<AcademicCourse>(`/institutions/${institutionId}/courses`, { method: 'POST', body: JSON.stringify(payload) }),
  getAcademicCourse: (institutionId: number, courseId: number) =>
    request<AcademicCourse>(`/institutions/${institutionId}/courses/${courseId}`),
  updateAcademicCourse: (institutionId: number, courseId: number, payload: AcademicCourseUpdatePayload) =>
    request<AcademicCourse>(`/institutions/${institutionId}/courses/${courseId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteAcademicCourse: (institutionId: number, courseId: number) =>
    request<{ deleted: boolean }>(`/institutions/${institutionId}/courses/${courseId}`, { method: 'DELETE' }),

  getSections: (institutionId: number, params?: { course_id?: number; academic_term_id?: number; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.course_id) q.append('course_id', String(params.course_id));
    if (params?.academic_term_id) q.append('academic_term_id', String(params.academic_term_id));
    if (params?.status) q.append('status', params.status);
    const qs = q.toString();
    return request<AcademicSection[]>(`/institutions/${institutionId}/sections${qs ? `?${qs}` : ''}`);
  },
  createSection: (institutionId: number, payload: AcademicSectionCreatePayload) =>
    request<AcademicSection>(`/institutions/${institutionId}/sections`, { method: 'POST', body: JSON.stringify(payload) }),
  getSection: (institutionId: number, sectionId: number) =>
    request<AcademicSection>(`/institutions/${institutionId}/sections/${sectionId}`),
  updateSection: (institutionId: number, sectionId: number, payload: AcademicSectionUpdatePayload) =>
    request<AcademicSection>(`/institutions/${institutionId}/sections/${sectionId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteSection: (institutionId: number, sectionId: number) =>
    request<{ deleted: boolean }>(`/institutions/${institutionId}/sections/${sectionId}`, { method: 'DELETE' }),

  getSectionFaculty: (institutionId: number, sectionId: number) =>
    request<FacultyAssignment[]>(`/institutions/${institutionId}/sections/${sectionId}/faculty`),
  assignFacultyToSection: (institutionId: number, sectionId: number, payload: { faculty_id: number; role?: string; is_primary?: boolean }) =>
    request<FacultyAssignment>(`/institutions/${institutionId}/sections/${sectionId}/faculty`, { method: 'POST', body: JSON.stringify(payload) }),
  removeFacultyFromSection: (institutionId: number, sectionId: number, assignmentId: number) =>
    request<{ deleted: boolean }>(`/institutions/${institutionId}/sections/${sectionId}/faculty/${assignmentId}`, { method: 'DELETE' }),

  getFaculty: (institutionId: number, params?: { department_id?: number; status?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.department_id) q.append('department_id', String(params.department_id));
    if (params?.status) q.append('status', params.status);
    if (params?.search) q.append('search', params.search);
    const qs = q.toString();
    return request<FacultyProfile[]>(`/institutions/${institutionId}/faculty${qs ? `?${qs}` : ''}`);
  },
  createFaculty: (institutionId: number, payload: FacultyProfileCreatePayload) =>
    request<FacultyProfile>(`/institutions/${institutionId}/faculty`, { method: 'POST', body: JSON.stringify(payload) }),
  getFacultyProfile: (institutionId: number, facultyId: number) =>
    request<FacultyProfile>(`/institutions/${institutionId}/faculty/${facultyId}`),
  updateFaculty: (institutionId: number, facultyId: number, payload: FacultyProfileUpdatePayload) =>
    request<FacultyProfile>(`/institutions/${institutionId}/faculty/${facultyId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteFaculty: (institutionId: number, facultyId: number) =>
    request<{ deleted: boolean }>(`/institutions/${institutionId}/faculty/${facultyId}`, { method: 'DELETE' }),

  getRooms: (institutionId: number, params?: { building?: string; room_type?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.building) q.append('building', params.building);
    if (params?.room_type) q.append('room_type', params.room_type);
    if (params?.status) q.append('status', params.status);
    const qs = q.toString();
    return request<Room[]>(`/institutions/${institutionId}/rooms${qs ? `?${qs}` : ''}`);
  },
  createRoom: (institutionId: number, payload: RoomCreatePayload) =>
    request<Room>(`/institutions/${institutionId}/rooms`, { method: 'POST', body: JSON.stringify(payload) }),
  getRoom: (institutionId: number, roomId: number) =>
    request<Room>(`/institutions/${institutionId}/rooms/${roomId}`),
  updateRoom: (institutionId: number, roomId: number, payload: RoomUpdatePayload) =>
    request<Room>(`/institutions/${institutionId}/rooms/${roomId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteRoom: (institutionId: number, roomId: number) =>
    request<{ deleted: boolean }>(`/institutions/${institutionId}/rooms/${roomId}`, { method: 'DELETE' }),

  // ── Task N3 Student Academics & Constraints Endpoints ────────────────────
  getMyStudentProfile: () =>
    request<StudentProfile | null>('/students/me'),
  updateMyStudentProfile: (payload: StudentProfileUpdatePayload) =>
    request<StudentProfile>('/students/me', { method: 'PATCH', body: JSON.stringify(payload) }),

  getMyEnrollments: (params?: { academic_term_id?: number; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.academic_term_id) q.append('academic_term_id', String(params.academic_term_id));
    if (params?.status) q.append('status', params.status);
    const qs = q.toString();
    return request<SectionEnrollment[]>(`/students/me/enrollments${qs ? `?${qs}` : ''}`);
  },
  enrollInSection: (payload: SectionEnrollmentCreatePayload) =>
    request<SectionEnrollment>('/students/me/enrollments', { method: 'POST', body: JSON.stringify(payload) }),
  dropEnrollment: (enrollmentId: number) =>
    request<SectionEnrollment>(`/students/me/enrollments/${enrollmentId}`, { method: 'DELETE' }),

  getAvailableSections: (institutionId: number, params?: { academic_term_id?: number; department_id?: number; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.academic_term_id) q.append('academic_term_id', String(params.academic_term_id));
    if (params?.department_id) q.append('department_id', String(params.department_id));
    if (params?.search) q.append('search', params.search);
    const qs = q.toString();
    return request<AvailableSection[]>(`/institutions/${institutionId}/sections/available${qs ? `?${qs}` : ''}`);
  },

  getMyAvailability: () =>
    request<StudentAvailabilitySlot[]>('/students/me/availability'),
  saveMyAvailability: (payload: StudentAvailabilityPayload) =>
    request<StudentAvailabilitySlot[]>('/students/me/availability', { method: 'PUT', body: JSON.stringify(payload) }),

  getMyConstraints: () =>
    request<StudentConstraint[]>('/students/me/constraints'),
  createConstraint: (payload: StudentConstraintCreatePayload) =>
    request<StudentConstraint>('/students/me/constraints', { method: 'POST', body: JSON.stringify(payload) }),
  updateConstraint: (constraintId: number, payload: StudentConstraintUpdatePayload) =>
    request<StudentConstraint>(`/students/me/constraints/${constraintId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteConstraint: (constraintId: number) =>
    request<{ deleted: boolean }>(`/students/me/constraints/${constraintId}`, { method: 'DELETE' }),

  getMyPreferences: () =>
    request<StudentPreference>('/students/me/preferences'),
  updateMyPreferences: (payload: StudentPreferenceUpdatePayload) =>
    request<StudentPreference>('/students/me/preferences', { method: 'PUT', body: JSON.stringify(payload) }),

  // ── Task N4 Baseline Timetables & Course Meetings Endpoints ───────────────
  getTimetables: (institutionId: number, params?: { term_id?: number; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.term_id) q.append('term_id', String(params.term_id));
    if (params?.status) q.append('status', params.status);
    const qs = q.toString();
    return request<Timetable[]>(`/institutions/${institutionId}/timetables${qs ? `?${qs}` : ''}`);
  },
  createTimetable: (institutionId: number, payload: TimetableCreatePayload) =>
    request<Timetable>(`/institutions/${institutionId}/timetables`, { method: 'POST', body: JSON.stringify(payload) }),
  getTimetable: (institutionId: number, timetableId: number) =>
    request<Timetable>(`/institutions/${institutionId}/timetables/${timetableId}`),
  updateTimetable: (institutionId: number, timetableId: number, payload: TimetableUpdatePayload) =>
    request<Timetable>(`/institutions/${institutionId}/timetables/${timetableId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteTimetable: (institutionId: number, timetableId: number) =>
    request<{ deleted: boolean }>(`/institutions/${institutionId}/timetables/${timetableId}`, { method: 'DELETE' }),

  getMeetings: (institutionId: number, timetableId: number, params?: { section_id?: number; day_of_week?: number; room_id?: number }) => {
    const q = new URLSearchParams();
    if (params?.section_id) q.append('section_id', String(params.section_id));
    if (params?.day_of_week !== undefined) q.append('day_of_week', String(params.day_of_week));
    if (params?.room_id) q.append('room_id', String(params.room_id));
    const qs = q.toString();
    return request<CourseMeeting[]>(`/institutions/${institutionId}/timetables/${timetableId}/meetings${qs ? `?${qs}` : ''}`);
  },
  createMeeting: (institutionId: number, timetableId: number, payload: CourseMeetingCreatePayload) =>
    request<CourseMeeting>(`/institutions/${institutionId}/timetables/${timetableId}/meetings`, { method: 'POST', body: JSON.stringify(payload) }),
  getMeeting: (institutionId: number, timetableId: number, meetingId: number) =>
    request<CourseMeeting>(`/institutions/${institutionId}/timetables/${timetableId}/meetings/${meetingId}`),
  updateMeeting: (institutionId: number, timetableId: number, meetingId: number, payload: CourseMeetingUpdatePayload) =>
    request<CourseMeeting>(`/institutions/${institutionId}/timetables/${timetableId}/meetings/${meetingId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteMeeting: (institutionId: number, timetableId: number, meetingId: number) =>
    request<{ deleted: boolean }>(`/institutions/${institutionId}/timetables/${timetableId}/meetings/${meetingId}`, { method: 'DELETE' }),

  // ── Task N6 University Timetable Change & Impact Analysis ─────────────────
  previewTimetableChange: (institutionId: number, timetableId: number, payload: TimetableChangeProposal) =>
    request<TimetableImpactResponse>(`/institutions/${institutionId}/timetables/${timetableId}/changes/preview`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  applyTimetableChange: (institutionId: number, timetableId: number, payload: TimetableChangeApplyRequest) =>
    request<TimetableChangeApplyResponse>(`/institutions/${institutionId}/timetables/${timetableId}/changes/apply`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getMyAcademicSchedule: (params?: { term_id?: number }) => {
    const q = new URLSearchParams();
    if (params?.term_id) q.append('term_id', String(params.term_id));
    const qs = q.toString();
    return request<StudentAcademicSchedule>(`/students/me/schedule${qs ? `?${qs}` : ''}`);
  },

  // ── Task N5 Smart Planning Endpoints ─────────────────────────────────────
  previewSmartPlan: (payload?: SmartPlanPreviewRequest) =>
    request<SmartPlanPreviewResponse>('/students/me/planning/preview', {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }),
  applySmartPlan: (payload: PlanApplyRequest) =>
    request<PlanApplyResponse>('/students/me/planning/apply', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  revertSmartPlan: (weekStart: string) =>
    request<{ success: boolean; message: string; reverted_blocks_count: number }>(
      `/students/me/planning/revert?week_start=${encodeURIComponent(weekStart)}`,
      { method: 'DELETE' }
    ),
};

// ── Task N5 Smart Planning Interfaces ─────────────────────────────────────
export interface ProposedBlockOut {
  temp_id: string;
  title: string;
  day_of_week: number;
  day_name: string;
  date: string;
  start_time: string;
  end_time: string;
  duration_hours: number;
  study_task_id?: number | null;
  course_id?: number | null;
  type: string;
}

export interface ShiftAdjustmentOut {
  block_id: number;
  title: string;
  original_date: string;
  original_start_time: string;
  original_end_time: string;
  new_date: string;
  new_start_time: string;
  new_end_time: string;
  reason: string;
}

export interface PlanOptionSummary {
  added_study_blocks_count: number;
  moved_flexible_shifts_count: number;
  unchanged_classes_count: number;
  unchanged_fixed_commitments_count: number;
  total_study_hours: number;
  total_work_hours: number;
  is_valid: boolean;
  conflict_free: boolean;
}

export interface PlanOption {
  id: string;
  name: string;
  description: string;
  score: number;
  fit_percentage: number;
  reasons: string[];
  warnings: string[];
  trade_offs: string;
  added_blocks: ProposedBlockOut[];
  moved_blocks: ShiftAdjustmentOut[];
  summary: PlanOptionSummary;
}

export interface ScheduleContextSummary {
  enrolled_classes_count: number;
  fixed_work_shifts_count: number;
  flexible_work_shifts_count: number;
  personal_events_count: number;
  pending_tasks_count: number;
  total_study_hours_needed: number;
}

export interface SmartPlanPreviewRequest {
  target_week_start?: string;
  allow_flexible_work_moves?: boolean;
  preferred_time_of_day?: string;
  schedule_density?: string;
}

export interface SmartPlanPreviewResponse {
  week_start: string;
  week_end: string;
  context_summary: ScheduleContextSummary;
  has_feasible_solution: boolean;
  options: PlanOption[];
  blocking_issues: string[];
}

export interface PlanApplyBlock {
  title: string;
  day_of_week: number;
  date?: string;
  start_time: string;
  end_time: string;
  duration_hours: number;
  study_task_id?: number;
  course_id?: number;
  type?: string;
}

export interface PlanApplyShift {
  block_id: number;
  new_date?: string;
  new_day_of_week?: number;
  new_start_time: string;
  new_end_time: string;
}

export interface PlanApplyRequest {
  option_id: string;
  week_start?: string;
  approved_new_blocks: PlanApplyBlock[];
  approved_moved_shifts?: PlanApplyShift[];
}

export interface PlanApplyResponse {
  success: boolean;
  message: string;
  created_blocks_count: number;
  updated_shifts_count: number;
  applied_block_ids: number[];
  conflicts_detected_count: number;
  conflicts: any[];
}

// ── University Foundation Interfaces ───────────────────────────────────────
export interface Institution {
  id: number;
  name: string;
  code: string;
  description?: string | null;
  country?: string | null;
  timezone: string;
  email_domain?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InstitutionCreatePayload {
  name: string;
  code: string;
  description?: string;
  country?: string;
  timezone?: string;
  email_domain?: string;
}

export interface InstitutionUpdatePayload {
  name?: string;
  code?: string;
  description?: string | null;
  country?: string | null;
  timezone?: string;
  email_domain?: string | null;
  is_active?: boolean;
}

export interface InstitutionMembership {
  id: number;
  user_id: number;
  institution_id: number;
  role: 'student' | 'professor' | 'admin' | 'super_admin' | string;
  status: 'active' | 'inactive' | 'pending' | string;
  user_email?: string | null;
  user_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserInstitutionStatus {
  has_institution: boolean;
  institution?: Institution | null;
  membership?: InstitutionMembership | null;
}

export interface Department {
  id: number;
  institution_id: number;
  name: string;
  code: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DepartmentCreatePayload {
  name: string;
  code: string;
  description?: string;
}

export interface DepartmentUpdatePayload {
  name?: string;
  code?: string;
  description?: string | null;
  is_active?: boolean;
}

export interface AcademicTerm {
  id: number;
  institution_id: number;
  name: string;
  academic_year: string;
  term_type: 'semester' | 'trimester' | 'quarter' | 'custom' | string;
  start_date: string;
  end_date: string;
  status: 'draft' | 'upcoming' | 'active' | 'completed' | 'archived' | string;
  created_at: string;
  updated_at: string;
}

export interface AcademicTermCreatePayload {
  name: string;
  academic_year: string;
  term_type?: string;
  start_date: string;
  end_date: string;
  status?: string;
}

export interface AcademicTermUpdatePayload {
  name?: string;
  academic_year?: string;
  term_type?: string;
  start_date?: string;
  end_date?: string;
  status?: string;
}

export interface UniversityDashboardData {
  institution: Institution;
  membership: InstitutionMembership;
  department_count: number;
  member_count: number;
  course_count?: number;
  section_count?: number;
  faculty_count?: number;
  room_count?: number;
  active_term?: AcademicTerm | null;
}

// ── Academic Resources Interfaces (Task N2) ───────────────────────────────
export interface AcademicCourse {
  id: number;
  institution_id: number;
  department_id: number;
  department_name?: string | null;
  department_code?: string | null;
  code: string;
  name: string;
  description?: string | null;
  credits: number;
  level?: string | null;
  status: string;
  min_room_capacity?: number | null;
  required_room_type?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AcademicCourseCreatePayload {
  department_id: number;
  code: string;
  name: string;
  description?: string;
  credits?: number;
  level?: string;
  status?: string;
  min_room_capacity?: number;
  required_room_type?: string;
}

export interface AcademicCourseUpdatePayload {
  department_id?: number;
  code?: string;
  name?: string;
  description?: string | null;
  credits?: number;
  level?: string;
  status?: string;
  min_room_capacity?: number | null;
  required_room_type?: string | null;
}

export interface FacultyAssignment {
  id: number;
  institution_id: number;
  section_id: number;
  faculty_id: number;
  user_id: number;
  faculty_name?: string | null;
  faculty_email?: string | null;
  faculty_title?: string | null;
  role: string;
  is_primary: boolean;
  created_at: string;
}

export interface AcademicSection {
  id: number;
  institution_id: number;
  course_id: number;
  course_code?: string | null;
  course_name?: string | null;
  academic_term_id: number;
  term_name?: string | null;
  section_code: string;
  capacity: number;
  status: string;
  description?: string | null;
  instructors: FacultyAssignment[];
  created_at: string;
  updated_at: string;
}

export interface AcademicSectionCreatePayload {
  course_id: number;
  academic_term_id: number;
  section_code: string;
  capacity?: number;
  status?: string;
  description?: string;
}

export interface AcademicSectionUpdatePayload {
  section_code?: string;
  capacity?: number;
  status?: string;
  description?: string | null;
}

export interface FacultyProfile {
  id: number;
  institution_id: number;
  user_id: number;
  user_name?: string | null;
  user_email?: string | null;
  department_id?: number | null;
  department_name?: string | null;
  department_code?: string | null;
  employee_code?: string | null;
  title?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface FacultyProfileCreatePayload {
  user_id?: number;
  email?: string;
  department_id?: number;
  employee_code?: string;
  title?: string;
  status?: string;
}

export interface FacultyProfileUpdatePayload {
  department_id?: number | null;
  employee_code?: string | null;
  title?: string | null;
  status?: string;
}

export interface Room {
  id: number;
  institution_id: number;
  building: string;
  room_number: string;
  name?: string | null;
  capacity: number;
  room_type: string;
  description?: string | null;
  basic_features?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface RoomCreatePayload {
  building: string;
  room_number: string;
  name?: string;
  capacity: number;
  room_type?: string;
  description?: string;
  basic_features?: string;
  status?: string;
}

export interface RoomUpdatePayload {
  building?: string;
  room_number?: string;
  name?: string | null;
  capacity?: number;
  room_type?: string;
  description?: string | null;
  basic_features?: string | null;
  status?: string;
}

// ── Student Academics, Enrollments & Constraints Interfaces (Task N3) ───────
export interface StudentProfile {
  id: number;
  institution_id: number;
  user_id: number;
  department_id?: number | null;
  department_name?: string | null;
  student_number?: string | null;
  program?: string | null;
  year_of_study?: number | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface StudentProfileUpdatePayload {
  department_id?: number | null;
  student_number?: string | null;
  program?: string | null;
  year_of_study?: number | null;
}

export interface SectionEnrollment {
  id: number;
  institution_id: number;
  user_id: number;
  section_id: number;
  section_code?: string | null;
  course_id?: number | null;
  course_code?: string | null;
  course_name?: string | null;
  credits?: number | null;
  academic_term_id?: number | null;
  term_name?: string | null;
  instructors: string[];
  status: string;
  enrollment_date: string;
  created_at: string;
  updated_at: string;
}

export interface SectionEnrollmentCreatePayload {
  section_id: number;
}

export interface AvailableSection {
  id: number;
  institution_id: number;
  course_id: number;
  course_code: string;
  course_name: string;
  credits: number;
  academic_term_id: number;
  term_name?: string | null;
  section_code: string;
  capacity: number;
  enrolled_count: number;
  remaining_seats: number;
  is_full: boolean;
  status: string;
  description?: string | null;
  instructors: { faculty_name?: string | null; role?: string }[];
  is_enrolled: boolean;
}

export interface StudentAvailabilitySlot {
  id?: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_available: boolean;
  note?: string | null;
}

export interface StudentAvailabilityPayload {
  slots: StudentAvailabilitySlot[];
}

export interface StudentConstraint {
  id: number;
  institution_id?: number | null;
  user_id: number;
  constraint_type: string;
  name: string;
  parameters?: Record<string, any> | null;
  is_hard: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StudentConstraintCreatePayload {
  constraint_type: string;
  name: string;
  parameters?: Record<string, any> | null;
  is_hard?: boolean;
  is_active?: boolean;
}

export interface StudentConstraintUpdatePayload {
  name?: string;
  parameters?: Record<string, any> | null;
  is_hard?: boolean;
  is_active?: boolean;
}

export interface StudentPreference {
  id: number;
  institution_id?: number | null;
  user_id: number;
  preferred_time_of_day: string;
  schedule_density: string;
  max_days_per_week?: number | null;
  prefer_free_days?: number[] | null;
  break_preference: string;
  work_study_balance_weight: number;
  custom_weights?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface StudentPreferenceUpdatePayload {
  preferred_time_of_day?: string;
  schedule_density?: string;
  max_days_per_week?: number | null;
  prefer_free_days?: number[] | null;
  break_preference?: string;
  work_study_balance_weight?: number;
  custom_weights?: Record<string, any> | null;
}

export interface StudentAcademicSummary {
  institution_id: number;
  institution_name: string;
  student_number?: string | null;
  program?: string | null;
  year_of_study?: number | null;
  department_name?: string | null;
  current_term?: string | null;
  enrolled_courses_count: number;
  enrolled_credits: number;
  enrolled_sections: {
    section_id: number;
    course_code: string;
    course_name: string;
    section_code: string;
    credits: number;
    instructors: string[];
  }[];
}

// ── Task N4 Baseline Timetable & Course Meetings Interfaces ──────────────
export interface Timetable {
  id: number;
  institution_id: number;
  academic_term_id: number;
  name: string;
  description?: string | null;
  status: 'draft' | 'active' | 'archived' | string;
  created_at: string;
  updated_at: string;
  term_name?: string | null;
  academic_year?: string | null;
  meetings_count?: number;
  sections_count?: number;
}

export interface TimetableCreatePayload {
  academic_term_id: number;
  name: string;
  description?: string;
  status?: string;
}

export interface TimetableUpdatePayload {
  name?: string;
  description?: string;
  status?: string;
}

export interface CourseMeeting {
  id: number;
  institution_id: number;
  timetable_id: number;
  section_id: number;
  academic_term_id: number;
  day_of_week: number; // 0=Sun, 1=Mon, ..., 6=Sat
  start_time: string;
  end_time: string;
  room_id?: number | null;
  faculty_id?: number | null;
  meeting_type: string;
  status: string;
  created_at: string;
  updated_at: string;
  course_id?: number | null;
  course_code?: string | null;
  course_name?: string | null;
  section_code?: string | null;
  section_capacity?: number | null;
  room_building?: string | null;
  room_number?: string | null;
  room_name?: string | null;
  room_capacity?: number | null;
  faculty_name?: string | null;
  faculty_title?: string | null;
}

export interface CourseMeetingCreatePayload {
  section_id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  room_id?: number | null;
  faculty_id?: number | null;
  meeting_type?: string;
  status?: string;
}

export interface CourseMeetingUpdatePayload {
  day_of_week?: number;
  start_time?: string;
  end_time?: string;
  room_id?: number | null;
  faculty_id?: number | null;
  meeting_type?: string;
  status?: string;
}

export interface StudentAcademicSchedule {
  institution_id: number;
  institution_name?: string | null;
  academic_term_id?: number | null;
  academic_term_name?: string | null;
  enrolled_sections_count: number;
  meetings: CourseMeeting[];
}

// ── Task N6 University Timetable Editor & Impact Analysis Interfaces ───────
export interface TimetableChangeProposal {
  meeting_id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  room_id?: number | null;
  faculty_id?: number | null;
  meeting_type?: string | null;
}

export interface MeetingSnapshot {
  meeting_id: number;
  section_id: number;
  course_id?: number | null;
  course_code?: string | null;
  course_name?: string | null;
  section_code?: string | null;
  section_capacity?: number | null;
  day_of_week: number;
  day_name: string;
  start_time: string;
  end_time: string;
  room_id?: number | null;
  room_label?: string | null;
  room_capacity?: number | null;
  faculty_id?: number | null;
  faculty_name?: string | null;
  updated_at?: string | null;
}

export interface StudentImpactDetail {
  student_id: number;
  student_name: string;
  conflict_type: 'work_shift' | 'personal' | 'other_class' | 'unavailable' | 'hard_constraint' | 'none' | string;
  conflict_description: string;
  overlap_time?: string | null;
  is_new_conflict: boolean;
  is_resolved_conflict: boolean;
}

export interface ImpactSummary {
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'BLOCKED' | string;
  students_affected: number;
  new_conflicts: number;
  resolved_conflicts: number;
  work_conflicts: number;
  personal_conflicts: number;
  class_conflicts: number;
  availability_conflicts: number;
  hard_constraint_conflicts: number;
  room_issues: string[];
  faculty_issues: string[];
  blocked_reasons: string[];
}

export interface TimetableImpactResponse {
  is_blocked: boolean;
  summary: ImpactSummary;
  before: MeetingSnapshot;
  after: MeetingSnapshot;
  student_impacts: StudentImpactDetail[];
}

export interface TimetableChangeApplyRequest {
  meeting_id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  room_id?: number | null;
  faculty_id?: number | null;
  meeting_type?: string | null;
  expected_updated_at?: string | null;
}

export interface TimetableChangeApplyResponse {
  success: boolean;
  message: string;
  meeting: CourseMeeting;
  impact_summary: ImpactSummary;
  applied_at: string;
}

export const ERROR_MESSAGES: Record<string, string> = {
  SCHEDULE_LOAD_FAILED: 'Unable to load your schedule. Please try again.',
  ANALYTICS_LOAD_FAILED: "Analytics couldn't be loaded.",
  STUDY_PLAN_FAILED: "We couldn't generate study recommendations right now.",
  IMPORT_FAILED: "We couldn't process this file.",
  INVALID_REQUEST: 'The request was invalid. Please check your inputs.',
  BLOCK_NOT_FOUND: 'The requested schedule event could not be found.',
  UNAUTHORIZED: 'You are not authorized. Please log in again.',
  INTERNAL_ERROR: 'An unexpected server error occurred. Please try again.',
  section_capacity_reached: 'This section is at maximum capacity. No seats available.',
  already_enrolled: 'You are already enrolled in this section.',
  inactive_section: 'This section is not active for enrollment.',
  invalid_term: 'The academic term for this section is inactive or has concluded.',
  no_student_membership: 'You do not have a verified student membership at an active institution.',
  student_profile_not_found: 'Student institutional profile was not found.',
  tenant_mismatch: 'Cross-institution access is forbidden.',
  time_overlap: 'Availability slots cannot overlap on the same day.',
  room_conflict: 'Room is already occupied during this time.',
  faculty_conflict: 'Instructor has another overlapping meeting during this time.',
  section_conflict: 'This section already has another meeting scheduled at this time.',
  insufficient_room_capacity: 'Selected room capacity is less than section capacity.',
  invalid_time_range: 'Meeting start time must be earlier than end time.',
};

export function getErrorMessage(error: unknown, fallback: string = 'An unexpected error occurred'): string {
  if (error instanceof ApiError) {
    if (ERROR_MESSAGES[error.code]) {
      return ERROR_MESSAGES[error.code];
    }
    return error.message || fallback;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}

export interface MyDebugData {
  user_id: number;
  block_count: number;
  course_count: number;
  oldest_block: {
    id: number;
    title: string;
    type: string;
    created_at?: string | null;
  } | null;
}

/**
 * Session persistence verification test:
 * 1. Add a test block
 * 2. Sign out
 * 3. Sign back in
 * 4. Fetch /api/v1/blocks
 * 5. Assert: test block still exists
 */
export async function verifyPersistence(email: string, password: string): Promise<boolean> {
  // Ensure logged in
  const auth = await api.login(email, password);
  setAuthToken(auth.token);

  // 1. Add a test block
  const testTitle = `Test Block Persistence ${Date.now()}`;
  const created = await api.createBlock({
    title: testTitle,
    type: 'class',
    day_of_week: 1,
    start_time: '11:00:00',
    end_time: '12:00:00',
  });

  // 2. Sign out (remove token only)
  clearAuthToken();

  // 3. Sign back in
  const reAuth = await api.login(email, password);
  setAuthToken(reAuth.token);

  // 4. Fetch /api/v1/blocks
  const blocks = await api.getBlocks();

  // 5. Assert: test block still exists
  const found = blocks.find((b) => b.id === created.id || b.title === testTitle);
  if (!found) {
    throw new Error(`Session persistence failed: block '${testTitle}' not found after re-login.`);
  }

  // Cleanup test block
  await api.deleteBlock(found.id);
  return true;
}

