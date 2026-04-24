import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import AdminPage from '../src/components/AdminPage.svelte';
import type { ModuleNode } from '../src/lib/types';
import {
  buildAuthActor,
  buildModuleNode,
  buildMyContributions,
  buildQuestionRevisionProposal
} from './builders';

describe('AdminPage', () => {
  it('creates users from admin, updates the selected leaf module, creates a module, and offers leaf-module import', async () => {
    const user = userEvent.setup();
    const createUserSpy = vi.fn().mockResolvedValue({
      id: 10,
      handle: 'alice',
      display_name: 'Alice',
      role: 'user',
      created_at: '2026-04-05T10:00:00Z'
    });
    const createSpy = vi.fn().mockResolvedValue(
      buildModuleNode({
        id: 8,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        instruction: 'Translate the Norwegian term into English.'
      })
    );
    const updateSpy = vi.fn().mockResolvedValue(
      buildModuleNode({
        id: 2,
        title: 'Safety Checks',
        slug: 'safety_checks',
        full_slug: 'nursing/safety_checks',
        instruction: 'List each safety check before continuing.'
      })
    );
    const updateRoleSpy = vi.fn().mockResolvedValue({
      id: 9,
      handle: 'ignazio',
      display_name: 'Ignazio',
      role: 'admin',
      created_at: '2026-04-05T10:00:00Z'
    });
    const updatePasswordSpy = vi.fn().mockResolvedValue(undefined);
    const openImportSpy = vi.fn();
    const exportContentSpy = vi.fn().mockResolvedValue(undefined);
    const modules: ModuleNode[] = [
      buildModuleNode({
        id: 1,
        title: 'Nursing',
        slug: 'nursing',
        full_slug: 'nursing',
        children: [
          buildModuleNode({
            id: 2,
            title: 'Checks',
            slug: 'checks',
            full_slug: 'nursing/checks',
            instruction: 'List the safety checks in order.'
          }),
          buildModuleNode({
            id: 3,
            title: 'Definitions',
            slug: 'definitions',
            full_slug: 'nursing/definitions',
            instruction: 'Define the nursing term in plain language.'
          })
        ]
      })
    ];

    render(AdminPage, {
      props: {
        currentActor: buildAuthActor({ handle: 'admin', display_name: 'Admin', role: 'admin' }),
        modules,
        users: [{ id: 9, handle: 'ignazio', display_name: 'Ignazio', role: 'user', created_at: '2026-04-05T10:00:00Z' }],
        selectedModuleId: 2,
        moderationQueue: { pending_modules: [], rejected_modules: [], pending_questions: [], pending_revisions: [] },
        onCreateUser: createUserSpy,
        onUpdateUserRole: updateRoleSpy,
        onUpdateUserPassword: updatePasswordSpy,
        onCreateModule: createSpy,
        onUpdateModule: updateSpy,
        onOpenImport: openImportSpy,
        onExportContent: exportContentSpy
      }
    });

    expect(screen.getByRole('heading', { name: 'Catalog and moderation' })).toBeTruthy();
    expect(screen.getByRole('button', { name: /^Accounts/ })).toBeTruthy();
    expect(screen.getByRole('button', { name: /modules in the tree/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /^Import/ })).toBeTruthy();
    expect(screen.getByRole('button', { name: /^Export/ })).toBeTruthy();

    await user.click(screen.getByRole('button', { name: /^Accounts/ }));
    const accountsDialog = await screen.findByRole('dialog', { name: 'Accounts' });
    expect(within(accountsDialog).getByRole('button', { name: 'Create Account' }).className).toContain('primary-button');
    expect(within(accountsDialog).getByRole('button', { name: 'Save Role' }).className).toContain('primary-button');

    const confirmPasswordInputs = within(accountsDialog).getAllByLabelText('Confirm password');
    await user.type(within(accountsDialog).getByLabelText('Username'), 'alice');
    await user.type(within(accountsDialog).getByLabelText('Display name'), 'Alice');
    await user.type(within(accountsDialog).getByLabelText('Password'), 'password123');
    await user.type(confirmPasswordInputs[0], 'password999');
    expect((within(accountsDialog).getByRole('button', { name: 'Create Account' }) as HTMLButtonElement).disabled).toBe(true);
    expect(within(accountsDialog).getByText('Passwords must match before creating an account.')).toBeTruthy();
    await user.clear(confirmPasswordInputs[0]);
    await user.type(confirmPasswordInputs[0], 'password123');
    await user.click(within(accountsDialog).getByRole('button', { name: 'Create Account' }));
    expect(createUserSpy).toHaveBeenCalledWith({
      handle: 'alice',
      display_name: 'Alice',
      role: 'user',
      password: 'password123'
    });
    expect(await screen.findByText('Account ready: Alice.')).toBeTruthy();

    await user.selectOptions(within(accountsDialog).getByLabelText('Manage account'), '9');
    await user.selectOptions(within(accountsDialog).getAllByLabelText('Role')[1], 'admin');
    await user.click(within(accountsDialog).getByRole('button', { name: 'Save Role' }));
    expect(updateRoleSpy).toHaveBeenCalledWith(9, 'admin');
    expect(await screen.findByText('Role updated for Ignazio.')).toBeTruthy();

    await user.type(within(accountsDialog).getByLabelText('New password'), 'new-password123');
    await user.type(confirmPasswordInputs[1], 'new-password999');
    expect((within(accountsDialog).getByRole('button', { name: 'Update Password' }) as HTMLButtonElement).disabled).toBe(true);
    expect(within(accountsDialog).getByText('Passwords must match before updating a password.')).toBeTruthy();
    await user.clear(confirmPasswordInputs[1]);
    await user.type(confirmPasswordInputs[1], 'new-password123');
    await user.click(within(accountsDialog).getByRole('button', { name: 'Update Password' }));
    expect(updatePasswordSpy).toHaveBeenCalledWith(9, 'new-password123');
    expect(await screen.findByText('Password updated.')).toBeTruthy();

    await user.click(within(accountsDialog).getByRole('button', { name: 'Close' }));

    await user.click(screen.getByRole('button', { name: /modules in the tree/i }));
    const modulesDialog = await screen.findByRole('dialog', { name: 'Modules' });
    expect(within(modulesDialog).getByRole('button', { name: 'Save Module' }).className).toContain('primary-button');
    expect(within(modulesDialog).getByRole('button', { name: 'Create Module' }).className).toContain('primary-button');
    expect(within(modulesDialog).getByText('Selected leaf module')).toBeTruthy();
    expect(within(modulesDialog).getByText('Create module')).toBeTruthy();

    const titleInput = within(modulesDialog).getByDisplayValue('Checks');
    await user.clear(titleInput);
    await user.type(titleInput, 'Safety Checks');
    const editInstruction = within(modulesDialog).getByDisplayValue('List the safety checks in order.');
    await user.clear(editInstruction);
    await user.type(editInstruction, 'List each safety check before continuing.');
    await user.click(within(modulesDialog).getByRole('button', { name: 'Save Module' }));

    expect(updateSpy).toHaveBeenCalledWith(2, {
      title: 'Safety Checks',
      instruction: 'List each safety check before continuing.'
    });
    expect(await screen.findByText('Module ready: nursing/safety_checks.')).toBeTruthy();

    await user.type(within(modulesDialog).getByPlaceholderText('norwegian/vocabulary/nouns_to_english'), 'Vocabulary');
    await user.selectOptions(within(modulesDialog).getByLabelText('Parent module'), '1');
    await user.type(within(modulesDialog).getAllByLabelText('Instruction')[1], 'Use the Norwegian term as the prompt.');
    await user.click(within(modulesDialog).getByRole('button', { name: 'Create Module' }));

    expect(createSpy).toHaveBeenCalledWith({
      title: 'Vocabulary',
      parent_id: 1,
      instruction: 'Use the Norwegian term as the prompt.'
    });

    expect(await screen.findByText('Module ready: norwegian.')).toBeTruthy();

    await user.click(within(modulesDialog).getByRole('button', { name: 'Close' }));

    await user.click(screen.getByRole('button', { name: /^Import/ }));
    const importDialog = await screen.findByRole('dialog', { name: 'Import' });
    expect(within(importDialog).getByRole('button', { name: 'Import QML' }).className).toContain('primary-button');
    await user.selectOptions(within(importDialog).getByLabelText('Import target'), '3');
    await user.click(within(importDialog).getByRole('button', { name: 'Import QML' }));
    expect(openImportSpy).toHaveBeenCalledWith(3);

    await user.click(within(importDialog).getByRole('button', { name: 'Close' }));

    await user.click(screen.getByRole('button', { name: /^Export/ }));
    const exportDialog = await screen.findByRole('dialog', { name: 'Export' });
    expect(within(exportDialog).getByRole('button', { name: 'Export content' }).className).toContain('primary-button');
    await user.click(within(exportDialog).getByRole('button', { name: 'Export content' }));
    expect(exportContentSpy).toHaveBeenCalledTimes(1);
    expect(await screen.findByText('Verified content export ready: modules-export.zip.')).toBeTruthy();
  });

  it('shows module and contributions summaries for regular contributors without import or export', async () => {
    const user = userEvent.setup();
    render(AdminPage, {
      props: {
        currentActor: buildAuthActor({ handle: 'alice', display_name: 'Alice', role: 'user' }),
        modules: [
          buildModuleNode({
            id: 1,
            title: 'Nursing',
            slug: 'nursing',
            full_slug: 'nursing',
            children: [
              buildModuleNode({
                id: 2,
                title: 'Checks',
                slug: 'checks',
                full_slug: 'nursing/checks',
                instruction: 'List the safety checks in order.'
              })
            ]
          })
        ],
        users: [],
        selectedModuleId: 2,
        moderationQueue: null,
        contributions: buildMyContributions({
          revisions: [
            buildQuestionRevisionProposal({
              proposal_id: 41,
              module_full_slug: 'nursing/checks',
              current_prompt: 'sanitize',
              proposed_prompt: 'sanitize hands'
            })
          ]
        })
      }
    });

    expect(screen.queryByRole('button', { name: /^Import/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /^Export/ })).toBeNull();
    expect(screen.getByRole('button', { name: /^Modules/ })).toBeTruthy();
    expect(screen.getByRole('button', { name: /^My contributions/ })).toBeTruthy();

    await user.click(screen.getByRole('button', { name: /^My contributions/ }));
    const contributionsDialog = await screen.findByRole('dialog', { name: 'My contributions' });
    await user.click(within(contributionsDialog).getByRole('button', { name: /^nursing\/checks/i }));
    expect(await screen.findByRole('dialog', { name: 'Revision detail' })).toBeTruthy();
  });
});
