export type RouteName = 'quiz' | 'stats' | 'admin';
export type QuestionType = 'single_text' | 'multi_text' | 'ordered_multi' | 'inline_cloze';
export type ScheduleBucket =
  | 'hot'
  | 'due_review'
  | 'unseen'
  | 'one_shot_easy'
  | 'backlog_seen_correct'
  | 'not_due_recovered';

export interface ModuleUiCopy {
  question_label: string;
  answer_label: string;
  stats_title: string;
  review_title: string;
}

export interface ModuleNode {
  id: number;
  source_id: string | null;
  title: string;
  slug: string;
  full_slug: string;
  instruction: string;
  ui_copy: ModuleUiCopy;
  children: ModuleNode[];
}

export interface QuizTypeConfig {
  expected_slots?: number;
  slot_prompts?: string[];
  segments?: string[];
}

export interface SlotResult {
  index: number;
  is_correct: boolean;
  expected: string;
}

export interface QuizItem {
  id: number;
  position: number;
  question_id: number;
  module_id: number;
  module_title: string;
  module_instruction: string;
  review_flag: boolean;
  prompt: string;
  question_type: QuestionType;
  rank: number;
  type_config: QuizTypeConfig;
  submitted_answer: string[] | null;
  is_correct: boolean | null;
  score_earned?: number | null;
  score_possible?: number;
  slot_results?: SlotResult[];
  canonical_answers?: string[];
}

export interface QuizSession {
  id: number;
  module_id: number | null;
  completed_at: string | null;
  items: QuizItem[];
}

export interface SubmitAnswerResult {
  item_id: number;
  is_correct: boolean;
  score_earned: number;
  score_possible: number;
  slot_results: SlotResult[];
  canonical_answers: string[];
  session_completed: boolean;
  submitted_answer: string[];
}

export interface RecentSession {
  session_id: number;
  created_at: string;
  answered_count: number;
  correct_count: number;
  score_possible: number;
  accuracy: number;
}

export interface User {
  id: number;
  handle: string;
  display_name: string;
  created_at: string;
  disabled_at: string | null;
}

export interface QuestionSchedule {
  bucket: ScheduleBucket;
  recovery_streak: number | null;
  interval_step: number | null;
  last_incorrect_at: string | null;
  next_due_at: string | null;
}

export interface QuestionRow {
  question_id: number;
  module_id: number;
  module_title: string;
  module_full_slug: string;
  prompt: string;
  prompt_preview: string;
  question_type: QuestionType;
  rank: number;
  attempts: number;
  correct_percentage: number;
  last_asked_at: string | null;
  review_flag: boolean;
  accepted_answers: string[][];
  slot_prompts: string[];
  segments: string[];
  recent_incorrect_answers: Array<{
    submitted_answer: string[];
    answered_at: string;
  }>;
  schedule: QuestionSchedule;
}

export interface StatsResponse {
  summary: {
    total_questions: number;
    reviewed_questions: number;
    total_attempts: number;
    total_correct: number;
    total_possible: number;
    accuracy: number;
  };
  recent_sessions: RecentSession[];
  questions: QuestionRow[];
}

export interface QuestionDraftPayload {
  module_id: number;
  prompt: string;
  question_type: QuestionType;
  rank: number;
  accepted_answers: string[][];
  slot_prompts: string[];
  segments: string[];
}

export interface CreateModulePayload {
  title: string;
  parent_id: number | null;
  instruction: string;
  ui_copy?: ModuleUiCopy;
}

export interface QuestionImportUnresolvedRow {
  row_number: number;
  csv_line: string;
  issues: string[];
  inferred_type?: QuestionType | null;
}

export interface QuestionImportSession {
  session_id: number;
  expires_at: string;
  ready_to_commit: boolean;
  staged_valid_count: number;
  unresolved_rows: QuestionImportUnresolvedRow[];
  report_text: string;
  committed: boolean;
  committed_count: number;
}

export interface QuestionImportRowPayload {
  row_number: number;
  csv_line: string;
}
