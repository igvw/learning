export type RouteName = 'quiz' | 'stats' | 'admin';
export type QuestionType = 'single_text' | 'multi_text' | 'ordered_multi' | 'inline_cloze' | 'computed_text';
export type UserRole = 'admin' | 'user' | 'demo';
export type ModerationStatus = 'verified' | 'pending' | 'changes_requested' | 'rejected';
export type ProposalStatus = 'pending' | 'changes_requested' | 'approved' | 'rejected';
export type ModerationKind = 'module' | 'question' | 'revision';
export type ScheduleBucket =
  | 'hot0'
  | 'hot1'
  | 'hot1_sit_out'
  | 'due_review'
  | 'cooling'
  | 'unseen'
  | 'mastery';
export type LogicalBucket =
  | 'review'
  | 'unseen'
  | '1h'
  | '3h'
  | '6h'
  | '12h'
  | '1d'
  | '3d'
  | '7d'
  | '14d'
  | '30d'
  | '60d'
  | 'mastery';

export interface ModuleNode {
  id: number;
  title: string;
  slug: string;
  full_slug: string;
  instruction: string;
  admin_verified: boolean;
  moderation_status: ModerationStatus;
  created_by_user_id: number | null;
  creator_display_name: string | null;
  children: ModuleNode[];
}

export interface AuthActor {
  id: number | null;
  handle: string;
  display_name: string;
  role: UserRole;
  is_demo: boolean;
  created_at: string | null;
}

export interface BootstrapAdminPayload {
  handle: string;
  display_name: string;
  password: string;
}

export interface LoginPayload {
  handle: string;
  password: string;
}

export interface ViewerProposalState {
  proposal_id: number;
  status: ProposalStatus;
  delete_requested: boolean;
  admin_review_note: string;
}

export interface QuizTypeConfig {
  expected_slots?: number;
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
  module_instruction: string;
  review_flag: boolean;
  prompt: string;
  question_type: QuestionType;
  rank: number;
  type_config: QuizTypeConfig;
  admin_verified: boolean;
  moderation_status: ModerationStatus;
  created_by_user_id: number | null;
  creator_display_name: string | null;
  viewer_proposal?: ViewerProposalState | null;
  submitted_answer: string[] | null;
  is_correct: boolean | null;
  score_earned?: number | null;
  score_possible?: number;
  slot_results?: SlotResult[];
  canonical_answers?: string[];
  default_answers?: string[];
  accepted_answer_groups?: string[][];
  matched_default_answers?: boolean[];
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
  default_answers: string[];
  accepted_answer_groups: string[][];
  matched_default_answers: boolean[];
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
  role: UserRole;
  created_at: string;
}

export interface CreateUserPayload {
  handle: string;
  display_name: string;
  role: Extract<UserRole, 'admin' | 'user'>;
  password: string;
}

export interface UpdateUserRolePayload {
  role: Extract<UserRole, 'admin' | 'user'>;
}

export interface HealthResponse {
  status: string;
  instance_key: string;
  bootstrap_required: boolean;
}

export interface QuestionSchedule {
  bucket: ScheduleBucket;
  logical_bucket: LogicalBucket;
  recovery_streak: number | null;
  interval_step: number | null;
  last_incorrect_at: string | null;
  next_due_at: string | null;
}

export interface QuestionRow {
  question_id: number;
  module_id: number;
  module_full_slug: string;
  prompt: string;
  prompt_preview: string;
  question_type: QuestionType;
  rank: number;
  attempts: number;
  correct_percentage: number;
  first_asked_at: string | null;
  last_asked_at: string | null;
  review_flag: boolean;
  admin_verified: boolean;
  moderation_status: ModerationStatus;
  created_by_user_id: number | null;
  creator_display_name: string | null;
  viewer_proposal?: ViewerProposalState | null;
  accepted_answers: string[][];
  segments: string[];
  recent_incorrect_answers: Array<{
    answer_text: string;
    count: number;
    latest_answered_at: string;
  }>;
  schedule: QuestionSchedule;
}

export interface StatsResponse {
  schedule_timezone: string;
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
  segments: string[];
}

export interface QuestionMutationResult {
  question_id: number;
  proposal_id: number | null;
  admin_verified: boolean;
  moderation_status: ModerationStatus;
  delete_requested: boolean;
}

export interface QuestionReviewFlagResult {
  question_id: number;
  review_flag: boolean;
}

export interface CreateModulePayload {
  title: string;
  parent_id: number | null;
  instruction: string;
}

export interface UpdateModulePayload {
  title: string;
  instruction: string;
}

export interface UpdateUserPasswordPayload {
  password: string;
}

export interface ModerationActionPayload {
  action: 'approve' | 'reject' | 'changes_requested';
  note: string;
}

export interface BulkModerationResult {
  succeeded: number;
  failed: number;
}

export interface PendingModule {
  id: number;
  title: string;
  full_slug: string;
  parent_id: number | null;
  instruction: string;
  admin_verified: boolean;
  moderation_status: ModerationStatus;
  created_by_user_id: number | null;
  creator_display_name: string | null;
  admin_review_note: string;
}

export interface PendingQuestion {
  question_id: number;
  module_id: number;
  module_full_slug: string;
  prompt: string;
  question_type: QuestionType;
  rank: number;
  accepted_answers: string[][];
  segments: string[];
  admin_verified: boolean;
  moderation_status: ModerationStatus;
  created_by_user_id: number | null;
  creator_display_name: string | null;
  admin_review_note: string;
}

export interface QuestionRevisionProposal {
  proposal_id: number;
  question_id: number;
  proposer_user_id: number;
  proposer_display_name: string | null;
  status: ProposalStatus;
  delete_requested: boolean;
  admin_review_note: string;
  module_id: number;
  module_full_slug: string;
  current_prompt: string;
  current_question_type: QuestionType;
  current_accepted_answers: string[][];
  current_segments: string[];
  proposed_prompt: string;
  proposed_question_type: QuestionType;
  proposed_accepted_answers: string[][];
  proposed_segments: string[];
}

export interface ModerationQueue {
  pending_modules: PendingModule[];
  pending_questions: PendingQuestion[];
  pending_revisions: QuestionRevisionProposal[];
}

export interface MyContributions {
  modules: PendingModule[];
  questions: PendingQuestion[];
  revisions: QuestionRevisionProposal[];
}

export type QuestionImportReviewStatus = 'invalid' | 'duplicate' | 'relocation' | 'info' | 'conflict';

export interface QuestionImportMatchedQuestion {
  question_id?: number | null;
  module_id?: number | null;
  module_full_slug: string;
  qml_line: string;
  answer_blocks: string[];
}

export interface QuestionImportReviewRow {
  row_number: number;
  qml_line: string;
  status: QuestionImportReviewStatus;
  status_text: string;
  editable: boolean;
  blocking: boolean;
  target_module_full_slug?: string | null;
  current_answer_blocks: string[];
  imported_answer_blocks: string[];
  matched_questions: QuestionImportMatchedQuestion[];
}

export interface QuestionImportResult {
  ready_to_commit: boolean;
  rows: QuestionImportRowPayload[];
  valid_row_count: number;
  committable_row_numbers?: number[];
  exact_duplicate_count: number;
  review_rows: QuestionImportReviewRow[];
  report_text: string;
  committed: boolean;
  committed_count: number;
}

export interface QuestionImportRowPayload {
  row_number: number;
  qml_line: string;
}
