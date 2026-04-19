import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import AuthPage from '../src/components/AuthPage.svelte';


describe('AuthPage', () => {
  it('submits sign-in credentials through the login handler', async () => {
    const user = userEvent.setup();
    const loginSpy = vi.fn().mockResolvedValue(undefined);

    render(AuthPage, {
      props: {
        bootstrapRequired: false,
        onLogin: loginSpy,
      },
    });

    expect(screen.queryByText('Authentication')).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Sign In' })).toBeNull();
    expect(screen.getByPlaceholderText('Username')).toBeTruthy();
    expect(screen.getByPlaceholderText('Password')).toBeTruthy();
    expect(screen.queryByText('Sign in to continue.')).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Preview demo' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Demo' }).className).toContain('review-button');

    await user.type(screen.getByLabelText('Username'), ' user-a ');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(loginSpy).toHaveBeenCalledWith({ handle: 'user-a', password: 'password123' });
  });

  it('submits sign-in when Enter is pressed in the password field', async () => {
    const user = userEvent.setup();
    const loginSpy = vi.fn().mockResolvedValue(undefined);

    render(AuthPage, {
      props: {
        bootstrapRequired: false,
        onLogin: loginSpy,
      },
    });

    await user.type(screen.getByLabelText('Username'), ' user-a ');
    await user.type(screen.getByLabelText('Password'), 'password123{Enter}');

    expect(loginSpy).toHaveBeenCalledWith({ handle: 'user-a', password: 'password123' });
  });

  it('requires matching passwords before bootstrapping the first admin', async () => {
    const user = userEvent.setup();
    const bootstrapSpy = vi.fn().mockResolvedValue(undefined);

    render(AuthPage, {
      props: {
        bootstrapRequired: true,
        onBootstrapAdmin: bootstrapSpy,
      },
    });

    expect(screen.getByRole('heading', { name: 'Create admin account' })).toBeTruthy();
    expect(screen.getByText('Create the first admin account to unlock the app.')).toBeTruthy();

    await user.type(screen.getByLabelText('Username'), 'admin');
    await user.type(screen.getByLabelText('Display name'), 'Admin');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText('Confirm password'), 'password999');

    expect((screen.getByRole('button', { name: 'Create Admin' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText('Passwords must match before creating the first admin.')).toBeTruthy();
    expect(bootstrapSpy).not.toHaveBeenCalled();
  });

  it('starts demo mode through the demo handler', async () => {
    const user = userEvent.setup();
    const demoSpy = vi.fn().mockResolvedValue(undefined);

    render(AuthPage, {
      props: {
        bootstrapRequired: false,
        onDemo: demoSpy,
      },
    });

    await user.click(screen.getByRole('button', { name: 'Demo' }));

    expect(demoSpy).toHaveBeenCalledTimes(1);
  });
});
