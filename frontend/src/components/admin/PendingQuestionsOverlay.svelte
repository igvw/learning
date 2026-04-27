<script lang="ts">
  import { groupPendingQuestionsByModule } from '../../lib/pending-questions';
  import type { BulkModerationResult, ModerationActionPayload, PendingQuestion } from '../../lib/types';
  import ModerationOverlay from './ModerationOverlay.svelte';
  import PendingQuestionGroupTable from './PendingQuestionGroupTable.svelte';

  export let open = false;
  export let pendingQuestions: PendingQuestion[] = [];
  export let onClose: () => void = () => {};
  export let onQuestionModeration: (questionId: number, payload: ModerationActionPayload) => Promise<void> = async () => {
    throw new Error('Question moderation handler is not configured.');
  };
  export let onBulkQuestionModeration: (
    questionIds: number[],
    payload: ModerationActionPayload
  ) => Promise<BulkModerationResult> = async () => {
    throw new Error('Bulk question moderation handler is not configured.');
  };

  $: groupedPendingQuestions = groupPendingQuestionsByModule(pendingQuestions);
</script>

<ModerationOverlay
  {open}
  eyebrow="Moderation"
  title="Pending uploaded questions"
  titleId="pending-questions-title"
  copy="Bulk actions work per module table. Select rows to narrow the batch; request changes stays available per row."
  {onClose}
>
  {#if groupedPendingQuestions.length === 0}
    <p class="muted-copy">No pending uploaded questions right now.</p>
  {:else}
    <div class="moderation-overlay-stack">
      {#each groupedPendingQuestions as group (group.moduleFullSlug)}
        <PendingQuestionGroupTable
          {group}
          {onQuestionModeration}
          {onBulkQuestionModeration}
        />
      {/each}
    </div>
  {/if}
</ModerationOverlay>
