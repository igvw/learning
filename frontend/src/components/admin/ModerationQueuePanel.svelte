<script lang="ts">
  import type {
    BulkModerationResult,
    ModerationActionPayload,
    ModerationKind,
    ModerationQueue,
    ModerationRevisionActionPayload
  } from '../../lib/types';
  import ModerationSummaryCards from './ModerationSummaryCards.svelte';
  import PendingModulesOverlay from './PendingModulesOverlay.svelte';
  import PendingQuestionsOverlay from './PendingQuestionsOverlay.svelte';

  type ModerationOverlayKind = 'modules' | 'questions' | null;

  export let moderationQueue: ModerationQueue | null = null;
  export let onModerationAction: (
    kind: ModerationKind,
    id: number,
    payload: ModerationRevisionActionPayload
  ) => Promise<void> = async () => {
    throw new Error('Moderation handler is not configured.');
  };
  export let onDeleteRejectedModule: (moduleId: number) => Promise<void> = async () => {
    throw new Error('Rejected module delete handler is not configured.');
  };
  export let onBulkQuestionModeration: (
    questionIds: number[],
    payload: ModerationActionPayload
  ) => Promise<BulkModerationResult> = async () => {
    throw new Error('Bulk moderation handler is not configured.');
  };
  let openOverlay: ModerationOverlayKind = null;

  $: pendingModules = moderationQueue?.pending_modules ?? [];
  $: rejectedModules = moderationQueue?.rejected_modules ?? [];
  $: pendingQuestions = moderationQueue?.pending_questions ?? [];

  function openModerationOverlay(kind: Exclude<ModerationOverlayKind, null>): void {
    openOverlay = kind;
  }

  function closeModerationOverlay(): void {
    openOverlay = null;
  }
</script>

{#if moderationQueue}
  <ModerationSummaryCards
    pendingModulesCount={pendingModules.length}
    rejectedModulesCount={rejectedModules.length}
    pendingQuestionsCount={pendingQuestions.length}
    onOpen={openModerationOverlay}
  />

  <PendingModulesOverlay
    open={openOverlay === 'modules'}
    {pendingModules}
    {rejectedModules}
    onClose={closeModerationOverlay}
    onModuleModeration={(id, payload) => onModerationAction('module', id, payload)}
    {onDeleteRejectedModule}
  />

  <PendingQuestionsOverlay
    open={openOverlay === 'questions'}
    {pendingQuestions}
    onClose={closeModerationOverlay}
    onQuestionModeration={(id, payload) => onModerationAction('question', id, payload)}
    {onBulkQuestionModeration}
  />
{/if}
