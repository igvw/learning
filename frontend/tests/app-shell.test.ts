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
  updateModule: vi.fn(),
  validateQuestionImportRows: vi.fn(),
  validateQuestionImportText: vi.fn()
}));

import App from '../src/App.svelte';
import * as api from '../src/lib/api';
import { buildModuleNode, buildQuestionRow, buildRecentSession, buildStatsResponse, buildUser } from './builders';

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

function buildUsers() {
  return [
    buildUser({ id: 1, handle: 'user-a', display_name: 'User A' }),
    buildUser({ id: 2, handle: 'user-b', display_name: 'User B', created_at: '2026-04-05T10:05:00Z' })
  ];
}

describe('App', () => {
  it('uses the review toggle to switch the single table without reloading stats', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', '/stats');

    const stats = buildStatsResponse({
      summary: {
        total_questions: 2,
        reviewed_questions: 1,
        total_attempts: 1,
        total_correct: 1,
        total_possible: 1,
        accuracy: 1
      },
      recent_sessions: [
        buildRecentSession({
          session_id: 11,
          created_at: '2026-04-05T10:00:00Z'
        })
      ],
      questions: [
        buildQuestionRow({
          question_id: 1,
          module_id: 1,
          module_full_slug: 'biology',
          prompt: 'What structure anchors most plants in the ground?',
          prompt_preview: 'What structure anchors most plants in the ground?',
          review_flag: true,
          schedule: {
            bucket: 'hot1_sit_out',
            logical_bucket: 'review',
            recovery_streak: 1,
            interval_step: 0,
            last_incorrect_at: '2026-04-01T06:00:00Z'
          }
        }),
        buildQuestionRow({
          question_id: 2,
          module_id: 1,
          module_full_slug: 'biology',
          prompt: 'What is chlorophyll used for?',
          prompt_preview: 'What is chlorophyll used for?',
          question_type: 'single_text',
          rank: 2,
          accepted_answers: [['photosynthesis']]
        })
      ]
    });

    vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', instance_key: 'local-dev' });
    vi.mocked(api.getModulesTree).mockResolvedValue([buildModules()[0]]);
    vi.mocked(api.getUsers).mockResolvedValue([buildUsers()[0]]);
    vi.mocked(api.getStats).mockResolvedValue(stats);

    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Questions' })).toBeTruthy();
    });

    expect(api.getStats).toHaveBeenCalledTimes(1);
    expect(api.getStats).toHaveBeenCalledWith(1, 1);
    expect(screen.getByText('What is chlorophyll used for?')).toBeTruthy();
    expect(screen.queryByText('What structure anchors most plants in the ground?')).toBeNull();

    await user.click(screen.getByRole('checkbox', { name: 'Review only' }));

    expect(screen.getByText('What structure anchors most plants in the ground?')).toBeTruthy();
    expect(screen.queryByText('What is chlorophyll used for?')).toBeNull();
    expect(api.getStats).toHaveBeenCalledTimes(1);
  });

  it('switches users from the header menu in the full app and updates persisted state', async () => {
    const user = userEvent.setup();

    vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', instance_key: 'local-dev' });
    vi.mocked(api.getModulesTree).mockResolvedValue([buildModules()[0]]);
    vi.mocked(api.getUsers).mockResolvedValue(buildUsers());

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

    vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', instance_key: 'local-dev' });
    vi.mocked(api.getModulesTree).mockResolvedValue(buildModules());
    vi.mocked(api.getUsers).mockResolvedValue(buildUsers());

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
    window.localStorage.setItem('learning.local-dev.active-user-handle', 'user-a');
    window.localStorage.setItem('learning.local-dev.selected-module-full-slug', 'biology');
    window.localStorage.setItem('learning.published.active-user-handle', 'user-b');
    window.localStorage.setItem('learning.published.selected-module-full-slug', 'geography');
    window.localStorage.setItem('learning.active-user-id', '999');
    window.localStorage.setItem('learning.selected-module-id', '999');

    vi.mocked(api.getHealth)
      .mockResolvedValueOnce({ status: 'ok', instance_key: 'local-dev' })
      .mockResolvedValueOnce({ status: 'ok', instance_key: 'published' });
    vi.mocked(api.getModulesTree).mockResolvedValue(buildModules());
    vi.mocked(api.getUsers).mockResolvedValue(buildUsers());

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
});
