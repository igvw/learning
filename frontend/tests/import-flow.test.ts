import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/lib/api', () => ({
  bootstrapAdmin: vi.fn(),
  commitQuestionImport: vi.fn(),
  createModule: vi.fn(),
  createQuestion: vi.fn(),
  createQuizSession: vi.fn(),
  createUser: vi.fn(),
  deleteModule: vi.fn(),
  deleteQuestion: vi.fn(),
  getCurrentActor: vi.fn(),
  getHealth: vi.fn(),
  getModerationQueue: vi.fn(),
  getModulesTree: vi.fn(),
  getMyContributions: vi.fn(),
  getQuestion: vi.fn(),
  getStats: vi.fn(),
  getUsers: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  reviewModule: vi.fn(),
  reviewQuestion: vi.fn(),
  reviewQuestionRevision: vi.fn(),
  reviseQuestion: vi.fn(),
  submitQuizAnswer: vi.fn(),
  updateModule: vi.fn(),
  updateUserPassword: vi.fn(),
  updateUserRole: vi.fn(),
  validateQuestionImportRows: vi.fn(),
  validateQuestionImportText: vi.fn(),
  withdrawQuestionRevision: vi.fn()
}));

import App from '../src/App.svelte';
import * as api from '../src/lib/api';
import {
  buildAuthActor,
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

function buildImportModules() {
  return [
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
}

function mockAuthenticatedAdmin(modules: ReturnType<typeof buildImportModules>) {
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

function getImportDrawer(): HTMLElement {
  return screen.getByRole('complementary', { name: 'Question import' });
}

function findDrawerTextbox(value: string): HTMLInputElement | HTMLTextAreaElement | undefined {
  return within(getImportDrawer())
    .getAllByRole('textbox')
    .find((element) => (element as HTMLInputElement | HTMLTextAreaElement).value === value) as
    | HTMLInputElement
    | HTMLTextAreaElement
    | undefined;
}

async function openImportDrawer(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await screen.findByText('Catalog and moderation');
  await user.click(screen.getByRole('button', { name: /^Import Validate and commit QML into a verified leaf\.$/i }));
  const importDialog = await screen.findByRole('dialog', { name: 'Import' });
  await user.selectOptions(within(importDialog).getByLabelText('Import target'), '3');
  await user.click(within(importDialog).getByRole('button', { name: 'Import QML' }));
  await waitFor(() => {
    expect(within(getImportDrawer()).getByRole('heading', { name: 'Import Questions' })).toBeTruthy();
  });
}

async function setQmlText(value: string): Promise<void> {
  await fireEvent.input(within(getImportDrawer()).getByLabelText('QML text'), { target: { value } });
}

async function startImport(user: ReturnType<typeof userEvent.setup>, qmlText: string): Promise<void> {
  await setQmlText(qmlText);
  await user.click(within(getImportDrawer()).getByRole('button', { name: 'Start Import' }));
}

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  window.sessionStorage.clear();
  window.history.replaceState({}, '', '/quiz');
});

describe('import flow', () => {
  it('does not restore import drawer progress after a refresh', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

    const modules = buildImportModules();
    const restoredResult = buildImportResult({
      ready_to_commit: true,
      rows: [buildImportRow({ start_line: 35, end_line: 35, entry_kind: 'plain', qml_text: 'mot [against | toward]' })],
      valid_row_count: 1,
      committable_start_lines: [35],
      review_rows: [
        buildImportReviewRow({
          start_line: 35,
          end_line: 35,
          qml_text: 'mot [against | toward]',
          matched_questions: [
            {
              question_id: 8,
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              entry_kind: 'plain',
              qml_text: 'mot [against]',
              answer_blocks: ['against']
            }
          ]
        })
      ],
      report_text: '1 row ready'
    });

    mockAuthenticatedAdmin(modules);
    vi.mocked(api.validateQuestionImportText).mockResolvedValue(restoredResult);

    const firstRender = render(App);
    await openImportDrawer(user);
    await startImport(user, 'mot [against | toward]');

    await waitFor(() => {
      expect(screen.getByText('1 review rows')).toBeTruthy();
    });

    firstRender.unmount();

    mockAuthenticatedAdmin(modules);
    render(App);

    await screen.findByText('Catalog and moderation');
    expect(screen.queryByRole('heading', { name: 'Import Questions' })).toBeNull();

    await user.click(screen.getByRole('button', { name: /^Import\b/i }));
    const importDialog = await screen.findByRole('dialog', { name: 'Import' });
    await user.selectOptions(within(importDialog).getByLabelText('Import target'), '3');
    await user.click(within(importDialog).getByRole('button', { name: 'Import QML' }));

    await waitFor(() => {
      expect(within(getImportDrawer()).getByRole('heading', { name: 'Import Questions' })).toBeTruthy();
    });
    expect((within(getImportDrawer()).getByLabelText('QML text') as HTMLTextAreaElement).value).toBe('');
  });

  it('clears an idle import drawer when it is closed', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

    const modules = buildImportModules();
    mockAuthenticatedAdmin(modules);

    render(App);
    await openImportDrawer(user);
    await setQmlText('mot [against | toward]');

    await user.click(within(getImportDrawer()).getByRole('button', { name: 'Close' }));
    await waitFor(() => {
      expect(screen.queryByRole('complementary', { name: 'Question import' })).toBeNull();
    });

    await openImportDrawer(user);
    expect((within(getImportDrawer()).getByLabelText('QML text') as HTMLTextAreaElement).value).toBe('');
  });

  it('commits imports in 50-row chunks, keeps progress in the drawer, and does not show a header status pill', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

    const modules = buildImportModules();
    const rows = Array.from({ length: 120 }, (_, index) =>
      buildImportRow({
        start_line: index + 1,
        end_line: index + 1,
        entry_kind: 'plain',
        qml_text: `ord ${index + 1} [answer ${index + 1}]`
      })
    );
    const importResult = buildImportResult({
      ready_to_commit: true,
      rows,
      valid_row_count: 120,
      committable_start_lines: rows.map((row) => row.start_line),
      report_text: '120 ready to commit'
    });

    const firstChunk = deferred<typeof importResult>();
    const secondChunk = deferred<typeof importResult>();
    const thirdChunk = deferred<typeof importResult>();

    mockAuthenticatedAdmin(modules);
    vi.mocked(api.validateQuestionImportText).mockResolvedValue(importResult);
    vi.mocked(api.validateQuestionImportRows).mockResolvedValue(importResult);
    vi.mocked(api.commitQuestionImport)
      .mockImplementationOnce(() => firstChunk.promise)
      .mockImplementationOnce(() => secondChunk.promise)
      .mockImplementationOnce(() => thirdChunk.promise);

    render(App);
    await openImportDrawer(user);
    await startImport(user, rows.map((row) => row.qml_text).join('\n'));

    await waitFor(() => {
      expect(within(getImportDrawer()).getByRole('button', { name: 'Save' })).toBeTruthy();
    });

    await user.click(within(getImportDrawer()).getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenCalledTimes(1);
    });
    expect(within(getImportDrawer()).getByRole('button', { name: 'Saving 0/120' })).toBeTruthy();
    expect((within(getImportDrawer()).getByRole('button', { name: 'Close' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByRole('button', { name: /Uploading 0\/120/i })).toBeNull();

    firstChunk.resolve({ ...importResult, committed: true, committed_count: 50 });
    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenCalledTimes(2);
      expect(within(getImportDrawer()).getByRole('button', { name: 'Saving 50/120' })).toBeTruthy();
    });

    secondChunk.resolve({ ...importResult, committed: true, committed_count: 50 });
    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenCalledTimes(3);
      expect(within(getImportDrawer()).getByRole('button', { name: 'Saving 100/120' })).toBeTruthy();
    });

    thirdChunk.resolve({ ...importResult, committed: true, committed_count: 20 });
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Import Questions' })).toBeNull();
    });
  });

  it('filters exact no-op duplicate revisions before chunked save', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

    const modules = buildImportModules();
    const sessionResult = buildImportResult({
      ready_to_commit: true,
      rows: [buildImportRow({ start_line: 1, end_line: 1, entry_kind: 'plain', qml_text: 'mot [toward]' })],
      valid_row_count: 1,
      committable_start_lines: [1],
      review_rows: [
        buildImportReviewRow({
          start_line: 1,
          end_line: 1,
          qml_text: 'mot [toward]',
          matched_questions: [
            {
              question_id: 8,
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              entry_kind: 'plain',
              qml_text: 'mot [against]',
              answer_blocks: ['against']
            }
          ]
        })
      ],
      report_text: '1 row ready'
    });
    const exactDuplicateResult = buildImportResult({
      rows: [buildImportRow({ start_line: 1, end_line: 1, entry_kind: 'plain', qml_text: 'mot [against]' })],
      exact_duplicate_count: 1,
      report_text: '1 exact duplicates omitted'
    });

    mockAuthenticatedAdmin(modules);
    vi.mocked(api.validateQuestionImportText).mockResolvedValue(sessionResult);
    vi.mocked(api.validateQuestionImportRows).mockResolvedValue(exactDuplicateResult);

    render(App);
    await openImportDrawer(user);
    await startImport(user, 'mot [toward]');

    const [reviewInput] = within(getImportDrawer()).getAllByRole('textbox') as HTMLInputElement[];
    await waitFor(() => {
      expect(reviewInput).toBeTruthy();
    });

    await fireEvent.input(reviewInput, {
      target: { value: 'mot [against]' }
    });
    await user.click(within(getImportDrawer()).getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(within(getImportDrawer()).getByText('Nothing new to save.')).toBeTruthy();
    });
    expect(api.commitQuestionImport).not.toHaveBeenCalled();
  });

  it('keeps remaining rows open after a later chunk fails and revalidates them', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/admin');

    const modules = buildImportModules();
    const rows = Array.from({ length: 55 }, (_, index) =>
      buildImportRow({
        start_line: index + 1,
        end_line: index + 1,
        entry_kind: 'plain',
        qml_text: `ord ${index + 1} [answer ${index + 1}]`
      })
    );
    const initialResult = buildImportResult({
      ready_to_commit: true,
      rows,
      valid_row_count: 55,
      committable_start_lines: rows.map((row) => row.start_line),
      report_text: '55 ready to commit'
    });
    const remainingRows = rows.slice(50);
    const remainingResult = buildImportResult({
      rows: remainingRows,
      valid_row_count: 4,
      committable_start_lines: [51, 53, 54, 55],
      review_rows: [
        buildImportReviewRow({
          start_line: 52,
          end_line: 52,
          qml_text: 'broken row',
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
    const firstChunk = deferred<QuestionImportResult>();

    mockAuthenticatedAdmin(modules);
    vi.mocked(api.validateQuestionImportText).mockResolvedValue(initialResult);
    vi.mocked(api.validateQuestionImportRows)
      .mockResolvedValueOnce(initialResult)
      .mockResolvedValueOnce(remainingResult);
    vi.mocked(api.commitQuestionImport)
      .mockImplementationOnce(() => firstChunk.promise)
      .mockResolvedValueOnce({ ...remainingResult, committed: false, committed_count: 0 });

    render(App);
    await openImportDrawer(user);
    await startImport(user, rows.map((row) => row.qml_text).join('\n'));

    await waitFor(() => {
      expect(within(getImportDrawer()).getByRole('button', { name: 'Save' })).toBeTruthy();
    });

    await user.click(within(getImportDrawer()).getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenCalledTimes(1);
    });

    firstChunk.resolve({ ...initialResult, committed: true, committed_count: 50 });

    await waitFor(() => {
      expect(api.commitQuestionImport).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(api.validateQuestionImportRows).toHaveBeenCalledTimes(2);
      expect(within(getImportDrawer()).getByText('Saved 50 rows. Fix the highlighted rows to continue.')).toBeTruthy();
    });
    expect(findDrawerTextbox('ord 52 [answer 52]')).toBeTruthy();
    expect(within(getImportDrawer()).getByText('4 rows ready')).toBeTruthy();
    expect(findDrawerTextbox('ord 1 [answer 1]')).toBeUndefined();
  });
});
