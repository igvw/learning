<script lang="ts">
  import type { ModerationActionPayload, PendingModule } from '../../lib/types';
  import { reviewBadge } from '../../lib/moderation-display';
  import ModerationOverlay from './ModerationOverlay.svelte';

  export let open = false;
  export let pendingModules: PendingModule[] = [];
  export let onClose: () => void = () => {};
  export let onModuleModeration: (moduleId: number, payload: ModerationActionPayload) => Promise<void> = async () => {
    throw new Error('Module moderation handler is not configured.');
  };

  let moderationBusyKey = '';

  $: moderationLocked = Boolean(moderationBusyKey);

  async function handleModeration(moduleId: number, action: ModerationActionPayload['action']): Promise<void> {
    moderationBusyKey = `module:${moduleId}:${action}`;
    try {
      await onModuleModeration(moduleId, { action, note: '' });
    } finally {
      moderationBusyKey = '';
    }
  }
</script>

<ModerationOverlay
  {open}
  eyebrow="Moderation"
  title="Pending modules"
  titleId="pending-modules-title"
  copy="Review new module submissions one by one."
  {onClose}
>
  {#if pendingModules.length === 0}
    <p class="muted-copy">No pending modules right now.</p>
  {:else}
    <div class="moderation-overlay-stack">
      {#each pendingModules as module (module.id)}
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
            <button
              class="primary-button"
              type="button"
              disabled={moderationLocked}
              on:click={() => void handleModeration(module.id, 'approve')}
            >
              Approve
            </button>
            <button
              class="ghost-button"
              type="button"
              disabled={moderationLocked}
              on:click={() => void handleModeration(module.id, 'changes_requested')}
            >
              Request changes
            </button>
            <button
              class="ghost-button"
              type="button"
              disabled={moderationLocked}
              on:click={() => void handleModeration(module.id, 'reject')}
            >
              Reject
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</ModerationOverlay>
