import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../src/lib/api', () => ({
  bootstrapAdmin: vi.fn(),
  commitQuestionImport: vi.fn(),
  createDemoSession: vi.fn(),
  createModule: vi.fn(),
  createQuestion: vi.fn(),
  createQuizSession: vi.fn(),
  createUser: vi.fn(),
  deleteQuestion: vi.fn(),
  getCurrentActor: vi.fn(),
  getHealth: vi.fn(),
  getModerationQueue: vi.fn(),
  getModulesTree: vi.fn(),
  getMyContributions: vi.fn(),
  getStats: vi.fn(),
  getUsers: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  reviewModule: vi.fn(),
  reviewQuestion: vi.fn(),
  reviewQuestionRevision: vi.fn(),
  reviseQuestion: vi.fn(),
  setQuestionReviewFlag: vi.fn(),
  submitQuizAnswer: vi.fn(),
  updateModule: vi.fn(),
  updateUserPassword: vi.fn(),
  updateUserRole: vi.fn(),
  validateQuestionImportRows: vi.fn(),
  validateQuestionImportText: vi.fn()
}));

import App from '../src/App.svelte';
import * as api from '../src/lib/api';
import { persistImportSession } from '../src/lib/app-state';
import {
  buildAuthActor,
  buildStatsResponse,
  buildImportResult,
  buildImportReviewRow,
  buildImportRow,
  buildModerationQueue,
  buildModuleNode,
  buildUser
} from './builders';

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

function mockAuthenticatedAdmin(modules: ReturnType<typeof buildModuleNode>[]) {
  vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', instance_key: 'local-dev', bootstrap_required: false });
  vi.mocked(api.getCurrentActor).mockResolvedValue(
    buildAuthActor({
      handle: 'admin',
      display_name: 'Admin',
      role: 'admin'
    })
  );
  vi.mocked(api.getModulesTree).mockResolvedValue(modules);
  vi.mocked(api.getUsers).mockResolvedValue([buildUser({ id: 1, handle: 'admin', display_name: 'Admin', role: 'admin' })]);
  vi.mocked(api.getModerationQueue).mockResolvedValue(buildModerationQueue());
}

describe('import flow', () => {
  it('restores import drawer progress from session storage after a refresh', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

    const modules = [
      buildModuleNode({
        id: 1,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        children: [
          buildModuleNode({
            id: 2,
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            children: [
              buildModuleNode({
                id: 3,
                title: 'noun2en',
                slug: 'noun2en',
                full_slug: 'norwegian/vocabulary/noun2en',
                instruction: 'Translate each Norwegian noun into English.'
              })
            ]
          })
        ]
      })
    ];
    const restoredResult = buildImportResult({
      ready_to_commit: true,
      rows: [buildImportRow({ row_number: 35, qml_line: 'mot [against | toward]' })],
      valid_row_count: 1,
      committable_row_numbers: [35],
      review_rows: [
        buildImportReviewRow({
          row_number: 35,
          qml_line: 'mot [against | toward]',
          matched_questions: [
            {
              question_id: 8,
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              qml_line: 'mot [against]',
              answer_blocks: ['against']
            }
          ]
        })
      ],
      report_text: '1 row ready'
    });

    persistImportSession(window.sessionStorage, {
      instanceKey: 'local-dev',
      modules,
      open: true,
      targetModuleId: 3,
      qmlText: 'mot [against | toward]',
      rows: [buildImportRow({ row_number: 35, qml_line: 'mot [against | toward | opposite]' })],
      result: restoredResult
    });

    mockAuthenticatedAdmin(modules);
    vi.mocked(api.validateQuestionImportRows).mockResolvedValue({
      ...restoredResult,
      rows: [buildImportRow({ row_number: 35, qml_line: 'mot [against | toward | opposite]' })]
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

    expect(api.commitQuestionImport).toHaveBeenCalledWith(3, [
      { row_number: 35, qml_line: 'mot [against | toward | opposite]' }
    ]);
  });

  it('commits imports in 50-row chunks and shows determinate save progress', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

    const modules = [
      buildModuleNode({
        id: 1,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        children: [
          buildModuleNode({
            id: 2,
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            children: [
              buildModuleNode({
                id: 3,
                title: 'noun2en',
                slug: 'noun2en',
                full_slug: 'norwegian/vocabulary/noun2en',
                instruction: 'Translate each Norwegian noun into English.'
              })
            ]
          })
        ]
      })
    ];
    const rows = Array.from({ length: 120 }, (_, index) => buildImportRow({
      row_number: index + 1,
      qml_line: `ord ${index + 1} [answer ${index + 1}]`
    }));
    const importResult = buildImportResult({
      ready_to_commit: true,
      rows,
      valid_row_count: 120,
      committable_row_numbers: rows.map((row) => row.row_number),
      report_text: '120 ready to commit'
    });

    persistImportSession(window.sessionStorage, {
      instanceKey: 'local-dev',
      modules,
      open: true,
      targetModuleId: 3,
      qmlText: rows.map((row) => row.qml_line).join('\n'),
      rows,
      result: importResult
    });

    const firstChunk = deferred<typeof importResult>();
    const secondChunk = deferred<typeof importResult>();
    const thirdChunk = deferred<typeof importResult>();

    mockAuthenticatedAdmin(modules);
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
      expect(api.commitQuestionImport).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByRole('button', { name: 'Saving 0/120' })).toBeTruthy();

    firstChunk.resolve({ ...importResult, committed: true, committed_count: 50 });
    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenCalledTimes(2);
      expect(screen.getByRole('button', { name: 'Saving 50/120' })).toBeTruthy();
    });

    secondChunk.resolve({ ...importResult, committed: true, committed_count: 50 });
    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenCalledTimes(3);
      expect(screen.getByRole('button', { name: 'Saving 100/120' })).toBeTruthy();
    });

    thirdChunk.resolve({ ...importResult, committed: true, committed_count: 20 });
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Import Questions' })).toBeNull();
    });
  });

  it('filters exact no-op duplicate revisions before chunked save', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

    const modules = [
      buildModuleNode({
        id: 1,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        children: [
          buildModuleNode({
            id: 2,
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            children: [
              buildModuleNode({
                id: 3,
                title: 'noun2en',
                slug: 'noun2en',
                full_slug: 'norwegian/vocabulary/noun2en',
                instruction: 'Translate each Norwegian noun into English.'
              })
            ]
          })
        ]
      })
    ];
    const sessionResult = buildImportResult({
      ready_to_commit: true,
      rows: [buildImportRow({ row_number: 1, qml_line: 'mot [toward]' })],
      valid_row_count: 1,
      committable_row_numbers: [1],
      review_rows: [
        buildImportReviewRow({
          row_number: 1,
          qml_line: 'mot [toward]',
          matched_questions: [
            {
              question_id: 8,
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              qml_line: 'mot [against]',
              answer_blocks: ['against']
            }
          ]
        })
      ],
      report_text: '1 row ready'
    });
    const exactDuplicateResult = buildImportResult({
      rows: [buildImportRow({ row_number: 1, qml_line: 'mot [against]' })],
      exact_duplicate_count: 1,
      report_text: '1 exact duplicates omitted'
    });

    persistImportSession(window.sessionStorage, {
      instanceKey: 'local-dev',
      modules,
      open: true,
      targetModuleId: 3,
      qmlText: 'mot [toward]',
      rows: [buildImportRow({ row_number: 1, qml_line: 'mot [against]' })],
      result: sessionResult
    });

    mockAuthenticatedAdmin(modules);
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

    const modules = [
      buildModuleNode({
        id: 1,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        children: [
          buildModuleNode({
            id: 2,
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            children: [
              buildModuleNode({
                id: 3,
                title: 'noun2en',
                slug: 'noun2en',
                full_slug: 'norwegian/vocabulary/noun2en',
                instruction: 'Translate each Norwegian noun into English.'
              })
            ]
          })
        ]
      })
    ];
    const rows = Array.from({ length: 55 }, (_, index) => buildImportRow({
      row_number: index + 1,
      qml_line: `ord ${index + 1} [answer ${index + 1}]`
    }));
    const initialResult = buildImportResult({
      ready_to_commit: true,
      rows,
      valid_row_count: 55,
      committable_row_numbers: rows.map((row) => row.row_number),
      report_text: '55 ready to commit'
    });
    const remainingRows = rows.slice(50);
    const remainingResult = buildImportResult({
      rows: remainingRows,
      valid_row_count: 4,
      committable_row_numbers: [51, 53, 54, 55],
      review_rows: [
        buildImportReviewRow({
          row_number: 52,
          qml_line: 'broken row',
          status: 'invalid',
          status_text: 'Invalid QML: Question lines cannot be blank.',
          blocking: true,
          current_answer_blocks: [],
          imported_answer_blocks: [],
          matched_questions: []
        })
      ],
      report_text: '4 ready to commit | 1 rows need review'
    });

    persistImportSession(window.sessionStorage, {
      instanceKey: 'local-dev',
      modules,
      open: true,
      targetModuleId: 3,
      qmlText: rows.map((row) => row.qml_line).join('\n'),
      rows,
      result: initialResult
    });

    mockAuthenticatedAdmin(modules);
    vi.mocked(api.validateQuestionImportRows)
      .mockResolvedValueOnce(initialResult)
      .mockResolvedValueOnce(remainingResult);
    vi.mocked(api.commitQuestionImport)
      .mockResolvedValueOnce({ ...initialResult, committed: true, committed_count: 50 })
      .mockResolvedValueOnce({ ...remainingResult, committed: false, committed_count: 0 });

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Import Questions' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(api.validateQuestionImportRows).toHaveBeenCalledTimes(2);
      expect(screen.getByText('Saved 50 rows. Fix the highlighted rows to continue.')).toBeTruthy();
    });
    expect(screen.getByDisplayValue('ord 52 [answer 52]')).toBeTruthy();
    expect(screen.getByText('4 rows ready')).toBeTruthy();
    expect(screen.queryByDisplayValue('ord 1 [answer 1]')).toBeNull();
  });

  it('keeps uploads running after the drawer is hidden and lets the header reopen them', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

    const modules = [
      buildModuleNode({
        id: 1,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        children: [
          buildModuleNode({
            id: 2,
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            children: [
              buildModuleNode({
                id: 3,
                title: 'noun2en',
                slug: 'noun2en',
                full_slug: 'norwegian/vocabulary/noun2en',
                instruction: 'Translate each Norwegian noun into English.'
              })
            ]
          })
        ]
      })
    ];
    const rows = Array.from({ length: 60 }, (_, index) => buildImportRow({
      row_number: index + 1,
      qml_line: `ord ${index + 1} [answer ${index + 1}]`
    }));
    const importResult = buildImportResult({
      ready_to_commit: true,
      rows,
      valid_row_count: 60,
      committable_row_numbers: rows.map((row) => row.row_number),
      report_text: '60 ready to commit'
    });

    persistImportSession(window.sessionStorage, {
      instanceKey: 'local-dev',
      modules,
      open: true,
      targetModuleId: 3,
      qmlText: rows.map((row) => row.qml_line).join('\n'),
      rows,
      result: importResult
    });

    const firstChunk = deferred<typeof importResult>();
    const secondChunk = deferred<typeof importResult>();

    mockAuthenticatedAdmin(modules);
    vi.mocked(api.getStats).mockResolvedValue(buildStatsResponse());
    vi.mocked(api.validateQuestionImportRows).mockResolvedValue(importResult);
    vi.mocked(api.commitQuestionImport)
      .mockImplementationOnce(() => firstChunk.promise)
      .mockImplementationOnce(() => secondChunk.promise);

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Import Questions' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenCalledTimes(1);
      expect(screen.getByRole('button', { name: 'Saving 0/60' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Hide' }));

    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Import Questions' })).toBeNull();
      expect(screen.getByRole('button', { name: 'Uploading 0/60' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Stats' }));
    await waitFor(() => {
      expect(api.getStats).toHaveBeenCalledTimes(1);
    });

    firstChunk.resolve({ ...importResult, committed: true, committed_count: 50 });
    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenCalledTimes(2);
      expect(screen.getByRole('button', { name: 'Uploading 50/60' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Uploading 50/60' }));
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Import Questions' })).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Saving 50/60' })).toBeTruthy();
    });

    secondChunk.resolve({ ...importResult, committed: true, committed_count: 10 });
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Import Questions' })).toBeNull();
    });
  });
});
