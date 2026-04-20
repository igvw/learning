<script lang="ts">
  import type { PendingRevisionSection } from '../../lib/revision-review';
  import type {
    BulkModerationResult,
    BulkRevisionModerationItem,
    ModerationActionPayload,
    ModerationRevisionActionPayload,
    QuestionRevisionProposal
  } from '../../lib/types';
  import RevisionSnapshot from './RevisionSnapshot.svelte';

  type StatusTone = 'success' | 'error' | 'info';

  export let section: PendingRevisionSection;
  export let onRevisionModeration: (
    proposalId: number,
    payload: ModerationRevisionActionPayload
  ) => Promise<void> = async () => {
    throw new Error('Revision moderation handler is not configured.');
  };
  export let onBulkRevisionModeration: (
    items: BulkRevisionModerationItem[],
    payload: ModerationActionPayload
  ) => Promise<BulkModerationResult> = async () => {
    throw new Error('Bulk revision moderation handler is not configured.');
  };
  export let onOpenRevisionEditor: (proposal: QuestionRevisionProposal) => void = () => {};

  let expanded = false;
  let moderationBusyKey = '';
  let revisionBulkBusy = false;
  let revisionBulkStatusMessage = '';
  let revisionBulkStatusTone: StatusTone = 'info';
  let selectedRevisionProposalIds: number[] = [];
  let revisionResetStates: Record<number, boolean> = {};

  $: moderationLocked = Boolean(moderationBusyKey) || revisionBulkBusy;
  $: visibleRevisionIds = new Set(section.revisions.map((entry) => entry.proposal.proposal_id));
  $: if (selectedRevisionProposalIds.some((proposalId) => !visibleRevisionIds.has(proposalId))) {
    selectedRevisionProposalIds = selectedRevisionProposalIds.filter((proposalId) => visibleRevisionIds.has(proposalId));
  }
  $: {
    const nextResetStates: Record<number, boolean> = {};
    for (const proposalId of visibleRevisionIds) {
      nextResetStates[proposalId] = revisionResetStates[proposalId] ?? true;
    }
    const currentKeys = Object.keys(revisionResetStates);
    const nextKeys = Object.keys(nextResetStates);
    const resetStatesChanged =
      currentKeys.length !== nextKeys.length ||
      nextKeys.some((key) => revisionResetStates[Number(key)] !== nextResetStates[Number(key)]);
    if (resetStatesChanged) {
      revisionResetStates = nextResetStates;
    }
  }
  $: allRevisionsInSectionSelected =
    section.revisions.length > 0 &&
    section.revisions.every((entry) => selectedRevisionProposalIds.includes(entry.proposal.proposal_id));
  $: selectedRevisionsInSection =
    section.revisions.filter((entry) => selectedRevisionProposalIds.includes(entry.proposal.proposal_id)).length;

  function toggleRevisionSelection(selected: boolean): void {
    const proposalIds = section.revisions.map((entry) => entry.proposal.proposal_id);
    if (selected) {
      selectedRevisionProposalIds = [...new Set([...selectedRevisionProposalIds, ...proposalIds])];
      return;
    }
    selectedRevisionProposalIds = selectedRevisionProposalIds.filter((proposalId) => !proposalIds.includes(proposalId));
  }

  function revisionResetState(proposalId: number): boolean {
    return revisionResetStates[proposalId] ?? true;
  }

  function setRevisionResetState(proposalId: number, value: boolean): void {
    revisionResetStates = { ...revisionResetStates, [proposalId]: value };
  }

  function bulkStatus(
    result: BulkModerationResult,
    action: Extract<ModerationActionPayload['action'], 'approve' | 'reject'>,
    noun: string
  ): { message: string; tone: StatusTone } {
    const actionLabel = action === 'approve' ? 'Approved' : 'Rejected';
    const actionVerb = action === 'approve' ? 'approved' : 'rejected';
    return {
      tone: result.failed === 0 ? 'success' : result.succeeded === 0 ? 'error' : 'info',
      message:
        result.failed === 0
          ? `${actionLabel} ${result.succeeded} ${result.succeeded === 1 ? noun : `${noun}s`}.`
          : `${actionLabel} ${result.succeeded} ${result.succeeded === 1 ? noun : `${noun}s`}. ${result.failed} could not be ${actionVerb}.`
    };
  }

  async function handleRevisionModeration(
    proposalId: number,
    action: ModerationActionPayload['action']
  ): Promise<void> {
    moderationBusyKey = `revision:${proposalId}:${action}`;
    revisionBulkStatusMessage = '';
    try {
      await onRevisionModeration(proposalId, {
        action,
        note: '',
        ...(action === 'approve' ? { reset_stats: revisionResetState(proposalId) } : {})
      });
    } finally {
      moderationBusyKey = '';
    }
  }

  async function handleBulkModeration(
    action: Extract<ModerationActionPayload['action'], 'approve' | 'reject'>
  ): Promise<void> {
    const selectedItemsInSection = section.revisions
      .map((entry) => ({
        proposalId: entry.proposal.proposal_id,
        resetStats: revisionResetState(entry.proposal.proposal_id)
      }))
      .filter((item) => selectedRevisionProposalIds.includes(item.proposalId));
    const items: BulkRevisionModerationItem[] =
      selectedItemsInSection.length > 0
        ? selectedItemsInSection
        : section.revisions.map((entry) => ({
            proposalId: entry.proposal.proposal_id,
            resetStats: revisionResetState(entry.proposal.proposal_id)
          }));
    if (items.length === 0) {
      return;
    }

    revisionBulkBusy = true;
    revisionBulkStatusMessage = '';

    try {
      const result = await onBulkRevisionModeration(items, { action, note: '' });
      const status = bulkStatus(result, action, 'revision');
      revisionBulkStatusTone = status.tone;
      revisionBulkStatusMessage = status.message;

      if (result.failed === 0) {
        selectedRevisionProposalIds = selectedRevisionProposalIds.filter(
          (proposalId) => !items.some((item) => item.proposalId === proposalId)
        );
      }
    } finally {
      revisionBulkBusy = false;
    }
  }
</script>

<section class="dynamic-card moderation-revision-section">
  <button
    type="button"
    class="moderation-section-toggle"
    aria-expanded={expanded}
    on:click={() => {
      expanded = !expanded;
    }}
  >
    <div>
      <strong>{section.title}</strong>
      <p class="muted-copy">{section.revisions.length} proposals.</p>
    </div>
    <span class="moderation-summary-count">{section.revisions.length}</span>
  </button>

  {#if expanded}
    {#if revisionBulkStatusMessage}
      <div
        class={`banner ${revisionBulkStatusTone === 'success' ? 'success' : revisionBulkStatusTone === 'error' ? 'error' : 'info'}`}
      >
        {revisionBulkStatusMessage}
      </div>
    {/if}

    <div class="moderation-question-toolbar">
      <p class="muted-copy">{selectedRevisionsInSection} selected.</p>
      <div class="drawer-actions">
        <button
          class="primary-button"
          type="button"
          disabled={section.revisions.length === 0 || moderationLocked}
          on:click={() => void handleBulkModeration('approve')}
        >
          Approve selected
        </button>
        <button
          class="ghost-button"
          type="button"
          disabled={section.revisions.length === 0 || moderationLocked}
          on:click={() => void handleBulkModeration('reject')}
        >
          Reject selected
        </button>
      </div>
    </div>

    <div class="moderation-question-table-shell">
      <table class="moderation-question-table moderation-revision-table">
        <thead>
          <tr>
            <th class="moderation-checkbox-column">
              <input
                type="checkbox"
                aria-label={`Select all revisions in ${section.title}`}
                checked={allRevisionsInSectionSelected}
                disabled={moderationLocked}
                on:change={(event) => toggleRevisionSelection((event.currentTarget as HTMLInputElement).checked)}
              />
            </th>
            <th>Changes</th>
            <th>By</th>
            <th class="moderation-reset-column">Reset</th>
            <th class="moderation-actions-column">Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each section.revisions as entry (entry.proposal.proposal_id)}
            {@const revision = entry.proposal}
            <tr>
              <td class="moderation-checkbox-column">
                <input
                  type="checkbox"
                  aria-label={`Select revision proposal for ${revision.current_prompt}`}
                  value={revision.proposal_id}
                  disabled={moderationLocked}
                  bind:group={selectedRevisionProposalIds}
                />
              </td>
              <td>
                <RevisionSnapshot
                  proposal={revision}
                  interactive={true}
                  disabled={moderationLocked}
                  ariaLabel={`Open revision editor for ${revision.current_prompt}`}
                  onClick={() => onOpenRevisionEditor(revision)}
                />
              </td>
              <td>{revision.proposer_display_name ?? 'Unknown'}</td>
              <td class="moderation-reset-column">
                <input
                  type="checkbox"
                  aria-label={`Reset stats for revision proposal for ${revision.current_prompt}`}
                  checked={revisionResetState(revision.proposal_id)}
                  disabled={moderationLocked}
                  on:change={(event) =>
                    setRevisionResetState(
                      revision.proposal_id,
                      (event.currentTarget as HTMLInputElement).checked
                    )}
                />
              </td>
              <td class="moderation-actions-column">
                <div class="moderation-row-actions icon-stack">
                  <button
                    class="moderation-icon-button approve"
                    type="button"
                    aria-label={`Approve revision proposal for ${revision.current_prompt}`}
                    disabled={moderationLocked}
                    on:click={() => void handleRevisionModeration(revision.proposal_id, 'approve')}
                  >
                    ✓
                  </button>
                  <button
                    class="moderation-icon-button reject"
                    type="button"
                    aria-label={`Reject revision proposal for ${revision.current_prompt}`}
                    disabled={moderationLocked}
                    on:click={() => void handleRevisionModeration(revision.proposal_id, 'reject')}
                  >
                    ×
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>
