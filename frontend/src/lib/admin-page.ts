import type {
  LogicalBucket,
  ModuleNode,
  PendingQuestion,
  QuestionRevisionProposal,
  QuestionRow,
  QuestionType,
  ScheduleBucket
} from './types';

export type FlatModule = {
  id: number;
  title: string;
  full_slug: string;
  instruction: string;
  depth: number;
  isLeaf: boolean;
  admin_verified: boolean;
  created_by_user_id: number | null;
};

export type PendingQuestionGroup = {
  moduleFullSlug: string;
  moduleId: number;
  questions: PendingQuestion[];
};

export type RevisionChangedField = 'prompt' | 'question_type' | 'answers' | 'segments';
export type PendingRevisionPrimaryKind = 'delete' | 'type' | 'prompt' | 'answer_segment';

export type PendingRevisionEntry = {
  proposal: QuestionRevisionProposal;
  changedFields: RevisionChangedField[];
  primaryKind: PendingRevisionPrimaryKind;
};

export type PendingRevisionModuleGroup = {
  moduleFullSlug: string;
  moduleId: number;
  revisions: PendingRevisionEntry[];
};

export type PendingRevisionSection = {
  key: PendingRevisionPrimaryKind;
  title: string;
  revisions: PendingRevisionEntry[];
};

export type RevisionSeedSource = 'current' | 'proposed';

export function flattenModules(nodes: ModuleNode[], depth = 0): FlatModule[] {
  return nodes.flatMap((node) => [
    {
      id: node.id,
      title: node.title,
      full_slug: node.full_slug,
      instruction: node.instruction,
      depth,
      isLeaf: node.children.length === 0,
      admin_verified: node.admin_verified,
      created_by_user_id: node.created_by_user_id
    },
    ...flattenModules(node.children, depth + 1)
  ]);
}

export function reviewBadge(status: string, verified: boolean): string {
  return verified ? 'Verified' : status.replace('_', ' ');
}

export function groupPendingQuestionsByModule(questions: PendingQuestion[]): PendingQuestionGroup[] {
  const grouped = new Map<string, PendingQuestionGroup>();

  for (const question of questions) {
    const existing = grouped.get(question.module_full_slug);
    if (existing) {
      existing.questions.push(question);
      continue;
    }
    grouped.set(question.module_full_slug, {
      moduleFullSlug: question.module_full_slug,
      moduleId: question.module_id,
      questions: [question]
    });
  }

  return [...grouped.values()];
}

function answerGroupsEqual(left: string[][], right: string[][]): boolean {
  if (left.length !== right.length) {
    return false;
  }
  return left.every((group, index) => {
    const otherGroup = right[index] ?? [];
    if (group.length !== otherGroup.length) {
      return false;
    }
    return group.every((value, valueIndex) => value === otherGroup[valueIndex]);
  });
}

function stringListEqual(left: string[], right: string[]): boolean {
  if (left.length !== right.length) {
    return false;
  }
  return left.every((value, index) => value === right[index]);
}

export function revisionChangedFields(proposal: QuestionRevisionProposal): RevisionChangedField[] {
  if (proposal.delete_requested) {
    return [];
  }

  const changedFields: RevisionChangedField[] = [];
  if (proposal.current_prompt !== proposal.proposed_prompt) {
    changedFields.push('prompt');
  }
  if (proposal.current_question_type !== proposal.proposed_question_type) {
    changedFields.push('question_type');
  }
  if (!answerGroupsEqual(proposal.current_accepted_answers, proposal.proposed_accepted_answers)) {
    changedFields.push('answers');
  }
  if (!stringListEqual(proposal.current_segments, proposal.proposed_segments)) {
    changedFields.push('segments');
  }
  return changedFields;
}

export function revisionPrimaryKind(proposal: QuestionRevisionProposal): PendingRevisionPrimaryKind {
  if (proposal.delete_requested) {
    return 'delete';
  }
  if (proposal.current_question_type !== proposal.proposed_question_type) {
    return 'type';
  }
  if (proposal.current_prompt !== proposal.proposed_prompt) {
    return 'prompt';
  }
  return 'answer_segment';
}

export function revisionFieldLabel(field: RevisionChangedField): string {
  if (field === 'prompt') {
    return 'Prompt';
  }
  if (field === 'question_type') {
    return 'Type';
  }
  if (field === 'answers') {
    return 'Answers';
  }
  return 'Segments';
}

export function questionTypeLabel(questionType: QuestionType): string {
  if (questionType === 'single_text') {
    return 'Single text';
  }
  if (questionType === 'multi_text') {
    return 'Multi text';
  }
  if (questionType === 'ordered_multi') {
    return 'Ordered multi';
  }
  if (questionType === 'inline_cloze') {
    return 'Inline cloze';
  }
  return 'Computed text';
}

export function groupPendingRevisionsByModule(revisions: QuestionRevisionProposal[]): PendingRevisionModuleGroup[] {
  const grouped = new Map<string, PendingRevisionModuleGroup>();

  for (const proposal of revisions) {
    const entry: PendingRevisionEntry = {
      proposal,
      changedFields: revisionChangedFields(proposal),
      primaryKind: revisionPrimaryKind(proposal)
    };
    const existing = grouped.get(proposal.module_full_slug);
    if (existing) {
      existing.revisions.push(entry);
      continue;
    }
    grouped.set(proposal.module_full_slug, {
      moduleFullSlug: proposal.module_full_slug,
      moduleId: proposal.module_id,
      revisions: [entry]
    });
  }

  return [...grouped.values()].sort((left, right) => left.moduleFullSlug.localeCompare(right.moduleFullSlug));
}

export function revisionSectionsForModule(group: PendingRevisionModuleGroup): PendingRevisionSection[] {
  const sections: PendingRevisionSection[] = [
    { key: 'delete', title: 'Delete requests', revisions: [] },
    { key: 'type', title: 'Type changes', revisions: [] },
    { key: 'prompt', title: 'Prompt changes', revisions: [] },
    { key: 'answer_segment', title: 'Answer / segment changes', revisions: [] }
  ];

  for (const entry of group.revisions) {
    const section = sections.find((candidate) => candidate.key === entry.primaryKind);
    section?.revisions.push(entry);
  }

  return sections.filter((section) => section.revisions.length > 0);
}

const EMPTY_SCHEDULE: {
  bucket: ScheduleBucket;
  logical_bucket: LogicalBucket;
  recovery_streak: null;
  interval_step: null;
  last_incorrect_at: null;
  next_due_at: null;
} = {
  bucket: 'unseen',
  logical_bucket: 'unseen',
  recovery_streak: null,
  interval_step: null,
  last_incorrect_at: null,
  next_due_at: null
};

export function buildModerationRevisionSeed(
  proposal: QuestionRevisionProposal,
  source: RevisionSeedSource
): QuestionRow {
  const useCurrent = source === 'current';
  return {
    question_id: proposal.question_id,
    module_id: proposal.module_id,
    module_full_slug: proposal.module_full_slug,
    prompt: useCurrent ? proposal.current_prompt : proposal.proposed_prompt,
    prompt_preview: useCurrent ? proposal.current_prompt : proposal.proposed_prompt,
    question_type: useCurrent ? proposal.current_question_type : proposal.proposed_question_type,
    rank: 1,
    attempts: 0,
    correct_percentage: 0,
    first_asked_at: null,
    last_asked_at: null,
    review_flag: false,
    admin_verified: true,
    moderation_status: 'verified',
    created_by_user_id: null,
    creator_display_name: proposal.proposer_display_name,
    viewer_proposal: null,
    accepted_answers: useCurrent ? proposal.current_accepted_answers : proposal.proposed_accepted_answers,
    segments: useCurrent ? proposal.current_segments : proposal.proposed_segments,
    recent_incorrect_answers: [],
    schedule: { ...EMPTY_SCHEDULE }
  };
}
