<script lang="ts">
  import type {
    BulkRevisionModerationItem,
    BulkModerationResult,
    ModerationActionPayload,
    ModerationKind,
    ModerationQueue,
    ModerationRevisionActionPayload,
    QuestionRevisionProposal
  } from '../../lib/types';
  import ModerationSummaryCards from './ModerationSummaryCards.svelte';
  import PendingModulesOverlay from './PendingModulesOverlay.svelte';
  import PendingQuestionsOverlay from './PendingQuestionsOverlay.svelte';
  import PendingRevisionsOverlay from './PendingRevisionsOverlay.svelte';

  type ModerationOverlayKind = 'modules' | 'questions' | 'revisions' | null;

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
  export let onBulkRevisionModeration: (
    items: BulkRevisionModerationItem[],
    payload: ModerationActionPayload
  ) => Promise<BulkModerationResult> = async () => {
    throw new Error('Bulk revision moderation handler is not configured.');
  };
  export let onOpenRevisionEditor: (proposal: QuestionRevisionProposal) => void = () => {};

  let openOverlay: ModerationOverlayKind = null;

  $: pendingModules = moderationQueue?.pending_modules ?? [];
  $: rejectedModules = moderationQueue?.rejected_modules ?? [];
  $: pendingQuestions = moderationQueue?.pending_questions ?? [];
  $: pendingRevisions = moderationQueue?.pending_revisions ?? [];

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
    pendingRevisionsCount={pendingRevisions.length}
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

  <PendingRevisionsOverlay
    open={openOverlay === 'revisions'}
    {pendingRevisions}
    onClose={closeModerationOverlay}
    onRevisionModeration={(id, payload) => onModerationAction('revision', id, payload)}
    {onBulkRevisionModeration}
    {onOpenRevisionEditor}
  />
{/if}
