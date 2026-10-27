import { get, patch, post, put } from "./client";

export interface Module {
  id: string; title: string; description: string; difficulty: string; estimated_minutes: number;
  prerequisite_module_ids: string[]; status: "locked" | "unlocked" | "completed";
  lesson_viewed?: boolean; mastery_percentage?: number | null; practice_best?: string | null;
}
export interface NextStep { action: "diagnostic" | "module" | "revision" | "reassess" | "chat"; text: string; module_id?: string }
export interface ChatSummary {
  id: string; title: string; subject_id: string | null; subject_title: string; status: "active" | "archived";
  curated: boolean; has_diagnostic: boolean; overall_progress: number; modules_total: number; modules_completed: number;
  current_module_title: string | null; updated_at?: string;
  latest_score: { score: number; total: number; percentage: number; level: string } | null;
}
export interface ChatState extends ChatSummary {
  limitation?: string | null; weaknesses: string[]; strengths: string[]; level_note?: string | null;
  roadmap: { title: string; description: string; modules: Module[] } | null; current_module: Module | null;
  assessment_history: { id: string; kind: string; score: number; total: number; percentage: number; level: string; created_at: string }[];
  improvement: { first_percentage: number; latest_percentage: number; delta: number } | null;
  unresolved_mistakes: number; next_recommendation: NextStep;
}
export interface Msg { id: string; role: "user" | "assistant"; content: string; suggested_followups: string[]; is_mock?: boolean; provider?: string; notice?: string | null }
export interface DiagQuestion { id: string; question_number: number; question_text: string; option_a: string; option_b: string; option_c: string; option_d: string; topic: string; difficulty: string }
export interface PracticeQuestion { id: string; question: string; options: string[]; difficulty: string }
export interface Practice { correct: number; total: number; percentage: number; passed: boolean; xp_awarded: number; message: string; newly_completed: boolean;
  feedback: { question_id: string; question: string; options: string[]; selected_index: number; is_correct: boolean; correct_index: number; explanation: string }[];
  next_recommendation: NextStep }
export interface RevisionItem { module_id: string; module_title: string; question: string; your_answer: string; correct_answer: string; explanation: string }
export interface Project {
  id: string; subject_id: string; subject_title: string; level: string; title: string; objective: string; skills: string[];
  milestones: string[]; deliverables: string; rubric: string[]; milestones_done: number[]; status: "not_started" | "in_progress" | "submitted";
  submission_text?: string | null; submission_url?: string | null; reflection_scores?: Record<string, number> | null; evaluation_note?: string | null;
}
export interface Notification { id: string; kind: string; title: string; body: string; link: string | null; read_at: string | null; created_at: string }
export interface Prefs { battles: boolean; achievements: boolean; reminders: boolean; projects: boolean; quiet_start: string | null; quiet_end: string | null }
export interface Cert { verification_id: string; cert_type: string; title: string; description: string; issued_at?: string; recipient_name?: string }
export interface SkillProfile {
  subjects: { chat_id: string; subject_title: string; curated: boolean; level: string | null; latest_percentage: number | null;
    improvement: { delta: number } | null; weaknesses: string[]; modules_completed: number; modules_total: number;
    mastered_topics: { title: string; mastery_percentage: number | null }[] }[];
  projects: { id: string; title: string; level: string; subject_title: string; rubric_total: number; rubric_max: number; evidence_type: string }[];
  gamification: { total_xp: number; level: number; title: string; progress_percentage: number; next_threshold: number;
    streak: { current_streak: number; longest_streak: number }; battle_stats: { wins: number; losses: number; ties: number; total_battles: number } };
  badges: { badge_key: string; title: string; description: string }[]; certificates: Cert[]; disclaimer: string;
}

export const learn = {
  catalog: () => get<{ subjects: { id: string; title: string; modules: number }[] }>("/learn/catalog"),
  chats: (archived = false) => get<{ chats: ChatSummary[] }>(`/learn/chats?include_archived=${archived}`),
  createChat: (b: { subject_id?: string; custom_subject?: string; title?: string }) => post<ChatState>("/learn/chats", b),
  chat: (id: string) => get<ChatState>(`/learn/chats/${id}`),
  patchChat: (id: string, b: { title?: string; archived?: boolean }) => patch<ChatState>(`/learn/chats/${id}`, b),
  messages: (id: string) => get<{ messages: Msg[] }>(`/learn/chats/${id}/messages`),
  send: (id: string, message: string, mode: string) => post<Msg>(`/learn/chats/${id}/messages`, { message, mode }),
  diagQuestions: (id: string) => get<{ questions: DiagQuestion[] }>(`/learn/chats/${id}/assessment`),
  submitDiag: (id: string, answers: Record<string, string>) =>
    post<{ id: string; kind: string; score: number; total: number; percentage: number; proficiency_level: string; summary_feedback: string; is_mock: boolean }>(`/learn/chats/${id}/assessment`, { answers }),
  module: (id: string, mid: string) => get<{ module: Module; lesson: string; questions: PracticeQuestion[]; pass_rule: string }>(`/learn/chats/${id}/modules/${mid}`),
  practice: (id: string, mid: string, answers: Record<string, number>) => post<Practice>(`/learn/chats/${id}/modules/${mid}/practice`, { answers }),
  revision: (id: string) => get<{ items: RevisionItem[]; priorities: { module_title: string; missed: number }[]; suggestion: string }>(`/learn/chats/${id}/revision`),
  projects: () => get<{ projects: Project[] }>("/learn/projects"),
  milestone: (pid: string, index: number, done: boolean) => post<Project>(`/learn/projects/${pid}/milestones`, { index, done }),
  submitProject: (pid: string, b: { text: string; url?: string; rubric_scores: Record<string, number> }) => post<Project>(`/learn/projects/${pid}/submit`, b),
  skillProfile: () => get<SkillProfile>("/learn/skill-profile"),
};

export const notifications = {
  list: () => get<{ notifications: Notification[]; unread: number }>("/notifications"),
  unread: () => get<{ unread: number }>("/notifications/unread-count"),
  read: (id?: string) => post<{ unread: number }>(`/notifications/read${id ? `?notification_id=${encodeURIComponent(id)}` : ""}`),
  prefs: () => get<Prefs>("/notifications/preferences"),
  savePrefs: (p: Prefs) => put<Prefs>("/notifications/preferences", p),
};

// ---- compete / growth (existing backend modules) ----
export interface Invitation { id: string; sender_id: string; sender_name: string; recipient_id: string; recipient_name: string; subject_id: string; status: string; battle_id: string | null }
export interface BattleSummary {
  id: string; status: string; subject_id?: string; opponent_name: string; you_ready: boolean; opponent_ready: boolean;
  outcome?: string | null; you_won: boolean; scores?: { user_id: string; correct: number; answered: number; total: number }[] | null;
  created_at?: string; completed_at?: string | null;
}
export interface BattleView {
  battle_id: string; status: string; viewer_user_id: string; opponent_display_name: string; viewer_submitted: boolean; opponent_submitted: boolean;
  time_limit_seconds: number; started_at?: string | null;
  questions: { position: number; question_id: string; question_text: string; option_a: string; option_b: string; option_c: string; option_d: string; topic: string }[];
  result: { outcome: string; winner_user_id: string | null; scores: { user_id: string; correct: number; answered: number; total: number }[] } | null;
  review: { position: number; question_id: string; correct_option: string; explanation: string; answers: Record<string, string> }[];
}
export const battles = {
  invite: (recipient_identifier: string, subject_id: string) => post<{ invitation?: Invitation }>("/battles/invite", { recipient_identifier, subject_id }),
  invitations: () => get<Invitation[]>("/battles/invitations"),
  respond: (invitation_id: string, accept: boolean) => post<{ battle_id?: string; status?: string }>("/battles/invite/respond", { invitation_id, accept }),
  mine: () => get<BattleSummary[]>("/battles/my-battles"),
  view: (id: string) => get<BattleView>(`/battles/${id}`),
  ready: (id: string) => post<unknown>(`/battles/${id}/ready`, { battle_id: id }),
  submit: (id: string, answers: Record<string, string>, secs: number) => post<unknown>(`/battles/${id}/submit`, { battle_id: id, answers, time_taken_seconds: secs }),
  rematch: (id: string) => post<{ invitation?: Invitation }>(`/battles/${id}/rematch`, { battle_id: id }),
  leaderboard: () => get<{ user_id: string; name: string; total_battles: number; wins: number; losses: number; ties: number }[]>("/battles/leaderboard/ranking"),
};

export interface Org { id: string; name: string; org_type: string; description: string; is_verified: number | boolean; created_by_user_id: string }
export interface Comp {
  id: string; title: string; description: string; host_type: string; org_name?: string; difficulty: string; status: string;
  start_time: string; end_time: string; created_by_user_id?: string; questions: { id: string; question_text: string; option_a: string; option_b: string; option_c: string; option_d: string }[];
  user_submission?: { score: number; total_questions: number; percentage: number; rank: number } | null;
}
export const comps = {
  orgs: () => get<Org[]>("/competitions/organizations"),
  createOrg: (b: { name: string; org_type: string; description: string; domain?: string }) => post<{organization:Org}>("/competitions/organizations", b).then(r=>r.organization),
  list: () => get<Comp[]>("/competitions/list"),
  one: (id: string) => get<Comp>(`/competitions/${id}`),
  create: (b: unknown) => post<{competition:Comp}>("/competitions/create", b).then(r=>r.competition),
  submit: (id: string, answers: Record<string, string>, secs: number) =>
    post<{ score: number; total_questions: number; percentage: number; xp_awarded: number }>(`/competitions/${id}/submit`, { answers, time_taken_seconds: secs }),
  leaderboard: (id: string) => get<{ rank: number; user_name: string; score: number; total_questions: number; percentage: number }[]>(`/competitions/${id}/leaderboard`),
  dashboard: (id: string) => get<{ analytics: Record<string, number>; standings?: unknown[]; [k: string]: unknown }>(`/competitions/${id}/dashboard`),
  announce: (id: string) => post<{ status: string }>(`/competitions/${id}/announce-winners`),
};

export interface XpEvent { id: string; points_delta: number; reason: string; source_type: string; created_at: string }
export interface Reward { id: string; title: string; description: string; category: string; xp_cost: number; stock: number; can_afford: boolean; shortfall: number; is_demo?: boolean; fulfillment_note?: string }
export interface RefDash { referral_code: string; share_url: string; total_invited: number; pending_referrals: number; successful_referrals: number;
  xp_earned_from_referrals: number; reward_rule: string; referrer_xp: number; referee_xp: number;
  referral_history: { id: string; referee_name: string; status: string; created_at: string }[] }
export const growth = {
  profile: () => get<{ total_xp: number; level: number; title: string; progress_percentage: number; next_threshold: number; streak: { current_streak: number } }>("/gamification/profile"),
  ledger: () => get<XpEvent[]>("/gamification/ledger"),
  rewards: () => get<Reward[]>("/gamification/rewards"),
  redeem: (reward_id: string) => post<unknown>("/gamification/rewards/redeem", { reward_id }),
  referrals: () => get<RefDash>("/referrals/dashboard"),
  applyReferral: (referral_code: string) => post<{ message: string }>("/referrals/apply", { referral_code }),
  verify: (id: string) => get<{ is_valid: boolean; title?: string; recipient_name?: string; cert_type?: string; description?: string; issued_at?: string; verification_id?: string; error?: string }>(`/certificates/verify/${encodeURIComponent(id)}`),
  certHtml: (id: string) => get<{ html: string }>(`/certificates/${encodeURIComponent(id)}/download`),
  share: (id: string) => get<{ share_text: string; verification_url: string }>(`/certificates/${encodeURIComponent(id)}/share`),
  challengeLeaderboard: () => get<{ rank?: number; user_id: string; display_name?: string; name?: string; total_points: number }[]>("/challenges/leaderboard"),
  challengeHistory: () => get<{ challenge_id: string; title?: string; is_correct: number | boolean; points_awarded: number; completed_date?: string }[]>("/challenges/history"),
  challengeStreak: () => get<{ current_streak: number; longest_streak: number }>("/challenges/streak"),
  adminAnalytics: () => get<Record<string, Record<string, number>>>("/admin/competitions/analytics"),
  adminVerifyOrg: (id: string, is_verified: boolean) => post<unknown>(`/admin/competitions/organizations/${id}/verify`, { is_verified }),
  auditReferrals: () => get<unknown[]>("/admin/competitions/audit/referrals"),
  auditRewards: () => get<unknown[]>("/admin/competitions/audit/rewards"),
};
