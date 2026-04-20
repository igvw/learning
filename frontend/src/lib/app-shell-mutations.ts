import type {
  BulkModerationResult,
  BulkRevisionModerationItem,
  ModerationActionPayload,
  ModerationRevisionActionPayload,
  QuestionDraftPayload,
  QuestionRevisionProposal,
  QuestionRow
} from './types';

export type QuestionMutationReloadKind = 'question' | 'moderation';

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
  createQuestion: (payload: QuestionDraftPayload) => Promise<unknown>;
  reviseQuestion: (questionId: number, payload: QuestionDraftPayload & { reset_stats: boolean }) => Promise<unknown>;
  reviewQuestionRevision: (proposalId: number, payload: ModerationRevisionActionPayload) => Promise<unknown>;
}): Promise<QuestionMutationReloadKind> {
  if (editorMode === 'moderation' && editingRevisionProposal) {
    await reviewQuestionRevision(editingRevisionProposal.proposal_id, {
      action: 'approve',
      note: '',
      edited_revision: {
        ...payload,
        reset_stats: resetStats
      }
    });
    return 'moderation';
  }

  if (editingQuestion) {
    await reviseQuestion(editingQuestion.question_id, {
      ...payload,
      reset_stats: resetStats
    });
    return 'question';
  }

  await createQuestion(payload);
  return 'question';
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

export async function runBulkRevisionModeration({
  items,
  payload,
  reviewQuestionRevision
}: {
  items: BulkRevisionModerationItem[];
  payload: ModerationActionPayload;
  reviewQuestionRevision: (proposalId: number, payload: ModerationRevisionActionPayload) => Promise<unknown>;
}): Promise<BulkModerationResult> {
  let succeeded = 0;
  let failed = 0;

  for (const item of items) {
    try {
      await reviewQuestionRevision(item.proposalId, {
        ...payload,
        ...(payload.action === 'approve' ? { reset_stats: item.resetStats } : {})
      });
      succeeded += 1;
    } catch (error) {
      console.error(error);
      failed += 1;
    }
  }

  return { succeeded, failed };
}
