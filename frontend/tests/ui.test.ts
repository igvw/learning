import { cleanup, render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/lib/api', () => ({
  commitQuestionImport: vi.fn(),
  createModule: vi.fn(),
  createQuestion: vi.fn(),
  createQuizSession: vi.fn(),
  createUser: vi.fn(),
  getModulesTree: vi.fn(),
  getStats: vi.fn(),
  getUsers: vi.fn(),
  reviseQuestion: vi.fn(),
  setQuestionReviewFlag: vi.fn(),
  submitQuizAnswer: vi.fn(),
  validateQuestionImportRows: vi.fn(),
  validateQuestionImportText: vi.fn()
}));

import App from '../src/App.svelte';
import AdminPage from '../src/components/AdminPage.svelte';
import EditorDrawer from '../src/components/EditorDrawer.svelte';
import Header from '../src/components/Header.svelte';
import ImportDrawer from '../src/components/ImportDrawer.svelte';
import QuizPage from '../src/components/QuizPage.svelte';
import ModuleMenu from '../src/components/ModuleMenu.svelte';
import StatsPage from '../src/components/StatsPage.svelte';
import * as api from '../src/lib/api';
import { ensureModulePath } from '../src/lib/module-paths';
import type { ModuleNode, QuestionImportResult, QuizSession, StatsResponse, User } from '../src/lib/types';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  window.localStorage.clear();
  window.history.replaceState({}, '', '/quiz');
});

describe('module paths', () => {
  it('creates only missing segments for slash-separated module paths', async () => {
    let moduleTree: ModuleNode[] = [
      {
        id: 1,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        instruction: '',
        children: [
          {
            id: 2,
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            instruction: '',
            children: []
          }
        ]
      }
    ];

    const createSpy = vi.fn(async ({ title, parent_id, instruction }) => {
      const id = title === 'nouns_to_english' ? 3 : 4;
      const fullSlug =
        title === 'nouns_to_english'
          ? 'norwegian/vocabulary/nouns_to_english'
          : 'norwegian/vocabulary/nouns_to_english/plural_forms';
      return {
        id,
        title,
        slug: title,
        full_slug: fullSlug,
        instruction,
        children: []
      };
    });

    const reloadModules = vi.fn(async () => {
      moduleTree = [
        {
          ...moduleTree[0],
          children: [
            {
              ...moduleTree[0].children[0],
              children: [
                {
                  id: 3,
                  title: 'nouns_to_english',
                  slug: 'nouns_to_english',
                  full_slug: 'norwegian/vocabulary/nouns_to_english',
                  instruction: 'Translate to English.',
                  children: []
                }
              ]
            }
          ]
        }
      ];
      return moduleTree;
    });

    const created = await ensureModulePath({
      modules: moduleTree,
      parentId: null,
      titlePath: 'Norwegian / vocabulary / nouns_to_english',
      instruction: 'Translate to English.',
      createModule: createSpy,
      reloadModules
    });

    expect(createSpy).toHaveBeenCalledTimes(1);
    expect(createSpy).toHaveBeenCalledWith({
      title: 'nouns_to_english',
      parent_id: 2,
      instruction: 'Translate to English.'
    });
    expect(created.full_slug).toBe('norwegian/vocabulary/nouns_to_english');
  });
});

describe('Header', () => {
  it('shows an avatar-style active user badge and switches users from a small menu', async () => {
    const user = userEvent.setup();
    const selectSpy = vi.fn();
    const users: User[] = [
      {
        id: 1,
        handle: 'ignazio',
        display_name: 'Ignazio',
        created_at: '2026-04-05T10:00:00Z'
      },
      {
        id: 2,
        handle: 'ingrid',
        display_name: 'Ingrid',
        created_at: '2026-04-05T10:05:00Z'
      }
    ];

    render(Header, {
      props: {
        currentRoute: 'quiz',
        users,
        activeUserId: 1,
        onNavigate: vi.fn(),
        onToggleMenu: vi.fn(),
        onSelectUser: selectSpy
      }
    });

    const avatarButton = screen.getByRole('button', { name: 'Open user menu for Ignazio' });
    expect(avatarButton.textContent).toBe('I');
    expect(screen.queryByRole('button', { name: /create user/i })).toBeNull();
    expect(screen.queryByRole('combobox', { name: 'Active user' })).toBeNull();

    await user.click(avatarButton);
    expect(screen.getByRole('menu', { name: 'User menu' })).toBeTruthy();
    await user.click(screen.getByRole('menuitemradio', { name: /Ingrid/i }));
    expect(selectSpy).toHaveBeenCalledWith(2);
  });
});

describe('App', () => {
  it('persists the selected module across remounts', async () => {
    const user = userEvent.setup();
    const modules: ModuleNode[] = [
      {
        id: 1,
        title: 'Biology',
        slug: 'biology',
        full_slug: 'biology',
        instruction: '',
        children: []
      },
      {
        id: 2,
        title: 'Geography',
        slug: 'geography',
        full_slug: 'geography',
        instruction: '',
        children: []
      }
    ];
    const users: User[] = [
      {
        id: 1,
        handle: 'ignazio',
        display_name: 'Ignazio',
        created_at: '2026-04-05T10:00:00Z'
      }
    ];

    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue(users);

    const firstRender = render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Biology' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Open module menu' }));
    const moduleSelection = screen.getByLabelText('Module selection');
    await user.click(within(moduleSelection).getByRole('button', { name: /Geography\s*geography/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Geography' })).toBeTruthy();
    });
    expect(window.localStorage.getItem('learning.selected-module-id')).toBe('2');

    firstRender.unmount();

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Geography' })).toBeTruthy();
    });
  });
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
      expect(rowsAfterLastSeenSort[2].textContent).toContain(
        'What structure anchors most plants in the ground?'
      );
      expect(rowsAfterLastSeenSort[3].textContent).toContain('What is the capital of Canada?');
      expect(rowsAfterLastSeenSort[3].textContent).toContain('Never');
    });
  });
});

describe('EditorDrawer', () => {
  it('shows type-specific ghost text in create mode', async () => {
    const user = userEvent.setup();
    const modules: ModuleNode[] = [
      {
        id: 1,
        title: 'Geography',
        slug: 'geography',
        full_slug: 'geography',
        instruction: '',
        children: []
      }
    ];

    render(EditorDrawer, {
      props: {
        open: true,
        modules,
        defaultModuleId: 1,
        editingQuestion: null,
        saving: false,
        onClose: vi.fn(),
        onSave: vi.fn()
      }
    });

    expect(screen.getByPlaceholderText('What is the capital of Norway?')).toBeTruthy();
    expect(screen.getByPlaceholderText('oslo')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Question type'), 'multi_text');
    expect(screen.getByPlaceholderText('Name the two rivers that meet at Khartoum.')).toBeTruthy();
    expect(screen.getByPlaceholderText('white nile')).toBeTruthy();
    expect(screen.getByPlaceholderText('blue nile')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Question type'), 'ordered_multi');
    expect(screen.getByPlaceholderText('Name the stages in order.')).toBeTruthy();
    expect(screen.getByPlaceholderText('stage one')).toBeTruthy();
    expect(screen.getByPlaceholderText('stage two')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Question type'), 'inline_cloze');
    expect(screen.getByPlaceholderText('The [Amazon | Amazon River] flows through South America.')).toBeTruthy();
    expect(screen.getByPlaceholderText(/The derivative of/)).toBeTruthy();
    expect(screen.getByPlaceholderText('x^2')).toBeTruthy();
    expect(screen.getByPlaceholderText('.')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Question type'), 'computed_text');
    expect(screen.getByPlaceholderText(/\$m=\[1-10\]\*100\$/)).toBeTruthy();
    expect(screen.getByPlaceholderText('$m/v$ ml')).toBeTruthy();
    expect(screen.getByText('QML')).toBeTruthy();
  });

  it('shows dense revision fields and aggregated incorrect answers without duplicate module UI', () => {
    const modules: ModuleNode[] = [
      {
        id: 1,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        instruction: '',
        children: [
          {
            id: 2,
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            instruction: '',
            children: [
              {
                id: 3,
                title: 'noun2en',
                slug: 'noun2en',
                full_slug: 'norwegian/vocabulary/noun2en',
                instruction: 'Translate the Norwegian term into English.',
                children: []
              }
            ]
          }
        ]
      }
    ];

    render(EditorDrawer, {
      props: {
        open: true,
        modules,
        editingQuestion: {
          question_id: 30,
          module_id: 3,
          module_full_slug: 'norwegian/vocabulary/noun2en',
          prompt: 'hund',
          prompt_preview: 'hund',
          question_type: 'single_text',
          rank: 1,
          attempts: 4,
          correct_percentage: 0.5,
          last_asked_at: '2026-04-04T09:00:00Z',
          review_flag: true,
          accepted_answers: [['dog']],
          segments: [],
          schedule: {
            bucket: 'hot0',
            logical_bucket: 'unseen',
            recovery_streak: 0,
            interval_step: 0,
            last_incorrect_at: '2026-04-04T08:00:00Z',
            next_due_at: null,
            retry_pending: false
          },
          recent_incorrect_answers: [
            {
              answer_text: 'hound',
              count: 3,
              latest_answered_at: '2026-04-04T08:00:00Z'
            },
            {
              answer_text: 'puppy',
              count: 1,
              latest_answered_at: '2026-04-03T08:00:00Z'
            }
          ]
        },
        saving: false,
        onClose: vi.fn(),
        onSave: vi.fn()
      }
    });

    expect(screen.getByText('Previously incorrect answers')).toBeTruthy();
    expect(screen.getByText('hound')).toBeTruthy();
    expect(screen.getByText('puppy')).toBeTruthy();
    expect(screen.getByText('3')).toBeTruthy();
    expect(screen.getByText('1')).toBeTruthy();
    expect(screen.getByText('Module')).toBeTruthy();
    expect(screen.queryByText('Module path')).toBeNull();
    expect(screen.queryByText('Create module inline')).toBeNull();
    expect(screen.queryByText('Flag this question for manual review')).toBeNull();
  });
});

describe('ModuleMenu', () => {
  it('reveals submodules on click, selects parent and child modules, and collapses other top-level branches', async () => {
    const user = userEvent.setup();
    const selectSpy = vi.fn();
    const modules: ModuleNode[] = [
      {
        id: 1,
        title: 'Biology',
        slug: 'biology',
        full_slug: 'biology',
        instruction: '',
        children: [
          {
            id: 2,
            title: 'Plants',
            slug: 'plants',
            full_slug: 'biology/plants',
            instruction: 'Name the plant concept.',
            children: []
          }
        ]
      },
      {
        id: 3,
        title: 'Geography',
        slug: 'geography',
        full_slug: 'geography',
        instruction: '',
        children: [
          {
            id: 4,
            title: 'Rivers',
            slug: 'rivers',
            full_slug: 'geography/rivers',
            instruction: 'Name the river system.',
            children: []
          }
        ]
      }
    ];

    const view = render(ModuleMenu, {
      props: {
        open: true,
        modules,
        selectedModuleId: null,
        selectedModuleLabel: 'Biology',
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

    await view.rerender({
      open: true,
      modules,
      selectedModuleId: 2,
      selectedModuleLabel: 'Plants',
      onClose: vi.fn(),
      onSelect: selectSpy
    });

    await user.click(screen.getByRole('button', { name: /Geography geography/i }));
    expect(selectSpy).toHaveBeenCalledWith(3, true);

    await view.rerender({
      open: true,
      modules,
      selectedModuleId: 3,
      selectedModuleLabel: 'Geography',
      onClose: vi.fn(),
      onSelect: selectSpy
    });

    expect(screen.queryByText('Plants')).toBeNull();
    expect(screen.getByText('Rivers')).toBeTruthy();
  });
});

describe('AdminPage', () => {
  it('creates users from admin, creates a module, and offers leaf-module import', async () => {
    const user = userEvent.setup();
    const createUserSpy = vi.fn().mockResolvedValue({
      id: 9,
      handle: 'ignazio',
      display_name: 'Ignazio',
      created_at: '2026-04-05T10:00:00Z'
    });
    const createSpy = vi.fn().mockResolvedValue({
      id: 8,
      title: 'Norwegian',
      slug: 'norwegian',
      full_slug: 'norwegian',
      instruction: 'Translate the Norwegian term into English.',
      children: []
    });
    const openImportSpy = vi.fn();
    const modules: ModuleNode[] = [
      {
        id: 1,
        title: 'Nursing',
        slug: 'nursing',
        full_slug: 'nursing',
        instruction: '',
        children: [
          {
            id: 2,
            title: 'Checks',
            slug: 'checks',
            full_slug: 'nursing/checks',
            instruction: 'List the safety checks in order.',
            children: []
          },
          {
            id: 3,
            title: 'Definitions',
            slug: 'definitions',
            full_slug: 'nursing/definitions',
            instruction: 'Define the nursing term in plain language.',
            children: []
          }
        ]
      }
    ];

    render(AdminPage, {
      props: {
        modules,
        users: [],
        activeUser: null,
        selectedModuleId: 2,
        onCreateUser: createUserSpy,
        onCreateModule: createSpy,
        onOpenImport: openImportSpy
      }
    });

    expect(screen.queryByText('Current modules')).toBeNull();
    expect(screen.getByRole('heading', { name: 'Create Module Path' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Create User' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Import QML' })).toBeTruthy();
    expect(screen.queryByText('Users')).toBeNull();
    expect(screen.queryByText('Question import')).toBeNull();
    expect(screen.getAllByText(/Imports will create questions directly in/).length).toBeGreaterThan(0);

    expect(screen.getByRole('button', { name: 'Create Module' }).className).toContain('primary-button');
    expect(screen.getByRole('button', { name: 'Create User' }).className).toContain('primary-button');
    expect(screen.getByRole('button', { name: 'Import QML' }).className).toContain('primary-button');

    await user.type(screen.getByPlaceholderText('ignazio'), 'ignazio');
    await user.type(screen.getByPlaceholderText('Ignazio'), 'Ignazio');
    await user.click(screen.getByRole('button', { name: 'Create User' }));
    expect(createUserSpy).toHaveBeenCalledWith({
      handle: 'ignazio',
      display_name: 'Ignazio'
    });
    expect(await screen.findByText('User ready: Ignazio.')).toBeTruthy();

    const selects = screen.getAllByRole('combobox');
    await user.selectOptions(selects[1], '3');
    await user.click(screen.getByRole('button', { name: 'Import QML' }));
    expect(openImportSpy).toHaveBeenCalledWith(3);

    await user.type(screen.getByPlaceholderText('norwegian/vocabulary/nouns_to_english'), 'Vocabulary');
    await user.selectOptions(selects[0], '1');
    await user.type(
      screen.getByPlaceholderText('Translate each Norwegian noun into English.'),
      'Use the Norwegian term as the prompt.'
    );
    await user.click(screen.getByRole('button', { name: 'Create Module' }));

    expect(createSpy).toHaveBeenCalledWith({
      title: 'Vocabulary',
      parent_id: 1,
      instruction: 'Use the Norwegian term as the prompt.'
    });

    expect(await screen.findByText('Module path ready: norwegian.')).toBeTruthy();
  });
});

describe('ImportDrawer', () => {
  it('revalidates edited unresolved rows, supports discard, and returns to the start state after commit', async () => {
    const user = userEvent.setup();
    const revalidateSpy = vi.fn().mockResolvedValue(undefined);
    const commitSpy = vi.fn().mockResolvedValue(undefined);
    const moduleNode: ModuleNode = {
      id: 12,
      title: 'noun2en',
      slug: 'noun2en',
      full_slug: 'norwegian/vocabulary/noun2en',
      instruction: 'Translate each Norwegian noun into English.',
      children: []
    };
    const result: QuestionImportResult = {
      ready_to_commit: false,
      valid_row_count: 2,
      skipped_duplicate_count: 1,
      skipped_rows: [
        {
          row_number: 1,
          qml_line: 'hund [dog]',
          reason: 'Prompt already exists in this leaf module.',
          inferred_type: 'single_text'
        }
      ],
      report_text: 'row 2 | needs fix | Question lines cannot be blank. | ',
      committed: false,
      committed_count: 0,
      unresolved_rows: [
        {
          row_number: 2,
          qml_line: 'ordered: stage one',
          issues: ['Question lines cannot be blank.'],
          inferred_type: null
        },
        {
          row_number: 4,
          qml_line: 'ordered: stage alpha',
          issues: ['Question lines cannot be blank.'],
          inferred_type: null
        }
      ]
    };

    const view = render(ImportDrawer, {
      props: {
        open: true,
        moduleNode,
        result,
        busy: false,
        onClose: vi.fn(),
        onStartImport: vi.fn(),
        onRevalidate: revalidateSpy,
        onCommit: commitSpy
      }
    });

    expect(screen.getByDisplayValue('ordered: stage one')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Discard row 2' })).toBeTruthy();

    const rowInputs = view.getAllByRole('textbox');
    const unresolvedInput = rowInputs.find(
      (input) => (input as HTMLInputElement).value === 'ordered: stage one'
    ) as HTMLInputElement;
    await user.clear(unresolvedInput);
    await user.type(unresolvedInput, 'ordered: stage one ; stage two');
    await user.click(screen.getByRole('button', { name: 'Revalidate Rows' }));

    expect(revalidateSpy).toHaveBeenCalledWith([
      { row_number: 1, qml_line: 'hund [dog]' },
      { row_number: 2, qml_line: 'ordered: stage one ; stage two' },
      { row_number: 4, qml_line: 'ordered: stage alpha' }
    ]);

    await user.click(screen.getByRole('button', { name: 'Discard row 4' }));
    expect(revalidateSpy).toHaveBeenLastCalledWith([
      { row_number: 1, qml_line: 'hund [dog]' },
      { row_number: 2, qml_line: 'ordered: stage one ; stage two' }
    ]);

    await view.rerender({
      open: true,
      moduleNode,
      result: {
        ...result,
        ready_to_commit: true,
        valid_row_count: 3,
        skipped_duplicate_count: 1,
        skipped_rows: result.skipped_rows,
        report_text: 'All remaining rows are valid. Commit to save them.',
        unresolved_rows: []
      },
      busy: false,
      onClose: vi.fn(),
      onStartImport: vi.fn(),
      onRevalidate: revalidateSpy,
      onCommit: commitSpy
    });

    expect(screen.queryByRole('button', { name: 'Discard row 2' })).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Commit Import' }));
    expect(commitSpy).toHaveBeenCalledWith([
      { row_number: 1, qml_line: 'hund [dog]' },
      { row_number: 2, qml_line: 'ordered: stage one ; stage two' }
    ]);

    await view.rerender({
      open: true,
      moduleNode,
      result: null,
      busy: false,
      onClose: vi.fn(),
      onStartImport: vi.fn(),
      onRevalidate: revalidateSpy,
      onCommit: commitSpy
    });

    expect(screen.getByRole('button', { name: 'Start Import' })).toBeTruthy();
  });
});
