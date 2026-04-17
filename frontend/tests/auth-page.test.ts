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

    await user.type(screen.getByLabelText('Handle'), ' user-a ');
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

    await user.type(screen.getByLabelText('Handle'), ' user-a ');
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

    await user.type(screen.getByLabelText('Handle'), 'admin');
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

    await user.click(screen.getByRole('button', { name: 'Try Demo' }));

    expect(demoSpy).toHaveBeenCalledTimes(1);
  });
});
