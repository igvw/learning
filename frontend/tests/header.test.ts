import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import Header from '../src/components/Header.svelte';
import { buildAuthActor } from './builders';

describe('Header', () => {
  it('shows the current account menu and logs out from the avatar button', async () => {
    const user = userEvent.setup();
    const logoutSpy = vi.fn();

    render(Header, {
      props: {
        currentRoute: 'quiz',
        currentActor: buildAuthActor({ id: 1, handle: 'user-a', display_name: 'User A' }),
        onNavigate: vi.fn(),
        onToggleMenu: vi.fn(),
        onLogout: logoutSpy
      }
    });

    const avatarButton = screen.getByRole('button', { name: 'Open user menu for User A' });
    expect(avatarButton.textContent).toBe('U');

    await user.click(avatarButton);
    expect(screen.getByRole('menu', { name: 'Account menu' })).toBeTruthy();
    expect(screen.getByText('user account')).toBeTruthy();
    await user.click(screen.getByRole('menuitem', { name: /log out/i }));
    expect(logoutSpy).toHaveBeenCalledOnce();
  });
});
