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
  getCurrentActor: vi.fn(),
  getHealth: vi.fn(),
  getModerationQueue: vi.fn(),
  getModulesTree: vi.fn(),
  getMyContributions: vi.fn(),
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
  buildModuleNode,
  buildMyContributions
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

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Catalog and moderation' })).toBeTruthy();
    });

    await user.selectOptions(screen.getByLabelText('Manage account'), '1');
    await user.selectOptions(screen.getAllByLabelText('Role')[1], 'user');
    await user.click(screen.getByRole('button', { name: 'Save Role' }));

    expect(api.updateUserRole).toHaveBeenCalledWith(1, { role: 'user' });
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Contributions and pending content' })).toBeTruthy();
    });
  });
});
