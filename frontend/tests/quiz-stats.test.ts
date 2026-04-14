import './test-support';

import { render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import QuizPage from '../src/components/QuizPage.svelte';
import StatsPage from '../src/components/StatsPage.svelte';
import { buildFirstSeenGraph, buildRetryEligibilityGraph } from '../src/lib/stats-page';
import type { QuizSession, StatsResponse } from '../src/lib/types';

describe('QuizPage', () => {
  it('submits a single-answer prompt with Enter', async () => {
    const user = userEvent.setup();
    const submitSpy = vi.fn().mockResolvedValue(undefined);
    const session: QuizSession = {
      id: 22,
      module_id: null,
      completed_at: null,
      items: [
        {
          id: 7,
          position: 1,
          question_id: 10,
          module_id: 5,
          module_instruction: '',
          review_flag: false,
          prompt: 'What is the capital of Japan?',
          question_type: 'single_text',
          rank: 5,
          type_config: { expected_slots: 1 },
          submitted_answer: null,
          is_correct: null
        }
      ]
    };

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'All Modules',
        busyItemId: null,
        onSubmit: submitSpy
      }
    });

    const input = screen.getByRole('textbox');
    await user.type(input, 'Tokyo{enter}');

    expect(submitSpy).toHaveBeenCalledWith(7, ['Tokyo']);
  });

  it('moves through multi-answer inputs with Enter and submits from the last one', async () => {
    const user = userEvent.setup();
    const submitSpy = vi.fn().mockResolvedValue(undefined);
    const session: QuizSession = {
      id: 24,
      module_id: null,
      completed_at: null,
      items: [
        {
          id: 9,
          position: 1,
          question_id: 12,
          module_id: 5,
          module_instruction: '',
          review_flag: false,
          prompt: 'Name the capitals of Spain and Portugal.',
          question_type: 'ordered_multi',
          rank: 3,
          type_config: { expected_slots: 2 },
          submitted_answer: null,
          is_correct: null
        }
      ]
    };

    const view = render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onSubmit: submitSpy
      }
    });

    const inputs = view.getAllByRole('textbox');
    expect(screen.queryByText('Spain')).toBeNull();
    expect(screen.queryByText('Portugal')).toBeNull();
    await user.type(inputs[0], 'Madrid{enter}');

    expect(document.activeElement).toBe(inputs[1]);

    await user.type(inputs[1], 'Lisbon{enter}');

    expect(submitSpy).toHaveBeenCalledWith(9, ['Madrid', 'Lisbon']);
  });

  it('shows the default answer in the feedback box and focuses the completion action', async () => {
    const session: QuizSession = {
      id: 23,
      module_id: null,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        {
          id: 8,
          position: 1,
          question_id: 11,
          module_id: 5,
          module_instruction: '',
          review_flag: false,
          prompt: 'What is the capital of Kenya?',
          question_type: 'single_text',
          rank: 1,
          type_config: { expected_slots: 1 },
          submitted_answer: ['Mombasa'],
          is_correct: false,
          score_earned: 0,
          score_possible: 1,
          slot_results: [{ index: 0, is_correct: false, expected: 'nairobi' }],
          canonical_answers: ['nairobi'],
          default_answers: ['nairobi'],
          accepted_answer_groups: [['nairobi']],
          matched_default_answers: [false]
        }
      ]
    };

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onSubmit: vi.fn()
      }
    });

    const answeredCard = screen.getByText('1. What is the capital of Kenya?').closest('article');
    const answeredInput = screen.getByRole('textbox');
    const answerBox = screen.getByText('nairobi').closest('.answer-box');

    expect(screen.queryByText('Needs review')).toBeNull();
    expect(screen.queryByText('Accepted answers')).toBeNull();
    expect(screen.queryByText(/Slot 1:/)).toBeNull();
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
    expect(screen.getByText('nairobi')).toBeTruthy();
    expect(screen.getByText(/questions above for revision/i)).toBeTruthy();
    expect(answeredCard?.className).toContain('incorrect');
    expect(answeredInput.className).toContain('answer-incorrect');
    expect(answerBox?.className).toContain('plain-answer-box');
    const startAnotherQuizButton = screen.getByRole('button', { name: 'Start Another Quiz' });
    await waitFor(() => expect(document.activeElement).toBe(startAnotherQuizButton));
    expect(screen.getByRole('button', { name: 'Flag for revision' })).toBeTruthy();
  });

  it('lets you choose the number of questions before starting a quiz', async () => {
    const user = userEvent.setup();
    const changeSpy = vi.fn();

    render(QuizPage, {
      props: {
        session: null,
        moduleLabel: 'Geography',
        questionCount: 10,
        onChangeQuestionCount: changeSpy,
        onStartQuiz: vi.fn(),
        onSubmit: vi.fn()
      }
    });

    const input = screen.getByRole('spinbutton', { name: 'Questions per quiz' });
    await user.clear(input);
    await user.type(input, '15');
    await user.tab();

    expect(changeSpy).toHaveBeenCalledWith(15);
  });

  it('filters the completed session down to mistakes only', async () => {
    const user = userEvent.setup();
    const session: QuizSession = {
      id: 24,
      module_id: null,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        {
          id: 8,
          position: 1,
          question_id: 11,
          module_id: 5,
          module_instruction: '',
          review_flag: false,
          prompt: 'What is the capital of Kenya?',
          question_type: 'single_text',
          rank: 1,
          type_config: { expected_slots: 1 },
          submitted_answer: ['Mombasa'],
          is_correct: false,
          score_earned: 0,
          score_possible: 1,
          slot_results: [{ index: 0, is_correct: false, expected: 'nairobi' }],
          canonical_answers: ['nairobi'],
          default_answers: ['nairobi'],
          accepted_answer_groups: [['nairobi']],
          matched_default_answers: [false]
        },
        {
          id: 9,
          position: 2,
          question_id: 12,
          module_id: 5,
          module_instruction: '',
          review_flag: false,
          prompt: 'What is the capital of Japan?',
          question_type: 'single_text',
          rank: 2,
          type_config: { expected_slots: 1 },
          submitted_answer: ['Tokyo'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
          slot_results: [{ index: 0, is_correct: true, expected: 'tokyo' }],
          canonical_answers: ['tokyo'],
          default_answers: ['tokyo'],
          accepted_answer_groups: [['tokyo']],
          matched_default_answers: [true]
        }
      ]
    };

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onSubmit: vi.fn()
      }
    });

    expect(screen.getByText('1. What is the capital of Kenya?')).toBeTruthy();
    expect(screen.getByText('2. What is the capital of Japan?')).toBeTruthy();

    await user.click(screen.getByRole('button', { name: 'Review Mistakes' }));

    expect(screen.getByText('1. What is the capital of Kenya?')).toBeTruthy();
    expect(screen.queryByText('2. What is the capital of Japan?')).toBeNull();
    expect(screen.getByRole('button', { name: 'Show All Answers' })).toBeTruthy();
  });

  it('marks a completed question for revision', async () => {
    const user = userEvent.setup();
    const markSpy = vi.fn().mockResolvedValue(undefined);
    const session: QuizSession = {
      id: 25,
      module_id: null,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        {
          id: 18,
          position: 1,
          question_id: 21,
          module_id: 3,
          module_instruction: '',
          review_flag: false,
          prompt: 'Which river runs through Cairo?',
          question_type: 'single_text',
          rank: 5,
          type_config: { expected_slots: 1 },
          submitted_answer: ['Nile'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
          canonical_answers: ['nile / the nile'],
          default_answers: ['nile'],
          accepted_answer_groups: [['nile', 'the nile']],
          matched_default_answers: [true]
        }
      ]
    };

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        markingReviewQuestionId: null,
        onMarkForRevision: markSpy,
        onSubmit: vi.fn()
      }
    });

    const answeredCard = screen.getByText('1. Which river runs through Cairo?').closest('article');
    const answeredInput = screen.getByRole('textbox');

    expect(answeredCard?.className).toContain('correct');
    expect(answeredInput.className).toContain('answer-correct');
    expect(screen.queryByText('nile')).toBeNull();
    expect(screen.queryByText('nile / the nile')).toBeNull();
    expect(screen.queryByRole('list')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Flag for revision' }));
    expect(markSpy).toHaveBeenCalledWith(21);
  });

  it('shows all accepted answers when a correct alternative is submitted', () => {
    const session: QuizSession = {
      id: 27,
      module_id: null,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        {
          id: 20,
          position: 1,
          question_id: 23,
          module_id: 3,
          module_instruction: '',
          review_flag: false,
          prompt: 'Which river runs through Cairo?',
          question_type: 'single_text',
          rank: 5,
          type_config: { expected_slots: 1 },
          submitted_answer: ['the nile'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
          slot_results: [{ index: 0, is_correct: true, expected: 'nile / the nile' }],
          canonical_answers: ['nile / the nile'],
          default_answers: ['nile'],
          accepted_answer_groups: [['nile', 'the nile']],
          matched_default_answers: [false]
        }
      ]
    };

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onSubmit: vi.fn()
      }
    });

    expect(screen.getByText('nile / the nile')).toBeTruthy();
    expect(screen.queryByText(/^nile$/)).toBeNull();
    expect(screen.getAllByRole('listitem')).toHaveLength(1);
  });

  it('shows multi-slot defaults and expands to all answers when any slot used an alternative', () => {
    const session: QuizSession = {
      id: 26,
      module_id: null,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        {
          id: 19,
          position: 1,
          question_id: 22,
          module_id: 2,
          module_instruction: '',
          review_flag: false,
          prompt: 'Name the three major body sections of an insect.',
          question_type: 'ordered_multi',
          rank: 4,
          type_config: { expected_slots: 3 },
          submitted_answer: ['head', 'thorax', 'legs'],
          is_correct: false,
          score_earned: 2 / 3,
          score_possible: 1,
          slot_results: [
            { index: 0, is_correct: true, expected: 'head' },
            { index: 1, is_correct: true, expected: 'thorax' },
            { index: 2, is_correct: false, expected: 'abdomen' }
          ],
          canonical_answers: ['head / skull', 'thorax', 'abdomen'],
          default_answers: ['head', 'thorax', 'abdomen'],
          accepted_answer_groups: [['head', 'skull'], ['thorax'], ['abdomen']],
          matched_default_answers: [false, true, false]
        }
      ]
    };

    const view = render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Biology',
        busyItemId: null,
        onSubmit: vi.fn()
      }
    });

    const inputs = view.getAllByRole('textbox');
    expect(screen.getByText('2/3')).toBeTruthy();
    expect(inputs[0].className).toContain('answer-correct');
    expect(inputs[1].className).toContain('answer-correct');
    expect(inputs[2].className).toContain('answer-incorrect');
    expect(screen.getByText('head / skull')).toBeTruthy();
    expect(screen.getByText('thorax')).toBeTruthy();
    expect(screen.getByText('abdomen')).toBeTruthy();
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
    expect(screen.getByRole('button', { name: 'Flag for revision' })).toBeTruthy();
  });
});

describe('StatsPage', () => {
  it('builds retry eligibility counts across the coming week from fixed buckets only', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-04-05T10:30:00Z'));

    const graph = buildRetryEligibilityGraph([
      {
        question_id: 1,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'one hour',
        prompt_preview: 'one hour',
        question_type: 'single_text',
        rank: 1,
        attempts: 1,
        correct_percentage: 1,
        first_asked_at: '2026-04-05T09:00:00Z',
        last_asked_at: '2026-04-05T09:00:00Z',
        review_flag: false,
        accepted_answers: [['a']],
        segments: [],
        recent_incorrect_answers: [],
        schedule: {
          bucket: 'cooling',
          logical_bucket: '1h',
          recovery_streak: null,
          interval_step: 0,
          last_incorrect_at: null,
          next_due_at: '2026-04-05T11:00:00Z',
          retry_pending: false
        }
      },
      {
        question_id: 2,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'one day',
        prompt_preview: 'one day',
        question_type: 'single_text',
        rank: 2,
        attempts: 1,
        correct_percentage: 1,
        first_asked_at: '2026-04-05T09:00:00Z',
        last_asked_at: '2026-04-05T09:00:00Z',
        review_flag: false,
        accepted_answers: [['a']],
        segments: [],
        recent_incorrect_answers: [],
        schedule: {
          bucket: 'cooling',
          logical_bucket: '1d',
          recovery_streak: null,
          interval_step: 4,
          last_incorrect_at: null,
          next_due_at: '2026-04-06T09:00:00Z',
          retry_pending: false
        }
      },
      {
        question_id: 3,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'three day overdue',
        prompt_preview: 'three day overdue',
        question_type: 'single_text',
        rank: 3,
        attempts: 1,
        correct_percentage: 1,
        first_asked_at: '2026-04-05T09:00:00Z',
        last_asked_at: '2026-04-05T09:00:00Z',
        review_flag: false,
        accepted_answers: [['a']],
        segments: [],
        recent_incorrect_answers: [],
        schedule: {
          bucket: 'due_review',
          logical_bucket: '3d',
          recovery_streak: null,
          interval_step: 5,
          last_incorrect_at: null,
          next_due_at: '2026-04-04T10:00:00Z',
          retry_pending: false
        }
      },
      {
        question_id: 4,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'seven day retry pending',
        prompt_preview: 'seven day retry pending',
        question_type: 'single_text',
        rank: 4,
        attempts: 1,
        correct_percentage: 1,
        first_asked_at: '2026-04-05T09:00:00Z',
        last_asked_at: '2026-04-05T09:00:00Z',
        review_flag: false,
        accepted_answers: [['a']],
        segments: [],
        recent_incorrect_answers: [],
        schedule: {
          bucket: 'due_review',
          logical_bucket: '7d',
          recovery_streak: null,
          interval_step: 6,
          last_incorrect_at: null,
          next_due_at: null,
          retry_pending: true
        }
      },
      {
        question_id: 5,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'three day future',
        prompt_preview: 'three day future',
        question_type: 'single_text',
        rank: 5,
        attempts: 1,
        correct_percentage: 1,
        first_asked_at: '2026-04-05T09:00:00Z',
        last_asked_at: '2026-04-05T09:00:00Z',
        review_flag: false,
        accepted_answers: [['a']],
        segments: [],
        recent_incorrect_answers: [],
        schedule: {
          bucket: 'cooling',
          logical_bucket: '3d',
          recovery_streak: null,
          interval_step: 5,
          last_incorrect_at: null,
          next_due_at: '2026-04-06T10:00:00Z',
          retry_pending: false
        }
      },
      {
        question_id: 6,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'seven day future',
        prompt_preview: 'seven day future',
        question_type: 'single_text',
        rank: 6,
        attempts: 1,
        correct_percentage: 1,
        first_asked_at: '2026-04-05T09:00:00Z',
        last_asked_at: '2026-04-05T09:00:00Z',
        review_flag: false,
        accepted_answers: [['a']],
        segments: [],
        recent_incorrect_answers: [],
        schedule: {
          bucket: 'cooling',
          logical_bucket: '7d',
          recovery_streak: null,
          interval_step: 6,
          last_incorrect_at: null,
          next_due_at: '2026-04-08T10:00:00Z',
          retry_pending: false
        }
      },
      {
        question_id: 7,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'fourteen day future',
        prompt_preview: 'fourteen day future',
        question_type: 'single_text',
        rank: 7,
        attempts: 1,
        correct_percentage: 1,
        first_asked_at: '2026-04-05T09:00:00Z',
        last_asked_at: '2026-04-05T09:00:00Z',
        review_flag: false,
        accepted_answers: [['a']],
        segments: [],
        recent_incorrect_answers: [],
        schedule: {
          bucket: 'cooling',
          logical_bucket: '14d',
          recovery_streak: null,
          interval_step: 7,
          last_incorrect_at: null,
          next_due_at: '2026-04-11T10:00:00Z',
          retry_pending: false
        }
      },
      {
        question_id: 8,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'beyond week',
        prompt_preview: 'beyond week',
        question_type: 'single_text',
        rank: 8,
        attempts: 1,
        correct_percentage: 1,
        first_asked_at: '2026-04-05T09:00:00Z',
        last_asked_at: '2026-04-05T09:00:00Z',
        review_flag: false,
        accepted_answers: [['a']],
        segments: [],
        recent_incorrect_answers: [],
        schedule: {
          bucket: 'cooling',
          logical_bucket: '14d',
          recovery_streak: null,
          interval_step: 7,
          last_incorrect_at: null,
          next_due_at: '2026-04-12T10:00:00Z',
          retry_pending: false
        }
      },
      {
        question_id: 9,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'review',
        prompt_preview: 'review',
        question_type: 'single_text',
        rank: 9,
        attempts: 1,
        correct_percentage: 1,
        first_asked_at: '2026-04-05T09:00:00Z',
        last_asked_at: '2026-04-05T09:00:00Z',
        review_flag: true,
        accepted_answers: [['a']],
        segments: [],
        recent_incorrect_answers: [],
        schedule: {
          bucket: 'hot0',
          logical_bucket: 'review',
          recovery_streak: 0,
          interval_step: 0,
          last_incorrect_at: null,
          next_due_at: null,
          retry_pending: true
        }
      },
      {
        question_id: 10,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'mastery',
        prompt_preview: 'mastery',
        question_type: 'single_text',
        rank: 10,
        attempts: 1,
        correct_percentage: 1,
        first_asked_at: '2026-04-05T09:00:00Z',
        last_asked_at: '2026-04-05T09:00:00Z',
        review_flag: false,
        accepted_answers: [['a']],
        segments: [],
        recent_incorrect_answers: [],
        schedule: {
          bucket: 'mastery',
          logical_bucket: 'mastery',
          recovery_streak: null,
          interval_step: null,
          last_incorrect_at: null,
          next_due_at: null,
          retry_pending: false
        }
      },
      {
        question_id: 11,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'unseen',
        prompt_preview: 'unseen',
        question_type: 'single_text',
        rank: 11,
        attempts: 0,
        correct_percentage: 0,
        first_asked_at: null,
        last_asked_at: null,
        review_flag: false,
        accepted_answers: [['a']],
        segments: [],
        recent_incorrect_answers: [],
        schedule: {
          bucket: 'unseen',
          logical_bucket: 'unseen',
          recovery_streak: null,
          interval_step: null,
          last_incorrect_at: null,
          next_due_at: null,
          retry_pending: false
        }
      }
    ]);

    expect(graph.days.map((day) => day.label)).toEqual(['<1', '1', '2', '3', '4', '5', '6', '7']);
    expect(graph.days.map((day) => day.count)).toEqual([3, 2, 0, 1, 0, 0, 1, 1]);
  });

  it('builds first-time answered counts across the last 7 local days', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-04-10T12:00:00Z'));

    const buildQuestion = (questionId: number, firstAskedAt: string | null) => ({
      question_id: questionId,
      module_id: 1,
      module_full_slug: 'biology',
      prompt: `question ${questionId}`,
      prompt_preview: `question ${questionId}`,
      question_type: 'single_text' as const,
      rank: questionId,
      attempts: firstAskedAt ? 1 : 0,
      correct_percentage: 1,
      first_asked_at: firstAskedAt,
      last_asked_at: firstAskedAt,
      review_flag: false,
      accepted_answers: [['a']],
      segments: [],
      recent_incorrect_answers: [],
      schedule: {
        bucket: 'cooling' as const,
        logical_bucket: '1h' as const,
        recovery_streak: null,
        interval_step: 0,
        last_incorrect_at: null,
        next_due_at: null,
        retry_pending: false
      }
    });

    const graph = buildFirstSeenGraph([
      buildQuestion(1, '2026-04-10T08:00:00Z'),
      buildQuestion(2, '2026-04-10T09:00:00Z'),
      buildQuestion(3, '2026-04-09T08:00:00Z'),
      buildQuestion(4, '2026-04-07T08:00:00Z'),
      buildQuestion(5, '2026-04-04T08:00:00Z'),
      buildQuestion(6, '2026-04-03T08:00:00Z'),
      buildQuestion(7, null),
      buildQuestion(8, '2026-04-02T08:00:00Z')
    ]);

    expect(graph.days).toHaveLength(7);
    expect(graph.days.map((day) => day.count)).toEqual([1, 0, 0, 1, 0, 1, 2]);
  });

  it('filters the single table to review questions, keeps graphs visible, and sorts the displayed rows', async () => {
    const user = userEvent.setup();
    const openSpy = vi.fn();
    const toggleSpy = vi.fn();
    const stats: StatsResponse = {
      summary: {
        total_questions: 4,
        reviewed_questions: 2,
        total_attempts: 7,
        total_correct: 4,
        total_possible: 6,
        accuracy: 2 / 3
      },
      recent_sessions: [
        {
          session_id: 11,
          created_at: '2026-04-04T11:00:00Z',
          answered_count: 2,
          correct_count: 2,
          score_possible: 2,
          accuracy: 1
        },
        {
          session_id: 10,
          created_at: '2026-04-04T10:00:00Z',
          answered_count: 3,
          correct_count: 2,
          score_possible: 3,
          accuracy: 2 / 3
        }
      ],
      questions: [
        {
          question_id: 50,
          module_id: 3,
          module_full_slug: 'biology/plants',
          prompt: 'What structure anchors most plants in the ground?',
          prompt_preview: 'What structure anchors most plants in the ground?',
          question_type: 'single_text',
          rank: 2,
          attempts: 3,
          correct_percentage: 2 / 3,
          first_asked_at: '2026-04-01T06:00:00Z',
          last_asked_at: '2026-04-01T06:00:00Z',
          review_flag: true,
          accepted_answers: [['roots']],
          segments: [],
          schedule: {
            bucket: 'hot1_sit_out',
            logical_bucket: 'review',
            recovery_streak: 1,
            interval_step: 0,
            last_incorrect_at: '2026-04-04T08:00:00Z',
            next_due_at: null,
            retry_pending: false
          },
          recent_incorrect_answers: [
            {
              answer_text: 'stems',
              count: 2,
              latest_answered_at: '2026-04-04T08:00:00Z'
            }
          ]
        },
        {
          question_id: 51,
          module_id: 5,
          module_full_slug: 'geography/capitals',
          prompt: 'What is the capital of Canada?',
          prompt_preview: 'What is the capital of Canada?',
          question_type: 'single_text',
          rank: 5,
          attempts: 7,
          correct_percentage: 6 / 7,
          first_asked_at: '2026-03-30T07:00:00Z',
          last_asked_at: null,
          review_flag: false,
          accepted_answers: [['ottawa']],
          segments: [],
          schedule: {
            bucket: 'due_review',
            logical_bucket: '3h',
            recovery_streak: null,
            interval_step: 1,
            last_incorrect_at: '2026-04-01T08:00:00Z',
            next_due_at: '2026-04-07T08:00:00Z',
            retry_pending: false
          },
          recent_incorrect_answers: []
        },
        {
          question_id: 52,
          module_id: 5,
          module_full_slug: 'geography/capitals',
          prompt: 'What is the capital of Sweden?',
          prompt_preview: 'What is the capital of Sweden?',
          question_type: 'single_text',
          rank: 6,
          attempts: 2,
          correct_percentage: 1,
          first_asked_at: '2026-04-02T07:30:00Z',
          last_asked_at: '2026-04-02T07:30:00Z',
          review_flag: false,
          accepted_answers: [['stockholm']],
          segments: [],
          schedule: {
            bucket: 'mastery',
            logical_bucket: 'mastery',
            recovery_streak: null,
            interval_step: null,
            last_incorrect_at: null,
            next_due_at: null,
            retry_pending: false
          },
          recent_incorrect_answers: []
        },
        {
          question_id: 53,
          module_id: 3,
          module_full_slug: 'biology/plants',
          prompt: 'What process lets plants turn light into stored energy?',
          prompt_preview: 'What process lets plants turn light into stored energy?',
          question_type: 'single_text',
          rank: 1,
          attempts: 2,
          correct_percentage: 1 / 2,
          first_asked_at: '2026-04-03T07:00:00Z',
          last_asked_at: '2026-04-03T07:00:00Z',
          review_flag: true,
          accepted_answers: [['photosynthesis']],
          segments: [],
          schedule: {
            bucket: 'hot0',
            logical_bucket: 'review',
            recovery_streak: 0,
            interval_step: 0,
            last_incorrect_at: '2026-04-03T07:00:00Z',
            next_due_at: null,
            retry_pending: true
          },
          recent_incorrect_answers: [
            {
              answer_text: 'respiration',
              count: 1,
              latest_answered_at: '2026-04-03T07:00:00Z'
            }
          ]
        }
      ]
    };

    const view = render(StatsPage, {
      props: {
        moduleLabel: 'Biology',
        stats,
        loading: false,
        reviewOnly: false,
        onToggleReviewOnly: toggleSpy,
        onOpenCreate: vi.fn(),
        onOpenEdit: openSpy
      }
    });

    let mainPanel = screen.getByRole('heading', { name: 'Questions' }).closest('.panel') as HTMLElement;
    expect(screen.queryByText('What structure anchors most plants in the ground?')).toBeNull();
    expect(within(mainPanel).getByText('What is the capital of Canada?')).toBeTruthy();
    expect(within(mainPanel).getByText('What is the capital of Sweden?')).toBeTruthy();

    await user.click(within(mainPanel).getByText('What is the capital of Canada?'));
    expect(openSpy).toHaveBeenCalledWith(stats.questions[1]);

    await user.click(within(mainPanel).getByRole('button', { name: 'Bucket' }));
    await waitFor(() => {
      const rowsAfterScheduleSort = within(mainPanel).getAllByRole('row');
      expect(rowsAfterScheduleSort[1].textContent).toContain('What is the capital of Canada?');
      expect(rowsAfterScheduleSort[1].textContent).toContain('3h');
    });

    await user.click(within(mainPanel).getByRole('button', { name: 'Attempts' }));
    await waitFor(() => {
      const rowsAfterSort = within(mainPanel).getAllByRole('row');
      expect(rowsAfterSort[1].textContent).toContain('What is the capital of Canada?');
    });

    await user.click(screen.getByRole('checkbox'));
    expect(toggleSpy).toHaveBeenCalledWith(true);
    await view.rerender({
      moduleLabel: 'Biology',
      stats,
      loading: false,
      reviewOnly: true,
      onToggleReviewOnly: toggleSpy,
      onOpenCreate: vi.fn(),
      onOpenEdit: openSpy
    });

    mainPanel = screen.getByRole('heading', { name: 'Questions' }).closest('.panel') as HTMLElement;
    expect(within(mainPanel).getByText('What structure anchors most plants in the ground?')).toBeTruthy();
    expect(within(mainPanel).getByText('What process lets plants turn light into stored energy?')).toBeTruthy();
    expect(screen.queryByText('What is the capital of Canada?')).toBeNull();

    await user.click(within(mainPanel).getByText('What structure anchors most plants in the ground?'));
    expect(openSpy).toHaveBeenLastCalledWith(stats.questions[0]);

    expect(screen.getByRole('img', { name: 'Recent session accuracy graph' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Spaced repetition stage counts' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Entry state counts' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Retry eligibility by day' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'First-time questions answered by day' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Latest quiz performance' }).closest('.stats-chart-panel-performance')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Entry states' }).closest('.stats-chart-panel-entry')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Spaced repetition stages' }).closest('.stats-chart-panel-stages')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Retry eligibility' }).closest('.stats-chart-panel-retry')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'First-time questions answered' }).closest('.stats-chart-panel-first-seen')).toBeTruthy();
    const graphLabels = Array.from(view.container.querySelectorAll('.session-bar text')).map((node) => node.textContent);
    expect(graphLabels).toContain('2/3');
    expect(graphLabels).toContain('2/2');
    expect(graphLabels).toContain('Unseen');
    expect(graphLabels).toContain('Review');
    expect(graphLabels).toContain('Bucketed');
    expect(graphLabels).toContain('1h');
    expect(graphLabels).toContain('3h');
    expect(graphLabels).toContain('6h');
    expect(graphLabels).toContain('12h');
    expect(graphLabels).toContain('1d');
    expect(graphLabels).toContain('3d');
    expect(graphLabels).toContain('7d');
    expect(graphLabels).toContain('14d');
    expect(graphLabels).toContain('Mastery');
    expect(graphLabels).toContain('<1');
    expect(graphLabels).toContain('7');
    expect(view.container.querySelector('.graph-average-line title')?.textContent).toBe('83%');
    expect(screen.queryByRole('button', { name: 'Review' })).toBeNull();
    expect(within(mainPanel).getByRole('button', { name: 'Bucket' })).toBeTruthy();
    expect(within(mainPanel).getByRole('button', { name: 'Last seen' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Type' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Module' })).toBeNull();
    const firstRowClass =
      within(mainPanel).getByText('What structure anchors most plants in the ground?').closest('tr')?.className ?? '';
    expect(firstRowClass).toContain('flagged-review');
    expect(firstRowClass).not.toContain('hot1-row');

    await user.click(within(mainPanel).getByRole('button', { name: 'Last seen' }));
    await waitFor(() => {
      const rowsAfterLastSeenSort = within(mainPanel).getAllByRole('row');
      expect(rowsAfterLastSeenSort[1].textContent).toContain('What process lets plants turn light into stored energy?');
      expect(rowsAfterLastSeenSort[2].textContent).toContain('What structure anchors most plants in the ground?');
    });
  });

  it('shows an empty review state when the toggle is on but no review questions exist', () => {
    render(StatsPage, {
      props: {
        stats: {
          summary: {
            total_questions: 1,
            reviewed_questions: 0,
            total_attempts: 0,
            total_correct: 0,
            total_possible: 0,
            accuracy: 0
          },
          recent_sessions: [],
          questions: [
            {
              question_id: 1,
              module_id: 2,
              module_full_slug: 'geography/capitals',
              prompt: 'What is the capital of Canada?',
              prompt_preview: 'What is the capital of Canada?',
              question_type: 'single_text',
              rank: 1,
              attempts: 0,
              correct_percentage: 0,
              first_asked_at: null,
              last_asked_at: null,
              review_flag: false,
              accepted_answers: [['ottawa']],
              segments: [],
              recent_incorrect_answers: [],
              schedule: {
                bucket: 'unseen',
                logical_bucket: 'unseen',
                recovery_streak: null,
                interval_step: null,
                last_incorrect_at: null,
                next_due_at: null,
                retry_pending: false
              }
            }
          ]
        },
        reviewOnly: true
      }
    });

    expect(screen.getByText('No review questions in this scope.')).toBeTruthy();
  });

  it('shows an empty main table when every question is review-flagged', () => {
    render(StatsPage, {
      props: {
        stats: {
          summary: {
            total_questions: 1,
            reviewed_questions: 1,
            total_attempts: 1,
            total_correct: 1,
            total_possible: 1,
            accuracy: 1
          },
          recent_sessions: [],
          questions: [
            {
              question_id: 1,
              module_id: 2,
              module_full_slug: 'biology/plants',
              prompt: 'What structure anchors most plants in the ground?',
              prompt_preview: 'What structure anchors most plants in the ground?',
              question_type: 'single_text',
              rank: 1,
              attempts: 1,
              correct_percentage: 1,
              first_asked_at: '2026-04-01T06:00:00Z',
              last_asked_at: '2026-04-01T06:00:00Z',
              review_flag: true,
              accepted_answers: [['roots']],
              segments: [],
              recent_incorrect_answers: [],
              schedule: {
                bucket: 'hot1_sit_out',
                logical_bucket: 'review',
                recovery_streak: 1,
                interval_step: 0,
                last_incorrect_at: '2026-04-01T06:00:00Z',
                next_due_at: null,
                retry_pending: false
              }
            }
          ]
        }
      }
    });

    expect(screen.getByText('No non-review questions in this scope.')).toBeTruthy();
  });
});
