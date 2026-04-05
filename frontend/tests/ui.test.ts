import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import QuizPage from '../src/components/QuizPage.svelte';
import ModuleMenu from '../src/components/ModuleMenu.svelte';
import StatsPage from '../src/components/StatsPage.svelte';
import type { ModuleNode, QuizSession, StatsResponse } from '../src/lib/types';

afterEach(() => {
  cleanup();
});

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
          review_flag: false,
          prompt: 'What is the capital of Japan?',
          question_type: 'single_text',
          ranking: 5,
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
          review_flag: false,
          prompt: 'Name the capitals of Spain and Portugal.',
          question_type: 'ordered_multi',
          ranking: 3,
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
          review_flag: false,
          prompt: 'What is the capital of Kenya?',
          question_type: 'single_text',
          ranking: 1,
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

    const answeredCard = screen.getByText('What is the capital of Kenya?').closest('article');
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
          review_flag: false,
          prompt: 'Which river runs through Cairo?',
          question_type: 'single_text',
          ranking: 5,
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

    const answeredCard = screen.getByText('Which river runs through Cairo?').closest('article');
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
          review_flag: false,
          prompt: 'Name the three major body sections of an insect.',
          question_type: 'ordered_multi',
          ranking: 4,
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
  it('opens a question row, toggles the review filter, renders the graph, and sorts the table', async () => {
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
          module_title: 'Plants',
          prompt: 'What structure anchors most plants in the ground?',
          prompt_preview: 'What structure anchors most plants in the ground?',
          question_type: 'single_text',
          ranking: 2,
          attempts: 3,
          correct_percentage: 2 / 3,
          last_asked_at: null,
          review_flag: true,
          accepted_answers: [['roots']],
          slot_prompts: [],
          segments: []
        },
        {
          question_id: 51,
          module_id: 5,
          module_title: 'Capitals',
          prompt: 'What is the capital of Canada?',
          prompt_preview: 'What is the capital of Canada?',
          question_type: 'single_text',
          ranking: 5,
          attempts: 7,
          correct_percentage: 6 / 7,
          last_asked_at: null,
          review_flag: false,
          accepted_answers: [['ottawa']],
          slot_prompts: [],
          segments: []
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
    const graphLabels = Array.from(view.container.querySelectorAll('.session-bar text')).map((node) => node.textContent);
    expect(graphLabels).toEqual(['2/3', '2/2']);
    expect(view.container.querySelector('.graph-average-line title')?.textContent).toBe('83%');
    expect(screen.queryByRole('button', { name: 'Review' })).toBeNull();
    expect(screen.getByText('What structure anchors most plants in the ground?').closest('tr')?.className).toContain(
      'flagged-review'
    );

    await user.click(screen.getByRole('button', { name: 'Attempts' }));
    await waitFor(() => {
      const rowsAfterSort = screen.getAllByRole('row');
      expect(rowsAfterSort[1].textContent).toContain('What is the capital of Canada?');
    });
  });
});

describe('ModuleMenu', () => {
  it('reveals submodules on click and selects parent and child modules', async () => {
    const user = userEvent.setup();
    const selectSpy = vi.fn();
    const modules: ModuleNode[] = [
      {
        id: 1,
        source_id: 'biology',
        title: 'Biology',
        slug: 'biology',
        full_slug: 'biology',
        ui_copy: {
          question_label: 'Question',
          answer_label: 'Answer',
          stats_title: 'Stats',
          review_title: 'Review'
        },
        children: [
          {
            id: 2,
            source_id: 'biology-plants',
            title: 'Plants',
            slug: 'plants',
            full_slug: 'biology/plants',
            ui_copy: {
              question_label: 'Question',
              answer_label: 'Answer',
              stats_title: 'Stats',
              review_title: 'Review'
            },
            children: []
          }
        ]
      }
    ];

    render(ModuleMenu, {
      props: {
        open: true,
        modules,
        selectedModuleId: null,
        selectedModuleLabel: 'All Modules',
        onClose: vi.fn(),
        onSelect: selectSpy
      }
    });

    expect(screen.queryByRole('button', { name: 'All Modules' })).toBeNull();
    expect(screen.queryByText('Plants')).toBeNull();

    await user.click(screen.getByRole('button', { name: /Biology biology/i }));
    expect(selectSpy).toHaveBeenCalledWith(1, true);
    expect(screen.getByText('Plants')).toBeTruthy();

    await user.click(screen.getByText('Plants'));
    expect(selectSpy).toHaveBeenCalledWith(2, false);
  });
});
