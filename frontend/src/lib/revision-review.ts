import type { QuestionRevisionProposal, QuestionType } from './types';

export type RevisionChangedField = 'prompt' | 'question_type' | 'answers' | 'segments' | 'bundle_qml';
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
  if (proposal.current_question_type === 'bundle' || proposal.proposed_question_type === 'bundle') {
    if (proposal.current_question_type !== proposal.proposed_question_type) {
      changedFields.push('question_type');
    }
    if ((proposal.current_bundle_qml ?? '') !== (proposal.proposed_bundle_qml ?? '')) {
      changedFields.push('bundle_qml');
    }
    return changedFields;
  }
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
  return 'Bundle';
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
