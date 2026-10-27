// Mirrors backend/app/schemas/*. Keep in sync when the API changes.

export type Option = "A" | "B" | "C" | "D";

export interface User {
  id: string;
  name: string;
  email: string;
  created_at?: string | null;
  is_admin?: boolean;
}

export interface AuthResponse {
  token: string;
  token_type: string;
  user: User;
  demo_notice: string;
  referral_notice?: string | null;
}

export interface Health {
  status: string;
  database: string;
  ai_provider: string;
  ai_is_mock: boolean;
}

export interface Subject {
  id: string;
  slug: string;
  title: string;
  description: string;
  icon: string;
  is_active: boolean;
  question_count: number;
  difficulty: string;
}

export interface SubjectList {
  subjects: Subject[];
  selected_subject_id: string;
}

export interface ChatMessage {
  id: string;
  user_id: string;
  subject: string;
  role: "user" | "assistant";
  content: string;
  suggested_followups: string[];
  is_mock: boolean;
  provider: string;
  created_at?: string | null;
}

export interface ChatHistory {
  messages: ChatMessage[];
  active_provider: string;
  is_mock: boolean;
}

export interface Question {
  id: string;
  subject_id: string;
  question_number: number;
  question_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  topic: string;
  difficulty: string;
}

export interface BreakdownItem {
  question_id: string;
  question_text: string;
  selected_option: string;
  correct_option: string;
  is_correct: boolean;
  explanation: string;
  topic: string;
}

export interface AssessmentResult {
  id: string;
  user_id: string;
  subject_id: string;
  subject_title?: string | null;
  score: number;
  total: number;
  percentage: number;
  proficiency_level: string;
  summary_feedback: string;
  recommended_topics: string[];
  breakdown: BreakdownItem[];
  is_mock: boolean;
  provider: string;
  created_at?: string | null;
}

export interface AttemptSummary {
  id: string;
  subject_id: string;
  subject_title: string;
  score: number;
  total: number;
  percentage: number;
  proficiency_level: string;
  created_at: string;
}

export interface Badge {
  id: string;
  badge_key: string;
  title: string;
  description: string;
  icon: string;
  awarded_at: string;
}

export interface Dashboard {
  user: User;
  selected_subject: Subject;
  has_selected_subject: boolean;
  metrics: {
    total_assessments_completed: number;
    latest_score: number | null;
    latest_total: number;
    latest_percentage: number | null;
    latest_proficiency: string;
    average_percentage: number;
    highest_score: number;
    best_percentage: number;
    chat_questions_asked: number;
    challenges_attempted: number;
    total_points: number;
  };
  recommended_next_topics: string[];
  recommendations_source: "starter" | "latest_assessment";
  recent_attempts: AttemptSummary[];
  badges: Badge[];
}

export interface DailyChallenge {
  id: string;
  title: string;
  topic: string;
  difficulty: string;
  description: string;
  code_snippet: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  points: number;
  has_completed: boolean;
  correct_option: string | null;
  explanation: string | null;
  user_submission: { submitted_answer: string; is_correct: number; points_awarded: number } | null;
}

export interface ChallengeResult {
  challenge_id: string;
  is_correct: boolean;
  points_awarded: number;
  correct_option: string;
  explanation: string;
}
