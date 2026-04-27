import type { LogicalBucket, QuestionRevisionProposal, QuestionRow, ScheduleBucket } from './types';

export type RevisionSeedSource = 'current' | 'proposed';

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
    accepted_answers: useCurrent ? proposal.current_accepted_answers : proposal.proposed_accepted_answers,
    segments: useCurrent ? proposal.current_segments : proposal.proposed_segments,
    recent_incorrect_answers: [],
    schedule: { ...EMPTY_SCHEDULE }
  };
}
