export const API_BASE = "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: HeadersInit = { ...(options?.headers || {}) };
  if (options?.body && !(options.body instanceof FormData)) {
    (headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as { detail?: string | { msg?: string }[] }).detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join(", ")
          : res.statusText || "Request failed";
    throw new ApiError(message);
  }
  return data as T;
}

export type SkillEntry = {
  name: string;
  skill_id?: string;
  source?: string;
  level?: string;
  proficiency?: number;
  required?: number;
  evidence?: string[];
};

export type CompletedCourse = { id: string; title: string; skills: string[] };

export type Learner = {
  id: string;
  email: string;
  name: string;
  experience_level: string;
  interests: string[];
  goal: string;
  learning_preference: string;
  hours_per_week: number;
  hours_per_day?: number;
  duration_months?: number;
  budget?: string;
  skills: SkillEntry[];
  target_role: string;
  skill_gaps: string[] | { skill_id?: string; name?: string; current?: number; required?: number }[];
  streak_days?: number;
  last_active_date?: string;
  active_skill_id?: string;
  completed_courses: CompletedCourse[];
};

export type PathItem = {
  id: string;
  catalog_id: string;
  order: number;
  item_type: string;
  skill_id?: string;
  topic_id?: string;
  resources?: {
    title: string;
    url: string;
    type?: string;
    why?: string;
    rank?: number;
    about?: string;
    rating?: string;
    rating_source?: string;
  }[];
  phase?: string;
  week?: number;
  title: string;
  provider: string;
  url: string;
  hours: number;
  level: string;
  cost?: string;
  format?: string;
  skills: string[];
  description: string;
  milestone_title: string;
  prereq_ids: string[];
  why: string;
  status: string;
  feedback: string;
  locked: boolean;
};

export type LearningPath = {
  id: string | null;
  learner_id: string;
  goal: string;
  status: string;
  items: PathItem[];
  phases?: { name: string; items: PathItem[] }[];
  next_action: PathItem | null;
};

export type ChatSession = {
  id: string;
  skill_id?: string;
  title: string;
  created_at?: string | null;
  updated_at?: string | null;
  preview?: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | string;
  content: string;
  created_at?: string | null;
  skill_id?: string;
  session_id?: string;
};

export type GapRow = {
  skill_id: string;
  name: string;
  current: number;
  required: number;
  gap: number;
  importance: number;
  priority: number;
  prerequisites: string[];
};

export type DashboardData = {
  learner: Learner;
  path: LearningPath | null;
  enrolled_skills?: {
    id: string;
    name: string;
    overall_proficiency: number;
    confidence: number;
    status: string;
    active: boolean;
    next_title?: string | null;
    items_done?: number;
    items_total?: number;
    path_progress_percent?: number;
  }[];
  active_skill_id?: string;
  skills_count: number;
  skills: string[];
  skill_bars: SkillEntry[];
  skills_mastered: number;
  skills_total: number;
  path_progress_percent: number;
  items_done: number;
  items_total: number;
  projects_done: number;
  projects_total: number;
  milestones_done: number;
  milestones_total: number;
  streak_days: number;
  next_action: PathItem | null;
  next_skill: GapRow | null;
  recent_completions: PathItem[];
  goal: string;
  target_role: string;
  gaps: GapRow[];
  badges: string[];
  path_for_active_skill?: boolean;
  last_active_date?: string;
  active_skill?: {
    id: string;
    name: string;
    overall_proficiency: number;
    confidence: number;
    status: string;
    active: boolean;
  };
};

export type QuizItem = {
  id: string;
  order: number;
  skill_id: string;
  skill_name?: string;
  topic_id?: string;
  difficulty: string;
  question: string;
  options: string[];
};

export type Assessment = {
  id: string;
  learner_id: string;
  goal: string;
  status: string;
  items: QuizItem[];
  current_item?: QuizItem | null;
  next_item?: QuizItem | null;
  answered: number;
  total: number;
  correct?: boolean;
  done?: boolean;
};

export type GraphPayload = {
  skill?: { id: string; name: string };
  nodes: { id: string; name: string; proficiency: number; required: number; importance: number; status?: string; kind?: string; confidence?: number; parent_id?: string }[];
  edges: { source: string; target: string; relation: string }[];
};

export const api = {
  login: (email: string, name?: string) =>
    request<Learner>("/api/learner/login", {
      method: "POST",
      body: JSON.stringify({ email, name }),
    }),
  getLearner: (id: string) => request<Learner>(`/api/learner/${id}`),
  updateLearner: (id: string, payload: Partial<Learner>) =>
    request<Learner>(`/api/learner/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  addCourse: (id: string, title: string, skills: string[]) =>
    request<Learner>(`/api/learner/${id}/courses`, {
      method: "POST",
      body: JSON.stringify({ title, skills }),
    }),
  fromSemester: (id: string, skills: string[], semester?: string) =>
    request<Learner>(`/api/learner/${id}/from-semester`, {
      method: "POST",
      body: JSON.stringify({ skills, semester }),
    }),
  fromRoleFit: (
    id: string,
    payload: { target_role: string; missing_skills: string[]; strengths: string[]; role_fit_percentage?: number }
  ) =>
    request<Learner>(`/api/learner/${id}/from-role-fit`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getPath: (learnerId: string) => request<LearningPath>(`/api/path/${learnerId}`),
  generatePath: (learnerId: string) =>
    request<LearningPath>("/api/path/generate", {
      method: "POST",
      body: JSON.stringify({ learner_id: learnerId }),
    }),
  morePathResources: (learnerId: string, topicId: string) =>
    request<LearningPath>("/api/path/resources", {
      method: "POST",
      body: JSON.stringify({ learner_id: learnerId, topic_id: topicId }),
    }),
  adaptPath: (learnerId: string) =>
    request<LearningPath>("/api/path/adapt", {
      method: "POST",
      body: JSON.stringify({ learner_id: learnerId }),
    }),
  patchItem: (itemId: string, payload: { status?: string; feedback?: string }) =>
    request<LearningPath>(`/api/path/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  dashboard: (learnerId: string) => request<DashboardData>(`/api/dashboard/${learnerId}`),
  chat: (learnerId: string, message: string, skillId?: string, sessionId?: string) =>
    request<{
      reply: string;
      intent: string;
      actions?: string[];
      learner: Learner;
      path: LearningPath | null;
      messages: ChatMessage[];
      session_id?: string;
      session?: ChatSession;
    }>("/api/assistant/chat", {
      method: "POST",
      body: JSON.stringify({
        learner_id: learnerId,
        message,
        ...(skillId !== undefined ? { skill_id: skillId } : {}),
        ...(sessionId ? { session_id: sessionId } : {}),
      }),
    }),
  chatHistory: (learnerId: string, skillId?: string, sessionId?: string) => {
    const params = new URLSearchParams();
    if (skillId !== undefined) params.set("skill_id", skillId);
    if (sessionId) params.set("session_id", sessionId);
    const q = params.toString();
    return request<{ messages: ChatMessage[]; skill_id?: string; session_id?: string }>(
      `/api/assistant/history/${learnerId}${q ? `?${q}` : ""}`
    );
  },
  chatSessions: (learnerId: string, skillId?: string) =>
    request<{ sessions: ChatSession[] }>(
      `/api/assistant/sessions/${learnerId}${skillId !== undefined ? `?skill_id=${encodeURIComponent(skillId)}` : ""}`
    ),
  createChatSession: (learnerId: string, skillId?: string) =>
    request<ChatSession>("/api/assistant/sessions", {
      method: "POST",
      body: JSON.stringify({ learner_id: learnerId, skill_id: skillId || "" }),
    }),
  gaps: (learnerId: string) => request<{ gaps: GapRow[]; goal: string; target_role: string }>(`/api/skills/gaps/${learnerId}`),
  graph: (learnerId: string) => request<GraphPayload>(`/api/skills/graph/${learnerId}`),
  generateAssessment: (learnerId: string, skillId?: string) =>
    request<Assessment>("/api/assessment/generate", {
      method: "POST",
      body: JSON.stringify({ learner_id: learnerId, skill_id: skillId }),
    }),
  assessmentHistory: (learnerId: string) =>
    request<{
      assessments: {
        id: string;
        skill_id: string;
        skill_name?: string;
        goal: string;
        status: string;
        created_at?: string | null;
        answered: number;
        total: number;
      }[];
    }>(`/api/assessment/history/${learnerId}`),
  resolveSkill: (name: string, learnerId?: string) =>
    request<{ skill: { id: string; name: string }; topics: { id: string; name: string }[]; learner?: Learner }>(
      "/api/skills/resolve",
      { method: "POST", body: JSON.stringify({ name, learner_id: learnerId }) }
    ),
  learnerSkills: (learnerId: string) =>
    request<{ skills: { id: string; name: string; overall_proficiency: number; status: string; active: boolean }[]; active_skill_id: string }>(
      `/api/learner/${learnerId}/skills`
    ),
  setActiveSkill: (learnerId: string, skillId: string) =>
    request<{ active_skill_id: string; learner: Learner }>(`/api/learner/${learnerId}/active-skill`, {
      method: "PUT",
      body: JSON.stringify({ skill_id: skillId }),
    }),
  semesterRoadmap: (learnerId: string) =>
    request<{
      profile: { institution: string; branch: string; semester: string } | null;
      subjects: { subject: string; topic_ids: string[]; resources?: { title: string; url: string; type?: string; about?: string; why?: string; topic_id?: string }[] }[];
    }>(`/api/semester/roadmap/${learnerId}`),
  roleFitGaps: (learnerId: string, targetRole: string, missingSkills: string[]) =>
    request<{
      target_role: string;
      gaps: { skill_id: string; name: string; current: number; required: number; priority: string }[];
      active_skill_id: string;
    }>("/api/role-fit/gap-analysis", {
      method: "POST",
      body: JSON.stringify({ learner_id: learnerId, target_role: targetRole, missing_skills: missingSkills }),
    }),
  answerAssessment: (assessmentId: string, itemId: string, answer: string) =>
    request<
      Assessment & {
        explanation?: string;
        learner?: Learner;
        path?: LearningPath | null;
      }
    >("/api/assessment/answer", {
      method: "POST",
      body: JSON.stringify({ assessment_id: assessmentId, item_id: itemId, answer }),
    }),
  submitAssessment: (assessmentId: string, answers: { item_id: string; answer: string }[]) =>
    request<{
      assessment: Assessment;
      skill_scores: Record<string, number>;
      skipped_skills: string[];
      focus_skills: string[];
      learner: Learner;
      path: LearningPath | null;
      explanation: string;
    }>("/api/assessment/submit", {
      method: "POST",
      body: JSON.stringify({ assessment_id: assessmentId, answers }),
    }),
};
