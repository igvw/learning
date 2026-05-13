import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import ModerationQueuePanel from '../src/components/admin/ModerationQueuePanel.svelte';
import { buildModerationQueue } from './builders';

describe('ModerationQueuePanel', () => {
  it('shows summary cards, opens overlays, and supports bulk approve by module', async () => {
    const user = userEvent.setup();
    const moderationSpy = vi.fn().mockResolvedValue(undefined);
    const deleteRejectedModuleSpy = vi.fn().mockResolvedValue(undefined);
    const bulkSpy = vi.fn().mockResolvedValue({ succeeded: 2, failed: 0 });

    render(ModerationQueuePanel, {
      props: {
        moderationQueue: buildModerationQueue({
          pending_modules: [
            {
              id: 7,
              title: 'Vocabulary',
              full_slug: 'norwegian/vocabulary',
              parent_id: 1,
              instruction: 'Translate the Norwegian term into English.',
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 2,
              creator_display_name: 'Alice',
              admin_review_note: ''
            }
          ],
          rejected_modules: [
            {
              id: 8,
              title: 'Animals',
              full_slug: 'norwegian/animals',
              parent_id: 1,
              instruction: 'Translate the animal into English.',
              admin_verified: false,
              moderation_status: 'rejected',
              created_by_user_id: 2,
              creator_display_name: 'Alice',
              admin_review_note: 'Needs a different structure.'
            }
          ],
          pending_questions: [
            {
              question_id: 11,
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              prompt: 'hund',
              question_type: 'single_text',
              rank: 1,
              accepted_answers: [['dog']],
              segments: [],
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 2,
              creator_display_name: 'Alice',
              admin_review_note: ''
            },
            {
              question_id: 12,
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              prompt: 'katt',
              question_type: 'single_text',
              rank: 2,
              accepted_answers: [['cat']],
              segments: [],
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 2,
              creator_display_name: 'Alice',
              admin_review_note: ''
            }
          ]
        }),
        onModerationAction: moderationSpy,
        onDeleteRejectedModule: deleteRejectedModuleSpy,
        onBulkQuestionModeration: bulkSpy
      }
    });

    expect(screen.getByRole('button', { name: /^Modules/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /^Uploads/i })).toBeTruthy();
    expect(screen.queryByRole('button', { name: /^Revisions/i })).toBeNull();

    await user.click(screen.getByRole('button', { name: /^Modules/i }));
    expect(screen.getByRole('heading', { name: 'Modules' })).toBeTruthy();
    expect(screen.getByRole('button', { name: /^Pending/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /^Rejected/i })).toBeTruthy();

    await user.click(screen.getByRole('button', { name: /^Pending/i }));
    expect(screen.getByRole('heading', { name: 'Pending modules' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Back' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Approve' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Reject' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Reject' }));
    expect(moderationSpy).toHaveBeenCalledWith('module', 7, { action: 'reject', note: '' });

    await user.click(screen.getByRole('button', { name: 'Back' }));
    await user.click(screen.getByRole('button', { name: /^Rejected/i }));
    expect(screen.getByRole('heading', { name: 'Rejected modules' })).toBeTruthy();
    expect(screen.getByText('Needs a different structure.')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Approve' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    expect(deleteRejectedModuleSpy).toHaveBeenCalledWith(8);

    await user.click(screen.getByRole('button', { name: 'Close' }));

    await user.click(screen.getByRole('button', { name: /^Uploads/i }));
    expect(screen.getByRole('heading', { name: 'Pending uploaded questions' })).toBeTruthy();
    expect(screen.getByText('norwegian/vocabulary/noun2en')).toBeTruthy();

    await user.click(screen.getByLabelText('Select all pending questions in norwegian/vocabulary/noun2en'));
    await user.click(screen.getByRole('button', { name: 'Approve selected' }));

    expect(bulkSpy).toHaveBeenCalledWith([11, 12], { action: 'approve', note: '' });
    expect(await screen.findByText('Approved 2 questions.')).toBeTruthy();

    await user.click(screen.getAllByRole('button', { name: 'Reject' })[0]);
    expect(moderationSpy).toHaveBeenCalledWith('question', 11, { action: 'reject', note: '' });
  });

  it('reports partial bulk failures without removing the remaining selection', async () => {
    const user = userEvent.setup();
    const bulkSpy = vi.fn().mockResolvedValue({ succeeded: 1, failed: 1 });

    render(ModerationQueuePanel, {
      props: {
        moderationQueue: buildModerationQueue({
          pending_questions: [
            {
              question_id: 31,
              module_id: 9,
              module_full_slug: 'science/chemistry',
              prompt: 'H2O',
              question_type: 'single_text',
              rank: 1,
              accepted_answers: [['water']],
              segments: [],
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 4,
              creator_display_name: 'Chris',
              admin_review_note: ''
            },
            {
              question_id: 32,
              module_id: 9,
              module_full_slug: 'science/chemistry',
              prompt: 'NaCl',
              question_type: 'single_text',
              rank: 2,
              accepted_answers: [['salt']],
              segments: [],
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 4,
              creator_display_name: 'Chris',
              admin_review_note: ''
            }
          ]
        }),
        onModerationAction: vi.fn().mockResolvedValue(undefined),
        onBulkQuestionModeration: bulkSpy
      }
    });

    await user.click(screen.getByRole('button', { name: /^Uploads/i }));
    await user.click(screen.getByLabelText('Select all pending questions in science/chemistry'));
    await user.click(screen.getByRole('button', { name: 'Reject selected' }));

    expect(bulkSpy).toHaveBeenCalledWith([31, 32], { action: 'reject', note: '' });
    expect(await screen.findByText('Rejected 1 question. 1 could not be rejected.')).toBeTruthy();
    expect((screen.getByLabelText('Select pending question H2O') as HTMLInputElement).checked).toBe(true);
  });
});
