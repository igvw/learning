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
import { ensureModulePath } from '../src/lib/module-paths';
import type { ModuleNode, User } from '../src/lib/types';

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
