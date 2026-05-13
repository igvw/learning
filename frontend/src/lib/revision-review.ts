import type { QuestionRevisionProposal, QuestionType } from './types';

export type RevisionChangedField = 'prompt' | 'question_type' | 'answers' | 'segments' | 'bundle_qml';

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
