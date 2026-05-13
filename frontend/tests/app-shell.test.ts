import { render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../src/lib/api', () => ({
  bootstrapAdmin: vi.fn(),
  commitQuestionImport: vi.fn(),
  createModule: vi.fn(),
  createQuestion: vi.fn(),
  createQuizSession: vi.fn(),
  createUser: vi.fn(),
  deleteModule: vi.fn(),
  deleteQuestion: vi.fn(),
  deleteRejectedModule: vi.fn(),
  exportContentArchive: vi.fn(),
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
  buildModerationQueue,
  buildModuleNode,
  buildMyContributions,
  buildQuestionRow,
  buildQuestionRevisionProposal,
  buildQuizItem,
  buildQuizSession,
  buildStatsResponse
} from './builders';

function buildModules() {
  return [
    buildModuleNode({
      id: 1,
      title: 'Biology',
      slug: 'biology',
      full_slug: 'biology'
    }),
    buildModuleNode({
      id: 2,
      title: 'Geography',
      slug: 'geography',
      full_slug: 'geography'
    })
  ];
}

function mockAuthenticatedUser(modules = [buildModules()[0]]) {
  vi.mocked(api.getHealth).mockResolvedValue({
    status: 'ok',
    instance_key: 'local-dev',
    bootstrap_required: false
  });
  vi.mocked(api.getCurrentActor).mockResolvedValue(buildAuthActor());
  vi.mocked(api.getModulesTree).mockResolvedValue(modules);
  vi.mocked(api.getMyContributions).mockResolvedValue(buildMyContributions());
  vi.mocked(api.getStats).mockResolvedValue(buildStatsResponse());
}

describe('App', () => {
  it('persists the selected module across remounts within the same app instance', async () => {
    const user = userEvent.setup();
    const modules = buildModules();

    mockAuthenticatedUser(modules);

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

    expect(window.localStorage.getItem('learning.local-dev.selected-module-full-slug')).toBe('geography');

    firstRender.unmount();

    mockAuthenticatedUser(modules);
    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Geography' })).toBeTruthy();
    });
  });

  it('logs out from the account menu and returns to the auth screen', async () => {
    const user = userEvent.setup();

    mockAuthenticatedUser();
    vi.mocked(api.logout).mockResolvedValue(undefined);

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Open user menu for User A' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Open user menu for User A' }));
    await user.click(screen.getByRole('menuitem', { name: 'Log out' }));

    expect(api.logout).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Sign in' })).toBeTruthy();
    });
  });

  it('opens a submitted quiz question in the editor and returns to the quiz after save', async () => {
    const user = userEvent.setup();
    const bundleQml =
      '{A patient needs {} mg. The solution has {} mg/ml. How much is needed? []\n {500} {40} [12.5 ml]\n {600} {30} [20 ml]}';

    mockAuthenticatedUser();
    vi.mocked(api.createQuizSession).mockResolvedValue(
      buildQuizSession({
        id: 44,
        items: [
          buildQuizItem({
            id: 91,
            question_id: 91,
            prompt: 'A patient needs 500 mg. The solution has 40 mg/ml. How much is needed?',
            question_type: 'single_text',
            submitted_answer: ['12.5 ml'],
            is_correct: true,
            score_earned: 1,
            score_possible: 1,
            canonical_answers: ['12.5 ml'],
            default_answers: ['12.5 ml'],
            accepted_answer_groups: [['12.5 ml']],
            matched_default_answers: [true]
          }),
          buildQuizItem({
            id: 92,
            position: 2,
            question_id: 92,
            prompt: 'What is the capital of Sweden?'
          })
        ]
      })
    );
    vi.mocked(api.getQuestion).mockResolvedValue(
      buildQuestionRow({
        question_id: 91,
        module_id: 1,
        module_full_slug: 'biology',
        prompt: 'A patient needs {} mg. The solution has {} mg/ml. How much is needed? []',
        question_type: 'bundle',
        accepted_answers: [],
        bundle_qml: bundleQml
      })
    );
    vi.mocked(api.reviseQuestion).mockResolvedValue({
      question_id: 91,
      proposal_id: 1,
      admin_verified: true,
      moderation_status: 'verified',
      delete_requested: false
    });

    window.history.replaceState({}, '', '/quiz');
    render(App);

    await screen.findByRole('heading', { name: 'Biology' });
    await user.click(screen.getByRole('button', { name: 'Start Quiz' }));
    await screen.findByText('1. A patient needs 500 mg. The solution has 40 mg/ml. How much is needed?');

    await user.click(screen.getByRole('button', { name: 'Suggest change' }));

    await waitFor(() => {
      expect(api.getQuestion).toHaveBeenCalledWith(91);
    });
    const bundleInput = await screen.findByLabelText('Bundle QML');
    expect((bundleInput as HTMLTextAreaElement).value).toBe(
      'A patient needs {} mg. The solution has {} mg/ml. How much is needed? []\n{500} {40} [12.5 ml]\n{600} {30} [20 ml]'
    );

    await user.click(screen.getByRole('button', { name: 'Save Revision' }));

    await waitFor(() => {
      expect(api.reviseQuestion).toHaveBeenCalledWith(91, expect.objectContaining({
        module_id: 1,
        question_type: 'bundle',
        bundle_qml: expect.stringContaining('{600} {30} [20 ml]'),
        reset_stats: true
      }));
    });
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Revise Question' })).toBeNull();
    });
    const quizPrompt = screen.getByText('1. A patient needs 500 mg. The solution has 40 mg/ml. How much is needed?');
    expect(quizPrompt).toBeTruthy();
    expect(quizPrompt.closest('article')?.className).toContain('flagged-review');
  });

  it('refreshes auth state after an admin updates their own role', async () => {
    const user = userEvent.setup();
    const modules = [buildModules()[0]];

    vi.mocked(api.getHealth).mockResolvedValue({
      status: 'ok',
      instance_key: 'local-dev',
      bootstrap_required: false
    });
    vi.mocked(api.getCurrentActor)
      .mockResolvedValueOnce(buildAuthActor({ id: 1, handle: 'admin', display_name: 'Admin', role: 'admin' }))
      .mockResolvedValueOnce(buildAuthActor({ id: 1, handle: 'admin', display_name: 'Admin', role: 'user' }));
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue([
      { id: 1, handle: 'admin', display_name: 'Admin', role: 'admin', created_at: '2026-04-05T10:00:00Z' }
    ]);
    vi.mocked(api.getModerationQueue).mockResolvedValue({
      pending_modules: [],
      rejected_modules: [],
      pending_questions: []
    });
    vi.mocked(api.updateUserRole).mockResolvedValue({
      id: 1,
      handle: 'admin',
      display_name: 'Admin',
      role: 'user',
      created_at: '2026-04-05T10:00:00Z'
    });
    vi.mocked(api.getMyContributions).mockResolvedValue(buildMyContributions());

    window.history.replaceState({}, '', '/admin');
    render(App);

    await screen.findByText('Catalog and moderation');

    await user.click(screen.getByRole('button', { name: /^Accounts/ }));
    const accountsDialog = await screen.findByRole('dialog', { name: 'Accounts' });
    await user.selectOptions(within(accountsDialog).getByLabelText('Manage account'), '1');
    await user.selectOptions(within(accountsDialog).getAllByLabelText('Role')[1], 'user');
    await user.click(within(accountsDialog).getByRole('button', { name: 'Save Role' }));

    expect(api.updateUserRole).toHaveBeenCalledWith(1, { role: 'user' });
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Contributions and pending content' })).toBeTruthy();
    });
  });

  it('bulk approves pending uploaded questions and refreshes shared data once after the batch', async () => {
    const user = userEvent.setup();
    const modules = [buildModules()[0]];

    vi.mocked(api.getHealth).mockResolvedValue({
      status: 'ok',
      instance_key: 'local-dev',
      bootstrap_required: false
    });
    vi.mocked(api.getCurrentActor).mockResolvedValue(
      buildAuthActor({ id: 1, handle: 'admin', display_name: 'Admin', role: 'admin' })
    );
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue([
      { id: 1, handle: 'admin', display_name: 'Admin', role: 'admin', created_at: '2026-04-05T10:00:00Z' }
    ]);
    vi.mocked(api.getModerationQueue)
      .mockResolvedValueOnce(
        buildModerationQueue({
          pending_questions: [
            {
              question_id: 71,
              module_id: 1,
              module_full_slug: 'biology',
              prompt: 'cell',
              question_type: 'single_text',
              rank: 1,
              accepted_answers: [['cell']],
              segments: [],
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 2,
              creator_display_name: 'Alice',
              admin_review_note: ''
            },
            {
              question_id: 72,
              module_id: 1,
              module_full_slug: 'biology',
              prompt: 'tissue',
              question_type: 'single_text',
              rank: 2,
              accepted_answers: [['tissue']],
              segments: [],
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 2,
              creator_display_name: 'Alice',
              admin_review_note: ''
            }
          ]
        })
      )
      .mockResolvedValueOnce(buildModerationQueue());
    vi.mocked(api.reviewQuestion).mockResolvedValue({});

    window.history.replaceState({}, '', '/admin');
    render(App);

    await screen.findByText('Catalog and moderation');

    const initialModuleLoads = vi.mocked(api.getModulesTree).mock.calls.length;
    const initialModerationLoads = vi.mocked(api.getModerationQueue).mock.calls.length;

    await user.click(screen.getByRole('button', { name: /^Uploads/i }));
    await user.click(screen.getByLabelText('Select all pending questions in biology'));
    await user.click(screen.getByRole('button', { name: 'Approve selected' }));

    await waitFor(() => {
      expect(api.reviewQuestion).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(api.getModerationQueue).toHaveBeenCalledTimes(initialModerationLoads + 1);
    });

    expect(api.reviewQuestion).toHaveBeenNthCalledWith(1, 71, { action: 'approve', note: '' });
    expect(api.reviewQuestion).toHaveBeenNthCalledWith(2, 72, { action: 'approve', note: '' });
    expect(api.getModulesTree).toHaveBeenCalledTimes(initialModuleLoads + 1);
  });

  it('approves pending revisions from stats review and refreshes shared data', async () => {
    const user = userEvent.setup();
    const modules = [buildModules()[0]];

    vi.mocked(api.getHealth).mockResolvedValue({
      status: 'ok',
      instance_key: 'local-dev',
      bootstrap_required: false
    });
    vi.mocked(api.getCurrentActor).mockResolvedValue(
      buildAuthActor({ id: 1, handle: 'admin', display_name: 'Admin', role: 'admin' })
    );
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue([
      { id: 1, handle: 'admin', display_name: 'Admin', role: 'admin', created_at: '2026-04-05T10:00:00Z' }
    ]);
    vi.mocked(api.getModerationQueue).mockResolvedValue(buildModerationQueue());
    const statsMock = vi.mocked(api.getStats);
    statsMock.mockReset();
    statsMock
      .mockResolvedValueOnce(
        buildStatsResponse({
          summary: { reviewed_questions: 2 },
          revision_proposals: [
            buildQuestionRevisionProposal({
              proposal_id: 81,
              question_id: 71,
              module_id: 1,
              module_full_slug: 'biology',
              current_prompt: 'cell',
              proposed_prompt: 'cells'
            }),
            buildQuestionRevisionProposal({
              proposal_id: 82,
              question_id: 72,
              module_id: 1,
              module_full_slug: 'biology',
              current_prompt: 'tissue',
              proposed_prompt: 'tissues'
            })
          ]
        })
      )
      .mockResolvedValue(buildStatsResponse());
    vi.mocked(api.reviewQuestionRevision).mockResolvedValue({});

    window.history.replaceState({}, '', '/stats');
    render(App);

    await screen.findByRole('heading', { name: 'Biology' });

    const initialModuleLoads = vi.mocked(api.getModulesTree).mock.calls.length;
    const initialStatsLoads = statsMock.mock.calls.length;

    await user.click(screen.getByLabelText('Review'));
    await user.click(screen.getByRole('button', { name: /^Review\s+2/ }));
    await user.click(screen.getAllByRole('button', { name: 'Approve' })[0]);

    await waitFor(() => {
      expect(api.reviewQuestionRevision).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(api.getStats).toHaveBeenCalledTimes(initialStatsLoads + 1);
    });

    expect(api.reviewQuestionRevision).toHaveBeenCalledWith(81, {
      action: 'approve',
      note: '',
      reset_stats: true
    });
    expect(api.getModulesTree).toHaveBeenCalledTimes(initialModuleLoads + 1);
  });

  it('opens the stats revision drawer and approves an edited revision', async () => {
    const user = userEvent.setup();
    const modules = [buildModules()[0]];

    vi.mocked(api.getHealth).mockResolvedValue({
      status: 'ok',
      instance_key: 'local-dev',
      bootstrap_required: false
    });
    vi.mocked(api.getCurrentActor).mockResolvedValue(
      buildAuthActor({ id: 1, handle: 'admin', display_name: 'Admin', role: 'admin' })
    );
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue([
      { id: 1, handle: 'admin', display_name: 'Admin', role: 'admin', created_at: '2026-04-05T10:00:00Z' }
    ]);
    vi.mocked(api.getModerationQueue).mockResolvedValue(buildModerationQueue());
    vi.mocked(api.getStats).mockResolvedValue(
      buildStatsResponse({
        summary: { reviewed_questions: 1 },
        revision_proposals: [
          buildQuestionRevisionProposal({
            proposal_id: 81,
            question_id: 71,
            module_id: 1,
            module_full_slug: 'biology',
            current_prompt: 'cell',
            current_accepted_answers: [['cell']],
            proposed_prompt: 'cells',
            proposed_accepted_answers: [['cells']]
          })
        ]
      })
    );
    vi.mocked(api.reviewQuestionRevision).mockResolvedValue({});

    window.history.replaceState({}, '', '/stats');
    render(App);

    await screen.findByRole('heading', { name: 'Biology' });

    await user.click(screen.getByLabelText('Review'));
    await user.click(screen.getByRole('button', { name: /^Review\s+1/ }));
    await user.click(screen.getByRole('button', { name: 'Edit then approve' }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Approve Revision' })).toBeTruthy();
    });

    const promptInput = screen.getByLabelText('Prompt');
    await user.clear(promptInput);
    await user.type(promptInput, 'cells refined');

    const answersInput = screen.getByLabelText('Accepted answers');
    await user.clear(answersInput);
    await user.type(answersInput, 'cellular');

    await user.click(screen.getByRole('button', { name: 'Approve Revision' }));

    await waitFor(() => {
      expect(api.reviewQuestionRevision).toHaveBeenCalledWith(81, {
        action: 'approve',
        note: '',
        edited_revision: {
          module_id: 1,
          prompt: 'cells refined',
          question_type: 'single_text',
          rank: 1,
          accepted_answers: [['cellular']],
          segments: [],
          reset_stats: true
        }
      });
    });
  });

  it('calls the content export helper from the admin page', async () => {
    const user = userEvent.setup();
    const modules = [buildModules()[0]];

    vi.mocked(api.getHealth).mockResolvedValue({
      status: 'ok',
      instance_key: 'local-dev',
      bootstrap_required: false
    });
    vi.mocked(api.getCurrentActor).mockResolvedValue(
      buildAuthActor({ id: 1, handle: 'admin', display_name: 'Admin', role: 'admin' })
    );
    vi.mocked(api.getModulesTree).mockResolvedValue(modules);
    vi.mocked(api.getUsers).mockResolvedValue([
      { id: 1, handle: 'admin', display_name: 'Admin', role: 'admin', created_at: '2026-04-05T10:00:00Z' }
    ]);
    vi.mocked(api.getModerationQueue).mockResolvedValue(buildModerationQueue());
    vi.mocked(api.exportContentArchive).mockResolvedValue(undefined);

    window.history.replaceState({}, '', '/admin');
    render(App);

    await screen.findByText('Catalog and moderation');

    await user.click(screen.getByRole('button', { name: /^Export/ }));
    const exportDialog = await screen.findByRole('dialog', { name: 'Export' });
    await user.click(within(exportDialog).getByRole('button', { name: 'Export content' }));

    await waitFor(() => {
      expect(api.exportContentArchive).toHaveBeenCalledTimes(1);
    });
  });
});
