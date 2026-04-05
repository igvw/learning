import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import AdminPage from '../src/components/AdminPage.svelte';
import EditorDrawer from '../src/components/EditorDrawer.svelte';
import Header from '../src/components/Header.svelte';
import ImportDrawer from '../src/components/ImportDrawer.svelte';
import QuizPage from '../src/components/QuizPage.svelte';
import ModuleMenu from '../src/components/ModuleMenu.svelte';
import StatsPage from '../src/components/StatsPage.svelte';
import { ensureModulePath } from '../src/lib/module-paths';
import type { ModuleNode, QuestionImportSession, QuizSession, StatsResponse, User } from '../src/lib/types';

afterEach(() => {
  cleanup();
});

describe('module paths', () => {
  it('creates only missing segments for slash-separated module paths', async () => {
    let moduleTree: ModuleNode[] = [
      {
        id: 1,
        source_id: 'norwegian',
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        instruction: '',
        ui_copy: {
          question_label: 'Question',
          answer_label: 'Answer',
          stats_title: 'Stats',
          review_title: 'Review'
        },
        children: [
          {
            id: 2,
            source_id: 'norwegian-vocabulary',
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            instruction: '',
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

    const createSpy = vi.fn(async ({ title, parent_id, instruction }) => {
      const id = title === 'nouns_to_english' ? 3 : 4;
      const fullSlug =
        title === 'nouns_to_english'
          ? 'norwegian/vocabulary/nouns_to_english'
          : 'norwegian/vocabulary/nouns_to_english/plural_forms';
      return {
        id,
        source_id: null,
        title,
        slug: title,
        full_slug: fullSlug,
        instruction,
        ui_copy: {
          question_label: 'Question',
          answer_label: 'Answer',
          stats_title: 'Stats',
          review_title: 'Review'
        },
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
                  source_id: null,
                  title: 'nouns_to_english',
                  slug: 'nouns_to_english',
                  full_slug: 'norwegian/vocabulary/nouns_to_english',
                  instruction: 'Translate to English.',
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
      instruction: 'Translate to English.',
      ui_copy: undefined
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
        created_at: '2026-04-05T10:00:00Z',
        disabled_at: null
      },
      {
        id: 2,
        handle: 'ingrid',
        display_name: 'Ingrid',
        created_at: '2026-04-05T10:05:00Z',
        disabled_at: null
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
          module_title: 'Capitals',
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
          module_title: 'Capitals',
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
          module_title: 'Capitals',
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
          module_id: 3,
          module_title: 'Rivers',
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
          module_id: 2,
          module_title: 'Animals',
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
          module_full_slug: 'biology/plants',
          prompt: 'What structure anchors most plants in the ground?',
          prompt_preview: 'What structure anchors most plants in the ground?',
          question_type: 'single_text',
          rank: 2,
          attempts: 3,
          correct_percentage: 2 / 3,
          last_asked_at: null,
          review_flag: true,
          accepted_answers: [['roots']],
          slot_prompts: [],
          segments: [],
          schedule: {
            bucket: 'hot',
            recovery_streak: 1,
            interval_step: 0,
            last_incorrect_at: '2026-04-04T08:00:00Z',
            next_due_at: null
          },
          recent_incorrect_answers: [
            {
              submitted_answer: ['stems'],
              answered_at: '2026-04-04T08:00:00Z'
            }
          ]
        },
        {
          question_id: 51,
          module_id: 5,
          module_title: 'Capitals',
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
          slot_prompts: [],
          segments: [],
          schedule: {
            bucket: 'backlog_seen_correct',
            recovery_streak: null,
            interval_step: null,
            last_incorrect_at: null,
            next_due_at: null
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

describe('EditorDrawer', () => {
  it('shows full module path and recent incorrect answers without inline module creation or review checkbox', () => {
    const modules: ModuleNode[] = [
      {
        id: 1,
        source_id: 'norwegian',
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        instruction: '',
        ui_copy: {
          question_label: 'Question',
          answer_label: 'Answer',
          stats_title: 'Stats',
          review_title: 'Review'
        },
        children: [
          {
            id: 2,
            source_id: 'norwegian-vocabulary',
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            instruction: '',
            ui_copy: {
              question_label: 'Question',
              answer_label: 'Answer',
              stats_title: 'Stats',
              review_title: 'Review'
            },
            children: [
              {
                id: 3,
                source_id: 'norwegian-vocabulary-noun2en',
                title: 'noun2en',
                slug: 'noun2en',
                full_slug: 'norwegian/vocabulary/noun2en',
                instruction: 'Translate the Norwegian term into English.',
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
          module_title: 'noun2en',
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
          slot_prompts: [],
          segments: [],
          schedule: {
            bucket: 'hot',
            recovery_streak: 0,
            interval_step: 0,
            last_incorrect_at: '2026-04-04T08:00:00Z',
            next_due_at: null
          },
          recent_incorrect_answers: [
            {
              submitted_answer: ['hound'],
              answered_at: '2026-04-04T08:00:00Z'
            },
            {
              submitted_answer: ['puppy'],
              answered_at: '2026-04-03T08:00:00Z'
            }
          ]
        },
        saving: false,
        onClose: vi.fn(),
        onSave: vi.fn()
      }
    });

    expect(screen.getByText('norwegian/vocabulary/noun2en')).toBeTruthy();
    expect(screen.getByText('Previously incorrect answers')).toBeTruthy();
    expect(screen.getByText('hound')).toBeTruthy();
    expect(screen.getByText('puppy')).toBeTruthy();
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
        source_id: 'biology',
        title: 'Biology',
        slug: 'biology',
        full_slug: 'biology',
        instruction: '',
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
            instruction: 'Name the plant concept.',
            ui_copy: {
              question_label: 'Question',
              answer_label: 'Answer',
              stats_title: 'Stats',
              review_title: 'Review'
            },
            children: []
          }
        ]
      },
      {
        id: 3,
        source_id: 'geography',
        title: 'Geography',
        slug: 'geography',
        full_slug: 'geography',
        instruction: '',
        ui_copy: {
          question_label: 'Question',
          answer_label: 'Answer',
          stats_title: 'Stats',
          review_title: 'Review'
        },
        children: [
          {
            id: 4,
            source_id: 'geography-rivers',
            title: 'Rivers',
            slug: 'rivers',
            full_slug: 'geography/rivers',
            instruction: 'Name the river system.',
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
      created_at: '2026-04-05T10:00:00Z',
      disabled_at: null
    });
    const createSpy = vi.fn().mockResolvedValue({
      id: 8,
      source_id: null,
      title: 'Norwegian',
      slug: 'norwegian',
      full_slug: 'norwegian',
      instruction: 'Translate the Norwegian term into English.',
      ui_copy: {
        question_label: 'Question',
        answer_label: 'Answer',
        stats_title: 'Stats',
        review_title: 'Review'
      },
      children: []
    });
    const openImportSpy = vi.fn();
    const modules: ModuleNode[] = [
      {
        id: 1,
        source_id: 'nursing',
        title: 'Nursing',
        slug: 'nursing',
        full_slug: 'nursing',
        instruction: '',
        ui_copy: {
          question_label: 'Question',
          answer_label: 'Answer',
          stats_title: 'Stats',
          review_title: 'Review'
        },
        children: [
          {
            id: 2,
            source_id: 'nursing-checks',
            title: 'Checks',
            slug: 'checks',
            full_slug: 'nursing/checks',
            instruction: 'List the safety checks in order.',
            ui_copy: {
              question_label: 'Question',
              answer_label: 'Answer',
              stats_title: 'Stats',
              review_title: 'Review'
            },
            children: []
          },
          {
            id: 3,
            source_id: 'nursing-definitions',
            title: 'Definitions',
            slug: 'definitions',
            full_slug: 'nursing/definitions',
            instruction: 'Define the nursing term in plain language.',
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

    render(AdminPage, {
      props: {
        modules,
        users: [],
        activeUser: null,
        onCreateUser: createUserSpy,
        onCreateModule: createSpy,
        onOpenImport: openImportSpy
      }
    });

    expect(screen.queryByText('Current modules')).toBeNull();
    expect(screen.getAllByText(/Uploads will create questions directly in/).length).toBeGreaterThan(0);
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
    await user.click(screen.getByRole('button', { name: 'Import CSV' }));
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
    const discardSpy = vi.fn().mockResolvedValue(undefined);
    const commitSpy = vi.fn().mockResolvedValue(undefined);
    const moduleNode: ModuleNode = {
      id: 12,
      source_id: 'norwegian-vocabulary-noun2en',
      title: 'noun2en',
      slug: 'noun2en',
      full_slug: 'norwegian/vocabulary/noun2en',
      instruction: 'Translate each Norwegian noun into English.',
      ui_copy: {
        question_label: 'Question',
        answer_label: 'Answer',
        stats_title: 'Stats',
        review_title: 'Review'
      },
      children: []
    };
    const session: QuestionImportSession = {
      session_id: 77,
      expires_at: '2026-04-06T10:00:00Z',
      ready_to_commit: false,
      staged_valid_count: 2,
      report_text: 'row 2 | Prompt already exists in this leaf module. | hund,dog',
      committed: false,
      committed_count: 0,
      unresolved_rows: [
        {
          row_number: 2,
          csv_line: 'hund,dog',
          issues: ['Prompt already exists in this leaf module.'],
          inferred_type: 'single_text'
        },
        {
          row_number: 4,
          csv_line: 'katt,cat',
          issues: ['Prompt duplicates another kept row in this upload.'],
          inferred_type: 'single_text'
        }
      ]
    };

    const view = render(ImportDrawer, {
      props: {
        open: true,
        moduleNode,
        session,
        busy: false,
        onClose: vi.fn(),
        onStartImport: vi.fn(),
        onRevalidate: revalidateSpy,
        onDiscardRow: discardSpy,
        onCommit: commitSpy
      }
    });

    expect(screen.getByText('prompt,answers')).toBeTruthy();
    expect(screen.getByDisplayValue('hund,dog')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Discard row 2' })).toBeTruthy();

    const rowInputs = view.getAllByRole('textbox');
    const unresolvedInput = rowInputs.find((input) => (input as HTMLInputElement).value === 'hund,dog') as HTMLInputElement;
    await user.clear(unresolvedInput);
    await user.type(unresolvedInput, 'hund,hound');
    await user.click(screen.getByRole('button', { name: 'Revalidate Rows' }));

    expect(revalidateSpy).toHaveBeenCalledWith([
      { row_number: 2, csv_line: 'hund,hound' },
      { row_number: 4, csv_line: 'katt,cat' }
    ]);

    await user.click(screen.getByRole('button', { name: 'Discard row 4' }));
    expect(discardSpy).toHaveBeenCalledWith(4);

    await view.rerender({
      open: true,
      moduleNode,
      session: {
        ...session,
        ready_to_commit: true,
        staged_valid_count: 3,
        report_text: 'All remaining rows are valid. Commit to save them.',
        unresolved_rows: []
      },
      busy: false,
      onClose: vi.fn(),
      onStartImport: vi.fn(),
      onRevalidate: revalidateSpy,
      onDiscardRow: discardSpy,
      onCommit: commitSpy
    });

    expect(screen.queryByRole('button', { name: 'Discard row 2' })).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Commit Import' }));
    expect(commitSpy).toHaveBeenCalled();

    await view.rerender({
      open: true,
      moduleNode,
      session: null,
      busy: false,
      onClose: vi.fn(),
      onStartImport: vi.fn(),
      onRevalidate: revalidateSpy,
      onDiscardRow: discardSpy,
      onCommit: commitSpy
    });

    expect(screen.getByRole('button', { name: 'Start Import' })).toBeTruthy();
  });
});
