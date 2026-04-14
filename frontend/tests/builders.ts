import type {
  ModuleNode,
  QuestionImportResult,
  QuestionImportReviewRow,
  QuestionImportRowPayload,
  QuestionRow,
  QuestionSchedule,
  QuizItem,
  QuizSession,
  RecentSession,
  StatsResponse,
  User
} from '../src/lib/types';

export function buildUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    handle: 'user-a',
    display_name: 'User A',
    created_at: '2026-04-05T10:00:00Z',
    ...overrides
  };
}

export function buildModuleNode(
  overrides: Partial<ModuleNode> & {
    children?: ModuleNode[];
  } = {}
): ModuleNode {
  return {
    id: 1,
    title: 'Biology',
    slug: 'biology',
    full_slug: 'biology',
    instruction: '',
    children: overrides.children ?? [],
    ...overrides
  };
}

export function buildQuizItem(overrides: Partial<QuizItem> = {}): QuizItem {
  return {
    id: 1,
    position: 1,
    question_id: 1,
    module_id: 1,
    module_instruction: '',
    review_flag: false,
    prompt: 'Question prompt',
    question_type: 'single_text',
    rank: 1,
    type_config: overrides.type_config ?? { expected_slots: 1 },
    submitted_answer: null,
    is_correct: null,
    ...overrides
  };
}

export function buildQuizSession(overrides: Partial<QuizSession> = {}): QuizSession {
  return {
    id: 1,
    module_id: null,
    completed_at: null,
    items: overrides.items ?? [],
    ...overrides
  };
}

export function buildRecentSession(overrides: Partial<RecentSession> = {}): RecentSession {
  return {
    session_id: 1,
    created_at: '2026-04-05T10:00:00Z',
    answered_count: 1,
    correct_count: 1,
    score_possible: 1,
    accuracy: 1,
    ...overrides
  };
}

export function buildQuestionSchedule(overrides: Partial<QuestionSchedule> = {}): QuestionSchedule {
  return {
    bucket: 'unseen',
    logical_bucket: 'unseen',
    recovery_streak: null,
    interval_step: null,
    last_incorrect_at: null,
    next_due_at: null,
    retry_pending: false,
    ...overrides
  };
}

export function buildQuestionRow(
  overrides: Partial<QuestionRow> & {
    schedule?: Partial<QuestionSchedule>;
  } = {}
): QuestionRow {
  const { schedule, ...questionOverrides } = overrides;
  return {
    question_id: 1,
    module_id: 1,
    module_full_slug: 'biology',
    prompt: 'Question prompt',
    prompt_preview: 'Question prompt',
    question_type: 'single_text',
    rank: 1,
    attempts: 0,
    correct_percentage: 0,
    first_asked_at: null,
    last_asked_at: null,
    review_flag: false,
    accepted_answers: [['answer']],
    segments: [],
    recent_incorrect_answers: [],
    ...questionOverrides,
    schedule: buildQuestionSchedule(schedule)
  };
}

export function buildStatsResponse(
  overrides: Partial<StatsResponse> & {
    summary?: Partial<StatsResponse['summary']>;
    recent_sessions?: RecentSession[];
    questions?: QuestionRow[];
  } = {}
): StatsResponse {
  const { summary, recent_sessions, questions, ...statsOverrides } = overrides;
  return {
    summary: {
      total_questions: 0,
      reviewed_questions: 0,
      total_attempts: 0,
      total_correct: 0,
      total_possible: 0,
      accuracy: 0,
      ...summary
    },
    recent_sessions: recent_sessions ?? [],
    questions: questions ?? [],
    ...statsOverrides
  };
}

export function buildImportRow(overrides: Partial<QuestionImportRowPayload> = {}): QuestionImportRowPayload {
  return {
    row_number: 1,
    qml_line: 'mot [against]',
    ...overrides
  };
}

export function buildImportReviewRow(overrides: Partial<QuestionImportReviewRow> = {}): QuestionImportReviewRow {
  return {
    row_number: 1,
    qml_line: 'mot [against]',
    status: 'duplicate',
    status_text: 'This prompt already exists in the target leaf.',
    editable: true,
    blocking: false,
    target_module_full_slug: null,
    current_answer_blocks: ['against'],
    imported_answer_blocks: ['toward'],
    matched_questions: [],
    ...overrides
  };
}

export function buildImportResult(
  overrides: Partial<QuestionImportResult> & {
    rows?: QuestionImportRowPayload[];
    review_rows?: QuestionImportReviewRow[];
    committable_row_numbers?: number[];
  } = {}
): QuestionImportResult {
  const { rows, review_rows, committable_row_numbers, ...resultOverrides } = overrides;
  return {
    ready_to_commit: false,
    rows: rows ?? [],
    valid_row_count: 0,
    committable_row_numbers: committable_row_numbers ?? [],
    exact_duplicate_count: 0,
    review_rows: review_rows ?? [],
    report_text: '',
    committed: false,
    committed_count: 0,
    ...resultOverrides
  };
}
