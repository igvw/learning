import './test-support';

import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import QuizPage from '../src/components/QuizPage.svelte';
import StatsPage from '../src/components/StatsPage.svelte';
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

  it('shows only the expected answers in the feedback box and focuses the completion action', async () => {
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
          canonical_answers: ['nairobi']
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
          canonical_answers: ['nairobi']
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
          canonical_answers: ['tokyo']
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
          canonical_answers: ['nile / the nile']
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
    expect(screen.queryByText('nile / the nile')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Flag for revision' }));
    expect(markSpy).toHaveBeenCalledWith(21);
  });

  it('shows partial credit for multi-slot answers', () => {
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
          canonical_answers: ['head', 'thorax', 'abdomen']
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
    expect(screen.getByRole('button', { name: 'Flag for revision' })).toBeTruthy();
  });
});

describe('StatsPage', () => {
  it('opens a question row, toggles the review filter, renders both graphs, and sorts the table', async () => {
    const user = userEvent.setup();
    const openSpy = vi.fn();
    const toggleSpy = vi.fn();
    const stats: StatsResponse = {
      summary: {
        total_questions: 2,
        reviewed_questions: 1,
        total_attempts: 3,
        total_correct: 2,
        total_possible: 3,
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

    await user.click(screen.getByText('What structure anchors most plants in the ground?'));
    expect(openSpy).toHaveBeenCalledWith(stats.questions[0]);

    await user.click(screen.getByRole('checkbox'));
    expect(toggleSpy).toHaveBeenCalledWith(true);

    expect(screen.getByRole('img', { name: 'Recent session accuracy graph' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Spaced repetition stage counts' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Entry state counts' })).toBeTruthy();
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
    expect(view.container.querySelector('.graph-average-line title')?.textContent).toBe('83%');
    expect(screen.queryByRole('button', { name: 'Review' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Bucket' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Last seen' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Type' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Module' })).toBeNull();
    const firstRowClass = screen.getByText('What structure anchors most plants in the ground?').closest('tr')?.className ?? '';
    expect(firstRowClass).toContain('flagged-review');
    expect(firstRowClass).not.toContain('hot1-row');

    await user.click(screen.getByRole('button', { name: 'Bucket' }));
    await waitFor(() => {
      const rowsAfterScheduleSort = screen.getAllByRole('row');
      expect(rowsAfterScheduleSort[1].textContent).toContain('What is the capital of Canada?');
      expect(rowsAfterScheduleSort[1].textContent).toContain('3h');
    });

    await user.click(screen.getByRole('button', { name: 'Attempts' }));
    await waitFor(() => {
      const rowsAfterSort = screen.getAllByRole('row');
      expect(rowsAfterSort[1].textContent).toContain('What is the capital of Canada?');
    });

    await user.click(screen.getByRole('button', { name: 'Last seen' }));
    await waitFor(() => {
      const rowsAfterLastSeenSort = screen.getAllByRole('row');
      expect(rowsAfterLastSeenSort[1].textContent).toContain('What is the capital of Sweden?');
      expect(rowsAfterLastSeenSort[2].textContent).toContain('What structure anchors most plants in the ground?');
      expect(rowsAfterLastSeenSort[3].textContent).toContain('What is the capital of Canada?');
      expect(rowsAfterLastSeenSort[3].textContent).toContain('Never');
    });
  });
});
