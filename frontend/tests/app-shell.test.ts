import './test-support';

import { render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../src/lib/api', () => ({
  commitQuestionImport: vi.fn(),
  createModule: vi.fn(),
  createQuestion: vi.fn(),
  createQuizSession: vi.fn(),
  createUser: vi.fn(),
  deleteQuestion: vi.fn(),
  getHealth: vi.fn(),
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
import Header from '../src/components/Header.svelte';
import ModuleMenu from '../src/components/ModuleMenu.svelte';
import * as api from '../src/lib/api';
import { persistImportSession } from '../src/lib/app-state';
import { ensureModulePath } from '../src/lib/module-paths';
import type { ModuleNode, QuestionImportResult, StatsResponse, User } from '../src/lib/types';

function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
} {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

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
        handle: 'user-a',
        display_name: 'User A',
        created_at: '2026-04-05T10:00:00Z'
      },
      {
        id: 2,
        handle: 'user-b',
        display_name: 'User B',
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

    const avatarButton = screen.getByRole('button', { name: 'Open user menu for User A' });
    expect(avatarButton.textContent).toBe('U');
    expect(screen.queryByRole('button', { name: /create user/i })).toBeNull();
    expect(screen.queryByRole('combobox', { name: 'Active user' })).toBeNull();

    await user.click(avatarButton);
    expect(screen.getByRole('menu', { name: 'User menu' })).toBeTruthy();
    await user.click(screen.getByRole('menuitemradio', { name: /User B/i }));
    expect(selectSpy).toHaveBeenCalledWith(2);
  });
});

describe('App', () => {
  it('uses the review toggle as local table visibility instead of reloading stats', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/stats');

    const modules: ModuleNode[] = [
      {
        id: 1,
        title: 'Biology',
        slug: 'biology',
        full_slug: 'biology',
        instruction: '',
        children: []
      }
    ];
    const users: User[] = [
      {
        id: 1,
        handle: 'user-a',
        display_name: 'User A',
        created_at: '2026-04-05T10:00:00Z'
      }
    ];
    const stats: StatsResponse = {
      summary: {
        total_questions: 2,
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
          module_id: 1,
          module_full_slug: 'biology',
          prompt: 'What structure anchors most plants in the ground?',
          prompt_preview: 'What structure anchors most plants in the ground?',
          question_type: 'single_text',
          rank: 1,
          attempts: 1,
          correct_percentage: 1,
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
        },
        {
          question_id: 2,
          module_id: 1,
          module_full_slug: 'biology',
          prompt: 'What is chlorophyll used for?',
          prompt_preview: 'What is chlorophyll used for?',
          question_type: 'single_text',
          rank: 2,
          attempts: 0,
          correct_percentage: 0,
          last_asked_at: null,
          review_flag: false,
          accepted_answers: [['photosynthesis']],
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
    };

    vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', instance_key: 'local-dev' });
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue(users);
    vi.mocked(api.getStats).mockResolvedValue(stats);

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Questions' })).toBeTruthy();
    });

    expect(api.getStats).toHaveBeenCalledTimes(1);
    expect(api.getStats).toHaveBeenCalledWith(1, 1);
    expect(screen.queryByRole('heading', { name: 'Review Questions' })).toBeNull();

    await user.click(screen.getByRole('checkbox', { name: 'Review only' }));

    expect(screen.getByRole('heading', { name: 'Review Questions' })).toBeTruthy();
    expect(api.getStats).toHaveBeenCalledTimes(1);
  });

  it('switches users from the header menu in the full app and updates persisted state', async () => {
    const user = userEvent.setup();
    const modules: ModuleNode[] = [
      {
        id: 1,
        title: 'Biology',
        slug: 'biology',
        full_slug: 'biology',
        instruction: '',
        children: []
      }
    ];
    const users: User[] = [
      {
        id: 1,
        handle: 'user-a',
        display_name: 'User A',
        created_at: '2026-04-05T10:00:00Z'
      },
      {
        id: 2,
        handle: 'user-b',
        display_name: 'User B',
        created_at: '2026-04-05T10:05:00Z'
      }
    ];

    vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', instance_key: 'local-dev' });
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue(users);

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Open user menu for User A' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Open user menu for User A' }));
    await user.click(screen.getByRole('menuitemradio', { name: /User B/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Open user menu for User B' })).toBeTruthy();
    });
    expect(window.localStorage.getItem('learning.local-dev.active-user-handle')).toBe('user-b');
  });

  it('persists the selected module and active user across remounts within the same app instance', async () => {
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
        handle: 'user-a',
        display_name: 'User A',
        created_at: '2026-04-05T10:00:00Z'
      },
      {
        id: 2,
        handle: 'user-b',
        display_name: 'User B',
        created_at: '2026-04-05T10:05:00Z'
      }
    ];

    vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', instance_key: 'local-dev' });
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

    await user.click(screen.getByRole('button', { name: 'Open user menu for User A' }));
    await user.click(screen.getByRole('menuitemradio', { name: /User B/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Open user menu for User B' })).toBeTruthy();
    });
    expect(window.localStorage.getItem('learning.local-dev.selected-module-full-slug')).toBe('geography');
    expect(window.localStorage.getItem('learning.local-dev.active-user-handle')).toBe('user-b');
    expect(window.localStorage.getItem('learning.selected-module-id')).toBeNull();
    expect(window.localStorage.getItem('learning.active-user-id')).toBeNull();

    firstRender.unmount();

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Geography' })).toBeTruthy();
    });
    expect(screen.getByRole('button', { name: 'Open user menu for User B' })).toBeTruthy();
  });

  it('keeps remembered user and module separate for different app instances on the same origin', async () => {
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
        handle: 'user-a',
        display_name: 'User A',
        created_at: '2026-04-05T10:00:00Z'
      },
      {
        id: 2,
        handle: 'user-b',
        display_name: 'User B',
        created_at: '2026-04-05T10:05:00Z'
      }
    ];

    window.localStorage.setItem('learning.local-dev.active-user-handle', 'user-a');
    window.localStorage.setItem('learning.local-dev.selected-module-full-slug', 'biology');
    window.localStorage.setItem('learning.published.active-user-handle', 'user-b');
    window.localStorage.setItem('learning.published.selected-module-full-slug', 'geography');
    window.localStorage.setItem('learning.active-user-id', '999');
    window.localStorage.setItem('learning.selected-module-id', '999');

    vi.mocked(api.getHealth)
      .mockResolvedValueOnce({ status: 'ok', instance_key: 'local-dev' })
      .mockResolvedValueOnce({ status: 'ok', instance_key: 'published' });
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue(users);

    const firstRender = render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Biology' })).toBeTruthy();
    });
    expect(screen.getByRole('button', { name: 'Open user menu for User A' })).toBeTruthy();
    expect(window.localStorage.getItem('learning.active-user-id')).toBeNull();
    expect(window.localStorage.getItem('learning.selected-module-id')).toBeNull();

    firstRender.unmount();

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Geography' })).toBeTruthy();
    });
    expect(screen.getByRole('button', { name: 'Open user menu for User B' })).toBeTruthy();
  });

  it('restores import drawer progress from session storage after a refresh', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

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
                instruction: 'Translate each Norwegian noun into English.',
                children: []
              }
            ]
          }
        ]
      }
    ];
    const users: User[] = [
      {
        id: 1,
        handle: 'user-a',
        display_name: 'User A',
        created_at: '2026-04-05T10:00:00Z'
      }
    ];
    const restoredResult: QuestionImportResult = {
      ready_to_commit: true,
      rows: [{ row_number: 35, qml_line: 'mot [against | toward]' }],
      valid_row_count: 1,
      committable_row_numbers: [35],
      exact_duplicate_count: 0,
      review_rows: [
        {
          row_number: 35,
          qml_line: 'mot [against | toward]',
          status: 'duplicate',
          status_text: 'This prompt already exists in the target leaf.',
          editable: true,
          blocking: false,
          current_answer_blocks: ['against'],
          imported_answer_blocks: ['toward'],
          matched_questions: [
            {
              question_id: 8,
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              qml_line: 'mot [against]',
              answer_blocks: ['against']
            }
          ]
        }
      ],
      report_text: '1 row ready',
      committed: false,
      committed_count: 0
    };

    persistImportSession(window.sessionStorage, {
      instanceKey: 'local-dev',
      modules,
      open: true,
      targetModuleId: 3,
      qmlText: 'mot [against | toward]',
      rows: [{ row_number: 35, qml_line: 'mot [against | toward | opposite]' }],
      result: restoredResult
    });

    vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', instance_key: 'local-dev' });
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue(users);
    vi.mocked(api.validateQuestionImportRows).mockResolvedValue({
      ...restoredResult,
      rows: [{ row_number: 35, qml_line: 'mot [against | toward | opposite]' }]
    });
    vi.mocked(api.commitQuestionImport).mockResolvedValue({
      ...restoredResult,
      committed: true,
      committed_count: 1
    });

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Import Questions' })).toBeTruthy();
    });

    expect(screen.getByDisplayValue('mot [against | toward | opposite]')).toBeTruthy();
    expect(screen.getByText('1 review rows')).toBeTruthy();

    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(api.commitQuestionImport).toHaveBeenCalledWith(3, [{ row_number: 35, qml_line: 'mot [against | toward | opposite]' }]);
  });

  it('commits imports in 10-row chunks and shows determinate save progress', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

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
                instruction: 'Translate each Norwegian noun into English.',
                children: []
              }
            ]
          }
        ]
      }
    ];
    const users: User[] = [
      {
        id: 1,
        handle: 'user-a',
        display_name: 'User A',
        created_at: '2026-04-05T10:00:00Z'
      }
    ];
    const rows = Array.from({ length: 25 }, (_, index) => ({
      row_number: index + 1,
      qml_line: `ord ${index + 1} [answer ${index + 1}]`
    }));
    const importResult: QuestionImportResult = {
      ready_to_commit: true,
      rows,
      valid_row_count: 25,
      committable_row_numbers: rows.map((row) => row.row_number),
      exact_duplicate_count: 0,
      review_rows: [],
      report_text: '25 ready to commit',
      committed: false,
      committed_count: 0
    };

    persistImportSession(window.sessionStorage, {
      instanceKey: 'local-dev',
      modules,
      open: true,
      targetModuleId: 3,
      qmlText: rows.map((row) => row.qml_line).join('\n'),
      rows,
      result: importResult
    });

    const firstChunk = deferred<QuestionImportResult>();
    const secondChunk = deferred<QuestionImportResult>();
    const thirdChunk = deferred<QuestionImportResult>();

    vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', instance_key: 'local-dev' });
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue(users);
    vi.mocked(api.validateQuestionImportRows).mockResolvedValue(importResult);
    vi.mocked(api.commitQuestionImport)
      .mockImplementationOnce(() => firstChunk.promise)
      .mockImplementationOnce(() => secondChunk.promise)
      .mockImplementationOnce(() => thirdChunk.promise);

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Import Questions' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenNthCalledWith(1, 3, rows.slice(0, 10));
    });
    expect(screen.getByRole('button', { name: 'Saving 0/25' })).toBeTruthy();

    firstChunk.resolve({
      ...importResult,
      committed: true,
      committed_count: 10
    });
    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenNthCalledWith(2, 3, rows.slice(10, 20));
      expect(screen.getByRole('button', { name: 'Saving 10/25' })).toBeTruthy();
    });

    secondChunk.resolve({
      ...importResult,
      committed: true,
      committed_count: 10
    });
    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenNthCalledWith(3, 3, rows.slice(20, 25));
      expect(screen.getByRole('button', { name: 'Saving 20/25' })).toBeTruthy();
    });

    thirdChunk.resolve({
      ...importResult,
      committed: true,
      committed_count: 5
    });
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Import Questions' })).toBeNull();
    });
  });

  it('filters exact no-op duplicate revisions before chunked save', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

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
                instruction: 'Translate each Norwegian noun into English.',
                children: []
              }
            ]
          }
        ]
      }
    ];
    const users: User[] = [
      {
        id: 1,
        handle: 'user-a',
        display_name: 'User A',
        created_at: '2026-04-05T10:00:00Z'
      }
    ];
    const sessionResult: QuestionImportResult = {
      ready_to_commit: true,
      rows: [{ row_number: 1, qml_line: 'mot [toward]' }],
      valid_row_count: 1,
      committable_row_numbers: [1],
      exact_duplicate_count: 0,
      review_rows: [
        {
          row_number: 1,
          qml_line: 'mot [toward]',
          status: 'duplicate',
          status_text: 'This prompt already exists in the target leaf.',
          editable: true,
          blocking: false,
          current_answer_blocks: ['against'],
          imported_answer_blocks: ['toward'],
          matched_questions: [
            {
              question_id: 8,
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              qml_line: 'mot [against]',
              answer_blocks: ['against']
            }
          ]
        }
      ],
      report_text: '1 row ready',
      committed: false,
      committed_count: 0
    };
    const exactDuplicateResult: QuestionImportResult = {
      ready_to_commit: false,
      rows: [{ row_number: 1, qml_line: 'mot [against]' }],
      valid_row_count: 0,
      committable_row_numbers: [],
      exact_duplicate_count: 1,
      review_rows: [],
      report_text: '1 exact duplicates omitted',
      committed: false,
      committed_count: 0
    };

    persistImportSession(window.sessionStorage, {
      instanceKey: 'local-dev',
      modules,
      open: true,
      targetModuleId: 3,
      qmlText: 'mot [toward]',
      rows: [{ row_number: 1, qml_line: 'mot [against]' }],
      result: sessionResult
    });

    vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', instance_key: 'local-dev' });
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue(users);
    vi.mocked(api.validateQuestionImportRows).mockResolvedValue(exactDuplicateResult);

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Import Questions' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(screen.getByText('Nothing new to save.')).toBeTruthy();
    });
    expect(api.commitQuestionImport).not.toHaveBeenCalled();
  });

  it('keeps remaining rows open after a later chunk fails and revalidates them', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

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
                instruction: 'Translate each Norwegian noun into English.',
                children: []
              }
            ]
          }
        ]
      }
    ];
    const users: User[] = [
      {
        id: 1,
        handle: 'user-a',
        display_name: 'User A',
        created_at: '2026-04-05T10:00:00Z'
      }
    ];
    const rows = Array.from({ length: 15 }, (_, index) => ({
      row_number: index + 1,
      qml_line: `ord ${index + 1} [answer ${index + 1}]`
    }));
    const initialResult: QuestionImportResult = {
      ready_to_commit: true,
      rows,
      valid_row_count: 15,
      committable_row_numbers: rows.map((row) => row.row_number),
      exact_duplicate_count: 0,
      review_rows: [],
      report_text: '15 ready to commit',
      committed: false,
      committed_count: 0
    };
    const remainingRows = rows.slice(10);
    const remainingResult: QuestionImportResult = {
      ready_to_commit: false,
      rows: remainingRows,
      valid_row_count: 4,
      committable_row_numbers: [11, 13, 14, 15],
      exact_duplicate_count: 0,
      review_rows: [
        {
          row_number: 12,
          qml_line: 'broken row',
          status: 'invalid',
          status_text: 'Invalid QML: Question lines cannot be blank.',
          editable: true,
          blocking: true,
          current_answer_blocks: [],
          imported_answer_blocks: [],
          matched_questions: []
        }
      ],
      report_text: '4 ready to commit | 1 rows need review',
      committed: false,
      committed_count: 0
    };

    persistImportSession(window.sessionStorage, {
      instanceKey: 'local-dev',
      modules,
      open: true,
      targetModuleId: 3,
      qmlText: rows.map((row) => row.qml_line).join('\n'),
      rows,
      result: initialResult
    });

    vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', instance_key: 'local-dev' });
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue(users);
    vi.mocked(api.validateQuestionImportRows)
      .mockResolvedValueOnce(initialResult)
      .mockResolvedValueOnce(remainingResult);
    vi.mocked(api.commitQuestionImport)
      .mockResolvedValueOnce({
        ...initialResult,
        committed: true,
        committed_count: 10
      })
      .mockResolvedValueOnce({
        ...remainingResult,
        committed: false,
        committed_count: 0
      });

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Import Questions' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenNthCalledWith(1, 3, rows.slice(0, 10));
    });
    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenNthCalledWith(2, 3, rows.slice(10, 15));
    });
    await waitFor(() => {
      expect(api.validateQuestionImportRows).toHaveBeenNthCalledWith(2, 3, remainingRows);
      expect(screen.getByText('Saved 10 rows. Fix the highlighted rows to continue.')).toBeTruthy();
    });
    expect(screen.getByDisplayValue('ord 12 [answer 12]')).toBeTruthy();
    expect(screen.getByText('4 rows ready')).toBeTruthy();
    expect(screen.queryByDisplayValue('ord 1 [answer 1]')).toBeNull();
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
