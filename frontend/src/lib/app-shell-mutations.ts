import type {
  BulkModerationResult,
  ModerationActionPayload,
  ModerationRevisionActionPayload,
  QuestionDraftPayload,
  QuestionMutationResult,
  QuestionRevisionProposal,
  QuestionRow
} from './types';

export type QuestionMutationReloadKind = 'question' | 'moderation';
export interface SavedQuestionMutation {
  reloadKind: QuestionMutationReloadKind;
  mutationResult: QuestionMutationResult | null;
}

export async function saveQuestionMutation({
  editorMode,
  editingQuestion,
  editingRevisionProposal,
  payload,
  resetStats,
  createQuestion,
  reviseQuestion,
  reviewQuestionRevision
}: {
  editorMode: 'standard' | 'moderation';
  editingQuestion: QuestionRow | null;
  editingRevisionProposal: QuestionRevisionProposal | null;
  payload: QuestionDraftPayload;
  resetStats: boolean;
  createQuestion: (payload: QuestionDraftPayload) => Promise<QuestionMutationResult>;
  reviseQuestion: (questionId: number, payload: QuestionDraftPayload & { reset_stats: boolean }) => Promise<QuestionMutationResult>;
  reviewQuestionRevision: (proposalId: number, payload: ModerationRevisionActionPayload) => Promise<unknown>;
}): Promise<SavedQuestionMutation> {
  if (editorMode === 'moderation' && editingRevisionProposal) {
    await reviewQuestionRevision(editingRevisionProposal.proposal_id, {
      action: 'approve',
      note: '',
      edited_revision: {
        ...payload,
        reset_stats: resetStats
      }
    });
    return { reloadKind: 'moderation', mutationResult: null };
  }

  if (editingQuestion) {
    const mutationResult = await reviseQuestion(editingQuestion.question_id, {
      ...payload,
      reset_stats: resetStats
    });
    return { reloadKind: 'question', mutationResult };
  }

  const mutationResult = await createQuestion(payload);
  return { reloadKind: 'question', mutationResult };
}

export async function runBulkModeration({
  ids,
  payload,
  handler
}: {
  ids: number[];
  payload: ModerationActionPayload;
  handler: (id: number, payload: ModerationActionPayload) => Promise<unknown>;
}): Promise<BulkModerationResult> {
  let succeeded = 0;
  let failed = 0;

  for (const id of ids) {
    try {
      await handler(id, payload);
      succeeded += 1;
    } catch (error) {
      console.error(error);
      failed += 1;
    }
  }

  return { succeeded, failed };
}
