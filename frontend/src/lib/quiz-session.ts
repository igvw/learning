import type { QuizSession, SubmitAnswerResult } from './types';

export function applySubmitAnswerResult(
  session: QuizSession,
  itemId: number,
  result: SubmitAnswerResult,
  completedAt: string
): QuizSession {
  return {
    ...session,
    completed_at: result.session_completed ? completedAt : session.completed_at,
    items: session.items.map((item) =>
      item.id === itemId
        ? {
            ...item,
            submitted_answer: result.submitted_answer,
            is_correct: result.is_correct,
            score_earned: result.score_earned,
            score_possible: result.score_possible,
            slot_results: result.slot_results,
            canonical_answers: result.canonical_answers,
            default_answers: result.default_answers,
            accepted_answer_groups: result.accepted_answer_groups,
            matched_default_answers: result.matched_default_answers
          }
        : item
    )
  };
}

export function applyQuestionReviewFlag(
  session: QuizSession,
  questionId: number,
  reviewFlag = true
): QuizSession {
  return {
    ...session,
    items: session.items.map((item) =>
      item.question_id === questionId
        ? {
            ...item,
            review_flag: reviewFlag
          }
        : item
    )
  };
}
