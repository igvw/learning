<script lang="ts">
  import { groupPendingRevisionsByModule, revisionSectionsForModule } from '../../lib/revision-review';
  import type {
    BulkModerationResult,
    BulkRevisionModerationItem,
    ModerationActionPayload,
    ModerationRevisionActionPayload,
    QuestionRevisionProposal
  } from '../../lib/types';
  import ModerationOverlay from './ModerationOverlay.svelte';
  import PendingRevisionSectionTable from './PendingRevisionSectionTable.svelte';

  export let open = false;
  export let pendingRevisions: QuestionRevisionProposal[] = [];
  export let onClose: () => void = () => {};
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

  let selectedRevisionModuleSlug = '';

  $: groupedPendingRevisions = groupPendingRevisionsByModule(pendingRevisions);
  $: if (
    selectedRevisionModuleSlug &&
    !groupedPendingRevisions.some((group) => group.moduleFullSlug === selectedRevisionModuleSlug)
  ) {
    selectedRevisionModuleSlug = '';
  }
  $: selectedRevisionGroup =
    groupedPendingRevisions.find((group) => group.moduleFullSlug === selectedRevisionModuleSlug) ?? null;
  $: revisionSections = selectedRevisionGroup ? revisionSectionsForModule(selectedRevisionGroup) : [];
  $: copy = selectedRevisionGroup
    ? 'Open a change section to review that batch. Click any snapshot card to edit and approve it in the drawer.'
    : 'Choose a module to review its pending revisions.';

  function openRevisionModule(moduleFullSlug: string): void {
    selectedRevisionModuleSlug = moduleFullSlug;
  }

  function closeRevisionModule(): void {
    selectedRevisionModuleSlug = '';
  }
</script>

<ModerationOverlay
  {open}
  eyebrow="Moderation"
  title="Pending revisions"
  titleId="pending-revisions-title"
  {copy}
  {onClose}
>
  {#if groupedPendingRevisions.length === 0}
    <p class="muted-copy">No pending revisions right now.</p>
  {:else if !selectedRevisionGroup}
    <div class="moderation-summary-grid revision-module-grid">
      {#each groupedPendingRevisions as group (group.moduleFullSlug)}
        <button
          type="button"
          class="dynamic-card moderation-summary-card revision-module-card"
          aria-label={`Open pending revisions for ${group.moduleFullSlug}`}
          on:click={() => openRevisionModule(group.moduleFullSlug)}
        >
          <span class="eyebrow">Module</span>
          <strong>{group.moduleFullSlug}</strong>
          <span class="moderation-summary-count">{group.revisions.length}</span>
        </button>
      {/each}
    </div>
  {:else}
    <div class="moderation-overlay-stack">
      <div class="subsection-header moderation-detail-header">
        <div>
          <strong>{selectedRevisionGroup.moduleFullSlug}</strong>
          <p class="muted-copy">{selectedRevisionGroup.revisions.length} pending revisions.</p>
        </div>
        <button type="button" class="ghost-button" on:click={closeRevisionModule}>Back to modules</button>
      </div>

      {#each revisionSections as section (section.key)}
        <PendingRevisionSectionTable
          {section}
          {onRevisionModeration}
          {onBulkRevisionModeration}
          {onOpenRevisionEditor}
        />
      {/each}
    </div>
  {/if}
</ModerationOverlay>
