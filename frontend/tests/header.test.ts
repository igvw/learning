import './test-support';

import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import Header from '../src/components/Header.svelte';
import { buildUser } from './builders';

describe('Header', () => {
  it('shows an avatar-style active user badge and switches users from a small menu', async () => {
    const user = userEvent.setup();
    const selectSpy = vi.fn();
    const users = [
      buildUser({ id: 1, handle: 'user-a', display_name: 'User A' }),
      buildUser({ id: 2, handle: 'user-b', display_name: 'User B', created_at: '2026-04-05T10:05:00Z' })
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
