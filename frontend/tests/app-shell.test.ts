import { render, screen, waitFor, within } from '@testing-library/svelte';
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
  exportContentArchive: vi.fn(),
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
import {
  buildAuthActor,
  buildModerationQueue,
  buildModuleNode,
  buildMyContributions,
  buildQuestionRevisionProposal,
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
    expect(window.localStorage.getItem('learning.selected-module-id')).toBeNull();

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
      pending_questions: [],
      pending_revisions: []
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

  it('bulk approves pending revisions and refreshes shared data once after the batch', async () => {
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
    const moderationQueueMock = vi.mocked(api.getModerationQueue);
    moderationQueueMock.mockReset();
    moderationQueueMock
      .mockResolvedValueOnce(
        buildModerationQueue({
          pending_revisions: [
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
      .mockResolvedValueOnce(buildModerationQueue());
    vi.mocked(api.reviewQuestionRevision).mockResolvedValue({});

    window.history.replaceState({}, '', '/admin');
    render(App);

    await screen.findByText('Catalog and moderation');

    const initialModuleLoads = vi.mocked(api.getModulesTree).mock.calls.length;
    const initialModerationLoads = moderationQueueMock.mock.calls.length;

    await user.click(screen.getByRole('button', { name: /^Revisions/i }));
    await user.click(screen.getByRole('button', { name: 'Open pending revisions for biology' }));
    const revisionsDialog = screen.getByRole('dialog', { name: 'Pending revisions' });
    const promptToggle = within(revisionsDialog).getByText('Prompt changes').closest('button');
    expect(promptToggle).toBeTruthy();
    await user.click(promptToggle as HTMLElement);
    await waitFor(() => {
      expect(screen.getByLabelText('Select all revisions in Prompt changes')).toBeTruthy();
    });
    await user.click(screen.getByLabelText('Select all revisions in Prompt changes'));
    await user.click(screen.getAllByRole('button', { name: 'Approve selected' })[0]);

    await waitFor(() => {
      expect(api.reviewQuestionRevision).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(api.getModerationQueue).toHaveBeenCalledTimes(initialModerationLoads + 1);
    });

    expect(api.reviewQuestionRevision).toHaveBeenNthCalledWith(1, 81, {
      action: 'approve',
      note: '',
      reset_stats: true
    });
    expect(api.reviewQuestionRevision).toHaveBeenNthCalledWith(2, 82, {
      action: 'approve',
      note: '',
      reset_stats: true
    });
    expect(api.getModulesTree).toHaveBeenCalledTimes(initialModuleLoads + 1);
  });

  it('opens the moderation revision drawer and approves an edited revision', async () => {
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
    const moderationQueueMock = vi.mocked(api.getModerationQueue);
    moderationQueueMock.mockReset();
    moderationQueueMock.mockResolvedValue(
      buildModerationQueue({
        pending_revisions: [
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

    window.history.replaceState({}, '', '/admin');
    render(App);

    await screen.findByText('Catalog and moderation');

    await user.click(screen.getByRole('button', { name: /^Revisions/i }));
    await user.click(screen.getByRole('button', { name: 'Open pending revisions for biology' }));
    const revisionsDialog = screen.getByRole('dialog', { name: 'Pending revisions' });
    const promptToggle = within(revisionsDialog).getByText('Prompt changes').closest('button');
    expect(promptToggle).toBeTruthy();
    await user.click(promptToggle as HTMLElement);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Open revision editor for cell' })).toBeTruthy();
    });
    await user.click(screen.getByRole('button', { name: 'Open revision editor for cell' }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Approve Revision' })).toBeTruthy();
    });

    const promptInput = screen.getByLabelText('Prompt');
    await user.clear(promptInput);
    await user.type(promptInput, 'cells refined');

    const answersInput = screen.getByLabelText('Accepted answers, one per line');
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
