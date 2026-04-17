<script lang="ts">
  import { reviewBadge } from '../../lib/admin-page';
  import type { ModerationActionPayload, ModerationQueue } from '../../lib/types';

  export let moderationQueue: ModerationQueue | null = null;
  export let onModerationAction: (
    kind: 'module' | 'question' | 'revision',
    id: number,
    payload: ModerationActionPayload
  ) => Promise<void> = async () => {
    throw new Error('Moderation handler is not configured.');
  };

  let moderationBusyKey = '';

  async function handleModeration(
    kind: 'module' | 'question' | 'revision',
    id: number,
    action: ModerationActionPayload['action']
  ): Promise<void> {
    moderationBusyKey = `${kind}:${id}:${action}`;
    try {
      await onModerationAction(kind, id, { action, note: '' });
    } finally {
      moderationBusyKey = '';
    }
  }
</script>

{#if moderationQueue}
  <article class="panel admin-bar-panel">
    <div class="panel-header">
      <div><h3>Moderation queue</h3></div>
    </div>

    {#if moderationQueue.pending_modules.length === 0 && moderationQueue.pending_questions.length === 0 && moderationQueue.pending_revisions.length === 0}
      <p class="muted-copy">No pending submissions right now.</p>
    {/if}

    {#each moderationQueue.pending_modules as module (module.id)}
      <div class="dynamic-card compact-dynamic-card">
        <div class="subsection-header">
          <strong>Module: {module.full_slug}</strong>
          <span class="muted-copy">{reviewBadge(module.moderation_status, module.admin_verified)}</span>
        </div>
        <p class="muted-copy">By {module.creator_display_name ?? 'Unknown'}.</p>
        {#if module.instruction}
          <p class="muted-copy">{module.instruction}</p>
        {/if}
        <div class="drawer-actions">
          <button class="primary-button" type="button" disabled={Boolean(moderationBusyKey)} on:click={() => void handleModeration('module', module.id, 'approve')}>
            Approve
          </button>
          <button class="ghost-button" type="button" disabled={Boolean(moderationBusyKey)} on:click={() => void handleModeration('module', module.id, 'changes_requested')}>
            Request changes
          </button>
          <button class="ghost-button" type="button" disabled={Boolean(moderationBusyKey)} on:click={() => void handleModeration('module', module.id, 'reject')}>
            Reject
          </button>
        </div>
      </div>
    {/each}

    {#each moderationQueue.pending_questions as question (question.question_id)}
      <div class="dynamic-card compact-dynamic-card">
        <div class="subsection-header">
          <strong>Question: {question.prompt}</strong>
          <span class="muted-copy">{question.module_full_slug}</span>
        </div>
        <p class="muted-copy">By {question.creator_display_name ?? 'Unknown'}.</p>
        <p class="muted-copy">{question.accepted_answers.map((group) => group.join(' / ')).join(' | ')}</p>
        <div class="drawer-actions">
          <button class="primary-button" type="button" disabled={Boolean(moderationBusyKey)} on:click={() => void handleModeration('question', question.question_id, 'approve')}>
            Approve
          </button>
          <button class="ghost-button" type="button" disabled={Boolean(moderationBusyKey)} on:click={() => void handleModeration('question', question.question_id, 'changes_requested')}>
            Request changes
          </button>
          <button class="ghost-button" type="button" disabled={Boolean(moderationBusyKey)} on:click={() => void handleModeration('question', question.question_id, 'reject')}>
            Reject
          </button>
        </div>
      </div>
    {/each}

    {#each moderationQueue.pending_revisions as revision (revision.proposal_id)}
      <div class="dynamic-card compact-dynamic-card">
        <div class="subsection-header">
          <strong>Revision: {revision.module_full_slug}</strong>
          <span class="muted-copy">{revision.proposer_display_name ?? 'Unknown'}</span>
        </div>
        <div class="admin-bar-form">
          <div class="admin-wide-field">
            <h4>Current</h4>
            <p class="muted-copy">{revision.current_prompt}</p>
            <p class="muted-copy">{revision.current_accepted_answers.map((group) => group.join(' / ')).join(' | ')}</p>
          </div>
          <div class="admin-wide-field">
            <h4>Proposed</h4>
            {#if revision.delete_requested}
              <p class="muted-copy">Delete request.</p>
            {:else}
              <p class="muted-copy">{revision.proposed_prompt}</p>
              <p class="muted-copy">{revision.proposed_accepted_answers.map((group) => group.join(' / ')).join(' | ')}</p>
            {/if}
          </div>
        </div>
        <div class="drawer-actions">
          <button class="primary-button" type="button" disabled={Boolean(moderationBusyKey)} on:click={() => void handleModeration('revision', revision.proposal_id, 'approve')}>
            Approve
          </button>
          <button class="ghost-button" type="button" disabled={Boolean(moderationBusyKey)} on:click={() => void handleModeration('revision', revision.proposal_id, 'changes_requested')}>
            Request changes
          </button>
          <button class="ghost-button" type="button" disabled={Boolean(moderationBusyKey)} on:click={() => void handleModeration('revision', revision.proposal_id, 'reject')}>
            Reject
          </button>
        </div>
      </div>
    {/each}
  </article>
{/if}
