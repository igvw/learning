import { render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import ModerationQueuePanel from '../src/components/admin/ModerationQueuePanel.svelte';
import { buildModerationQueue, buildQuestionRevisionProposal } from './builders';

describe('ModerationQueuePanel', () => {
  it('shows summary cards, opens overlays, and supports bulk approve by module', async () => {
    const user = userEvent.setup();
    const moderationSpy = vi.fn().mockResolvedValue(undefined);
    const deleteRejectedModuleSpy = vi.fn().mockResolvedValue(undefined);
    const bulkSpy = vi.fn().mockResolvedValue({ succeeded: 2, failed: 0 });
    const bulkRevisionSpy = vi.fn().mockResolvedValue({ succeeded: 1, failed: 0 });
    const openRevisionEditorSpy = vi.fn();

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
          ],
          pending_revisions: [
            buildQuestionRevisionProposal({
              proposal_id: 21,
              question_id: 5,
              proposer_user_id: 3,
              proposer_display_name: 'Bob',
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              current_prompt: 'dag',
              current_question_type: 'single_text',
              current_accepted_answers: [['day']],
              proposed_prompt: 'dagen',
              proposed_question_type: 'single_text',
              proposed_accepted_answers: [['the day']]
            }),
            buildQuestionRevisionProposal({
              proposal_id: 22,
              question_id: 6,
              proposer_user_id: 3,
              proposer_display_name: 'Bob',
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              current_prompt: 'liten',
              current_question_type: 'single_text',
              current_accepted_answers: [['small']],
              proposed_prompt: 'liten',
              proposed_question_type: 'multi_text',
              proposed_accepted_answers: [['small'], ['little']]
            }),
            buildQuestionRevisionProposal({
              proposal_id: 23,
              question_id: 7,
              proposer_user_id: 3,
              proposer_display_name: 'Bob',
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              current_prompt: 'natt',
              current_question_type: 'single_text',
              current_accepted_answers: [['night']],
              proposed_prompt: 'natt',
              proposed_question_type: 'single_text',
              proposed_accepted_answers: [['night']],
              delete_requested: true
            }),
            buildQuestionRevisionProposal({
              proposal_id: 24,
              question_id: 8,
              proposer_user_id: 3,
              proposer_display_name: 'Bob',
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              current_prompt: 'morgen',
              current_question_type: 'inline_cloze',
              current_accepted_answers: [['morning']],
              current_segments: ['It is ', '.'],
              proposed_prompt: 'morgen',
              proposed_question_type: 'inline_cloze',
              proposed_accepted_answers: [['early morning']],
              proposed_segments: ['This is ', '.']
            })
          ]
        }),
        onModerationAction: moderationSpy,
        onDeleteRejectedModule: deleteRejectedModuleSpy,
        onBulkQuestionModeration: bulkSpy,
        onBulkRevisionModeration: bulkRevisionSpy,
        onOpenRevisionEditor: openRevisionEditorSpy
      }
    });

    expect(screen.getByRole('button', { name: /^Modules/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /^Uploads/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /^Revisions/i })).toBeTruthy();

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

    await user.click(screen.getByRole('button', { name: /^Revisions/i }));
    expect(screen.getByRole('heading', { name: 'Pending revisions' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Open pending revisions for norwegian/vocabulary/noun2en' })).toBeTruthy();

    await user.click(screen.getByRole('button', { name: 'Open pending revisions for norwegian/vocabulary/noun2en' }));
    expect(screen.getByRole('button', { name: 'Back to modules' })).toBeTruthy();
    expect(screen.getByText('Delete requests')).toBeTruthy();
    expect(screen.getByText('Type changes')).toBeTruthy();
    expect(screen.getByText('Prompt changes')).toBeTruthy();
    expect(screen.getByText('Answer / segment changes')).toBeTruthy();
    expect(screen.queryByLabelText('Select all revisions in Prompt changes')).toBeNull();

    const revisionsDialog = screen.getByRole('dialog', { name: 'Pending revisions' });
    const promptToggle = within(revisionsDialog).getByText('Prompt changes').closest('button');
    expect(promptToggle).toBeTruthy();
    await user.click(promptToggle as HTMLElement);
    await waitFor(() => {
      expect(screen.getByLabelText('Select all revisions in Prompt changes')).toBeTruthy();
    });
    const promptHeading = screen.getByText('Prompt changes');
    const promptSection = promptHeading.closest('section');
    expect(promptSection).toBeTruthy();
    expect(within(promptSection as HTMLElement).getByRole('columnheader', { name: 'Changes' })).toBeTruthy();
    expect(within(promptSection as HTMLElement).queryByRole('columnheader', { name: 'Question' })).toBeNull();
    expect(within(promptSection as HTMLElement).getByRole('columnheader', { name: 'Reset' })).toBeTruthy();
    expect(within(promptSection as HTMLElement).getByText('Current')).toBeTruthy();
    expect(within(promptSection as HTMLElement).getByText('Proposed')).toBeTruthy();
    expect(within(promptSection as HTMLElement).getAllByText('Single text').length).toBeGreaterThan(0);
    expect(within(promptSection as HTMLElement).queryByText(/^Prompt$/)).toBeNull();
    expect(screen.queryByRole('button', { name: /Request changes/i })).toBeNull();
    expect(
      (within(promptSection as HTMLElement).getByLabelText(
        'Reset stats for revision proposal for dag'
      ) as HTMLInputElement).checked
    ).toBe(true);

    await user.click(screen.getByRole('button', { name: 'Open revision editor for dag' }));
    expect(openRevisionEditorSpy).toHaveBeenCalledWith(expect.objectContaining({ proposal_id: 21 }));

    await user.click(screen.getByLabelText('Select all revisions in Prompt changes'));
    await user.click(within(promptSection as HTMLElement).getByRole('button', { name: 'Approve selected' }));

    expect(bulkRevisionSpy).toHaveBeenCalledWith([{ proposalId: 21, resetStats: true }], {
      action: 'approve',
      note: ''
    });
    expect(await screen.findByText('Approved 1 revision.')).toBeTruthy();

    const deleteToggle = within(revisionsDialog).getByText('Delete requests').closest('button');
    expect(deleteToggle).toBeTruthy();
    await user.click(deleteToggle as HTMLElement);
    const deleteHeading = screen.getByText('Delete requests');
    const deleteSection = deleteHeading.closest('section');
    expect(deleteSection).toBeTruthy();
    expect(within(deleteSection as HTMLElement).queryByText('Proposed')).toBeNull();
    expect(within(deleteSection as HTMLElement).queryByText(/^Delete$/)).toBeNull();
    expect(within(deleteSection as HTMLElement).getByText('natt')).toBeTruthy();
    expect(within(deleteSection as HTMLElement).getByRole('button', { name: 'Approve revision proposal for natt' })).toBeTruthy();
    expect(within(deleteSection as HTMLElement).getByRole('button', { name: 'Reject revision proposal for natt' })).toBeTruthy();

    await user.click(screen.getByRole('button', { name: 'Back to modules' }));
    expect(screen.getByRole('button', { name: 'Open pending revisions for norwegian/vocabulary/noun2en' })).toBeTruthy();
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
