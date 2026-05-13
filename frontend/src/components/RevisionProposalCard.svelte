<script lang="ts">
  import RevisionSnapshot from './admin/RevisionSnapshot.svelte';
  import type { ModerationRevisionActionPayload, QuestionRevisionProposal } from '../lib/types';

  export let proposal: QuestionRevisionProposal;
  export let isAdmin = false;
  export let busyKey = '';
  export let onOpenEditor: (proposal: QuestionRevisionProposal) => void = () => {};
  export let onWithdraw: (questionId: number) => Promise<void> | void = () => {};
  export let onModeration: (proposalId: number, payload: ModerationRevisionActionPayload) => Promise<void> | void = () => {};

  let resetStats = true;

  $: approveBusy = busyKey === `revision:${proposal.proposal_id}:approve`;
  $: rejectBusy = busyKey === `revision:${proposal.proposal_id}:reject`;
  $: withdrawBusy = busyKey === `revision:${proposal.proposal_id}:withdraw`;
  $: cardBusy = Boolean(busyKey);
</script>

<article class="dynamic-card revision-proposal-card">
  <div class="subsection-header revision-proposal-header">
    <div>
      <strong>{proposal.module_full_slug}</strong>
      <p class="muted-copy">
        {proposal.delete_requested ? 'Delete request' : 'Revision proposal'}
        {#if isAdmin && proposal.proposer_display_name}
          by {proposal.proposer_display_name}
        {/if}
      </p>
    </div>
  </div>

  <RevisionSnapshot {proposal} />

  {#if proposal.admin_review_note}
    <div class="banner info">{proposal.admin_review_note}</div>
  {/if}

  <div class="revision-proposal-actions">
    {#if isAdmin}
      <label class="checkbox-field dense-checkbox-field">
        <input type="checkbox" bind:checked={resetStats} disabled={cardBusy} />
        <span>Reset stats</span>
      </label>
      <button class="ghost-button" type="button" disabled={cardBusy} on:click={() => onOpenEditor(proposal)}>
        Edit then approve
      </button>
      <button
        class="primary-button"
        type="button"
        disabled={cardBusy}
        on:click={() => onModeration(proposal.proposal_id, { action: 'approve', note: '', reset_stats: resetStats })}
      >
        {approveBusy ? 'Approving...' : 'Approve'}
      </button>
      <button
        class="danger-button"
        type="button"
        disabled={cardBusy}
        on:click={() => onModeration(proposal.proposal_id, { action: 'reject', note: '' })}
      >
        {rejectBusy ? 'Rejecting...' : 'Reject'}
      </button>
    {:else}
      <button class="ghost-button" type="button" disabled={cardBusy} on:click={() => onOpenEditor(proposal)}>
        Edit proposal
      </button>
      <button class="danger-button" type="button" disabled={cardBusy} on:click={() => onWithdraw(proposal.question_id)}>
        {withdrawBusy ? 'Removing...' : 'Remove from review'}
      </button>
    {/if}
  </div>
</article>
