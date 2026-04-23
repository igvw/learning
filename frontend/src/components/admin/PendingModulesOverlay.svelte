<script lang="ts">
  import type { ModerationActionPayload, PendingModule } from '../../lib/types';
  import { reviewBadge } from '../../lib/moderation-display';
  import AdminSummaryCard from './AdminSummaryCard.svelte';
  import ModerationOverlay from './ModerationOverlay.svelte';

  export let open = false;
  export let pendingModules: PendingModule[] = [];
  export let rejectedModules: PendingModule[] = [];
  export let onClose: () => void = () => {};
  export let onModuleModeration: (moduleId: number, payload: ModerationActionPayload) => Promise<void> = async () => {
    throw new Error('Module moderation handler is not configured.');
  };
  export let onDeleteRejectedModule: (moduleId: number) => Promise<void> = async () => {
    throw new Error('Rejected module delete handler is not configured.');
  };

  let moderationBusyKey = '';
  let selectedView: 'pending' | 'rejected' | null = null;

  $: moderationLocked = Boolean(moderationBusyKey);
  $: if (!open) {
    moderationBusyKey = '';
    selectedView = null;
  }
  $: activeModules = selectedView === 'rejected' ? rejectedModules : pendingModules;
  $: activeTitle = selectedView === null ? 'Modules' : selectedView === 'pending' ? 'Pending modules' : 'Rejected modules';
  $: activeCopy =
    selectedView === null
      ? 'Choose which module submissions to review.'
      : selectedView === 'pending'
        ? 'Review new module submissions one by one.'
        : 'Revisit rejected module submissions or delete rejected subtrees.';

  async function handleModeration(moduleId: number, action: ModerationActionPayload['action']): Promise<void> {
    moderationBusyKey = `module:${moduleId}:${action}`;
    try {
      await onModuleModeration(moduleId, { action, note: '' });
    } finally {
      moderationBusyKey = '';
    }
  }

  async function handleDelete(moduleId: number): Promise<void> {
    moderationBusyKey = `module:${moduleId}:delete`;
    try {
      await onDeleteRejectedModule(moduleId);
    } finally {
      moderationBusyKey = '';
    }
  }
</script>

<ModerationOverlay
  {open}
  eyebrow=""
  title={activeTitle}
  titleId="pending-modules-title"
  copy={activeCopy}
  {onClose}
>
  {#if selectedView === null}
    <div class="admin-summary-grid">
      <AdminSummaryCard
        title="Pending"
        detail="Ready for review."
        countLabel={String(pendingModules.length)}
        onClick={() => {
          selectedView = 'pending';
        }}
      />
      <AdminSummaryCard
        title="Rejected"
        detail="Rejected but still reviewable."
        countLabel={String(rejectedModules.length)}
        onClick={() => {
          selectedView = 'rejected';
        }}
      />
    </div>

    {#if pendingModules.length + rejectedModules.length === 0}
      <p class="muted-copy">No module submissions need moderation right now.</p>
    {/if}
  {:else}
    <div class="moderation-overlay-stack">
      <div class="drawer-actions">
        <button
          class="ghost-button"
          type="button"
          disabled={moderationLocked}
          on:click={() => {
            selectedView = null;
          }}
        >
          Back
        </button>
      </div>

      {#if activeModules.length === 0}
        <p class="muted-copy">{selectedView === 'pending' ? 'No pending modules right now.' : 'No rejected modules right now.'}</p>
      {/if}

      {#each activeModules as module (module.id)}
        <div class="dynamic-card compact-dynamic-card">
          <div class="subsection-header">
            <strong>Module: {module.full_slug}</strong>
            <span class="muted-copy">{reviewBadge(module.moderation_status, module.admin_verified)}</span>
          </div>
          <p class="muted-copy">By {module.creator_display_name ?? 'Unknown'}.</p>
          {#if module.instruction}
            <p class="muted-copy">{module.instruction}</p>
          {/if}
          {#if module.admin_review_note}
            <p class="muted-copy">{module.admin_review_note}</p>
          {/if}
          <div class="drawer-actions">
            <button
              class="primary-button"
              type="button"
              disabled={moderationLocked}
              on:click={() => void handleModeration(module.id, 'approve')}
            >
              Approve
            </button>
            {#if selectedView === 'pending'}
              <button
                class="ghost-button"
                type="button"
                disabled={moderationLocked}
                on:click={() => void handleModeration(module.id, 'reject')}
              >
                Reject
              </button>
            {:else}
              <button
                class="danger-button"
                type="button"
                disabled={moderationLocked}
                on:click={() => void handleDelete(module.id)}
              >
                Delete
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</ModerationOverlay>
