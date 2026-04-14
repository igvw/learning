import './test-support';

import { describe, expect, it } from 'vitest';

import { buildQuizItem, buildQuizSession } from './builders';
import { applyQuestionReviewFlag, applySubmitAnswerResult } from '../src/lib/quiz-session';
import type { SubmitAnswerResult } from '../src/lib/types';

describe('quiz-session helpers', () => {
  it('applies a submit result to the matching session item and completion timestamp', () => {
    const session = buildQuizSession({
      completed_at: null,
      items: [
        buildQuizItem({ id: 7, question_id: 10 }),
        buildQuizItem({ id: 8, question_id: 11 })
      ]
    });
    const result: SubmitAnswerResult = {
      item_id: 7,
      is_correct: true,
      score_earned: 1,
      score_possible: 1,
      slot_results: [{ index: 0, is_correct: true, expected: 'tokyo' }],
      canonical_answers: ['tokyo'],
      default_answers: ['tokyo'],
      accepted_answer_groups: [['tokyo']],
      matched_default_answers: [true],
      session_completed: true,
      submitted_answer: ['Tokyo']
    };

    const updated = applySubmitAnswerResult(session, 7, result, '2026-04-07T10:00:00Z');

    expect(updated.completed_at).toBe('2026-04-07T10:00:00Z');
    expect(updated.items[0].submitted_answer).toEqual(['Tokyo']);
    expect(updated.items[0].accepted_answer_groups).toEqual([['tokyo']]);
    expect(updated.items[1].submitted_answer).toBeNull();
  });

  it('applies a review flag only to the targeted question', () => {
    const session = buildQuizSession({
      items: [
        buildQuizItem({ id: 1, question_id: 10, review_flag: false }),
        buildQuizItem({ id: 2, question_id: 11, review_flag: false })
      ]
    });

    const updated = applyQuestionReviewFlag(session, 11, true);

    expect(updated.items[0].review_flag).toBe(false);
    expect(updated.items[1].review_flag).toBe(true);
  });
});
