<script lang="ts">
  import { groupPendingQuestionsByModule, reviewBadge } from '../../lib/admin-page';
  import type {
    BulkModerationResult,
    ModerationActionPayload,
    ModerationKind,
    ModerationQueue
  } from '../../lib/types';
  import type { PendingQuestionGroup } from '../../lib/admin-page';
  import ModerationOverlay from './ModerationOverlay.svelte';

  type ModerationOverlayKind = 'modules' | 'questions' | 'revisions' | null;
  type StatusTone = 'success' | 'error' | 'info';

  export let moderationQueue: ModerationQueue | null = null;
  export let onModerationAction: (
    kind: ModerationKind,
    id: number,
    payload: ModerationActionPayload
  ) => Promise<void> = async () => {
    throw new Error('Moderation handler is not configured.');
  };
  export let onBulkQuestionModeration: (
    questionIds: number[],
    payload: ModerationActionPayload
  ) => Promise<BulkModerationResult> = async () => {
    throw new Error('Bulk moderation handler is not configured.');
  };

  let moderationBusyKey = '';
  let openOverlay: ModerationOverlayKind = null;
  let selectedQuestionIds: number[] = [];
  let bulkBusyModuleSlug = '';
  let bulkStatusMessage = '';
  let bulkStatusTone: StatusTone = 'info';

  $: pendingModules = moderationQueue?.pending_modules ?? [];
  $: pendingQuestions = moderationQueue?.pending_questions ?? [];
  $: pendingRevisions = moderationQueue?.pending_revisions ?? [];
  $: groupedPendingQuestions = groupPendingQuestionsByModule(pendingQuestions);
  $: totalPendingCount = pendingModules.length + pendingQuestions.length + pendingRevisions.length;
  $: visibleQuestionIds = new Set(pendingQuestions.map((question) => question.question_id));
  $: if (selectedQuestionIds.some((questionId) => !visibleQuestionIds.has(questionId))) {
    selectedQuestionIds = selectedQuestionIds.filter((questionId) => visibleQuestionIds.has(questionId));
  }

  function resetQuestionOverlayState(): void {
    selectedQuestionIds = [];
    bulkBusyModuleSlug = '';
    bulkStatusMessage = '';
    bulkStatusTone = 'info';
  }

  function openModerationOverlay(kind: Exclude<ModerationOverlayKind, null>): void {
    if (kind === 'questions') {
      resetQuestionOverlayState();
    }
    openOverlay = kind;
  }

  function closeModerationOverlay(): void {
    openOverlay = null;
    moderationBusyKey = '';
    resetQuestionOverlayState();
  }

  function allQuestionsSelected(group: PendingQuestionGroup): boolean {
    return group.questions.length > 0 && group.questions.every((question) => selectedQuestionIds.includes(question.question_id));
  }

  function selectedQuestionCount(group: PendingQuestionGroup): number {
    return group.questions.filter((question) => selectedQuestionIds.includes(question.question_id)).length;
  }

  function toggleModuleQuestionSelection(group: PendingQuestionGroup, selected: boolean): void {
    const groupQuestionIds = group.questions.map((question) => question.question_id);
    if (selected) {
      selectedQuestionIds = [...new Set([...selectedQuestionIds, ...groupQuestionIds])];
      return;
    }
    selectedQuestionIds = selectedQuestionIds.filter((questionId) => !groupQuestionIds.includes(questionId));
  }

  async function handleModeration(
    kind: ModerationKind,
    id: number,
    action: ModerationActionPayload['action']
  ): Promise<void> {
    moderationBusyKey = `${kind}:${id}:${action}`;
    bulkStatusMessage = '';
    try {
      await onModerationAction(kind, id, { action, note: '' });
    } finally {
      moderationBusyKey = '';
    }
  }

  async function handleBulkModeration(
    group: PendingQuestionGroup,
    action: Extract<ModerationActionPayload['action'], 'approve' | 'reject'>
  ): Promise<void> {
    const selectedQuestionIdsInGroup = group.questions
      .map((question) => question.question_id)
      .filter((questionId) => selectedQuestionIds.includes(questionId));
    const questionIds = selectedQuestionIdsInGroup.length > 0 ? selectedQuestionIdsInGroup : group.questions.map((question) => question.question_id);
    if (questionIds.length === 0) {
      return;
    }

    bulkBusyModuleSlug = group.moduleFullSlug;
    bulkStatusMessage = '';

    try {
      const result = await onBulkQuestionModeration(questionIds, { action, note: '' });
      const actionLabel = action === 'approve' ? 'Approved' : 'Rejected';
      const actionVerb = action === 'approve' ? 'approved' : 'rejected';
      bulkStatusTone = result.failed === 0 ? 'success' : result.succeeded === 0 ? 'error' : 'info';
      bulkStatusMessage =
        result.failed === 0
          ? `${actionLabel} ${result.succeeded} ${result.succeeded === 1 ? 'question' : 'questions'}.`
          : `${actionLabel} ${result.succeeded} ${result.succeeded === 1 ? 'question' : 'questions'}. ${result.failed} could not be ${actionVerb}.`;

      if (result.failed === 0) {
        selectedQuestionIds = selectedQuestionIds.filter((questionId) => !questionIds.includes(questionId));
      }
    } finally {
      bulkBusyModuleSlug = '';
    }
  }
</script>

{#if moderationQueue}
  <article class="panel admin-bar-panel">
    <div class="panel-header">
      <div>
        <h3>Moderation queue</h3>
        <p class="muted-copy">Open one category at a time so the admin page stays focused.</p>
      </div>
    </div>

    {#if totalPendingCount === 0}
      <p class="muted-copy">No pending submissions right now.</p>
    {/if}

    <div class="moderation-summary-grid">
      <button
        type="button"
        class="dynamic-card moderation-summary-card"
        aria-haspopup="dialog"
        on:click={() => openModerationOverlay('modules')}
      >
        <span class="eyebrow">Modules</span>
        <strong>Pending modules</strong>
        <span class="moderation-summary-count">{pendingModules.length}</span>
      </button>

      <button
        type="button"
        class="dynamic-card moderation-summary-card"
        aria-haspopup="dialog"
        on:click={() => openModerationOverlay('questions')}
      >
        <span class="eyebrow">Uploads</span>
        <strong>Pending uploaded questions</strong>
        <span class="moderation-summary-count">{pendingQuestions.length}</span>
      </button>

      <button
        type="button"
        class="dynamic-card moderation-summary-card"
        aria-haspopup="dialog"
        on:click={() => openModerationOverlay('revisions')}
      >
        <span class="eyebrow">Revisions</span>
        <strong>Pending revisions</strong>
        <span class="moderation-summary-count">{pendingRevisions.length}</span>
      </button>
    </div>
  </article>

  <ModerationOverlay
    open={openOverlay === 'modules'}
    eyebrow="Moderation"
    title="Pending modules"
    titleId="pending-modules-title"
    copy="Review new module submissions one by one."
    onClose={closeModerationOverlay}
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
                disabled={Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                on:click={() => void handleModeration('module', module.id, 'approve')}
              >
                Approve
              </button>
              <button
                class="ghost-button"
                type="button"
                disabled={Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                on:click={() => void handleModeration('module', module.id, 'changes_requested')}
              >
                Request changes
              </button>
              <button
                class="ghost-button"
                type="button"
                disabled={Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                on:click={() => void handleModeration('module', module.id, 'reject')}
              >
                Reject
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </ModerationOverlay>

  <ModerationOverlay
    open={openOverlay === 'questions'}
    eyebrow="Moderation"
    title="Pending uploaded questions"
    titleId="pending-questions-title"
    copy="Bulk actions work per module table. Select rows to narrow the batch; request changes stays available per row."
    onClose={closeModerationOverlay}
  >
    {#if bulkStatusMessage}
      <div class={`banner ${bulkStatusTone === 'success' ? 'success' : bulkStatusTone === 'error' ? 'error' : 'info'}`}>
        {bulkStatusMessage}
      </div>
    {/if}

    {#if groupedPendingQuestions.length === 0}
      <p class="muted-copy">No pending uploaded questions right now.</p>
    {:else}
      <div class="moderation-overlay-stack">
        {#each groupedPendingQuestions as group (group.moduleFullSlug)}
          <section class="dynamic-card moderation-question-group">
            <div class="subsection-header">
              <div>
                <strong>{group.moduleFullSlug}</strong>
                <p class="muted-copy">{group.questions.length} pending uploaded questions.</p>
              </div>
              {#if bulkBusyModuleSlug === group.moduleFullSlug}
                <span class="muted-copy">Processing selection...</span>
              {/if}
            </div>

            <div class="moderation-question-toolbar">
              <p class="muted-copy">{selectedQuestionCount(group)} selected.</p>
              <div class="drawer-actions">
                <button
                  class="primary-button"
                  type="button"
                  disabled={group.questions.length === 0 || Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                  on:click={() => void handleBulkModeration(group, 'approve')}
                >
                  Approve selected
                </button>
                <button
                  class="ghost-button"
                  type="button"
                  disabled={group.questions.length === 0 || Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                  on:click={() => void handleBulkModeration(group, 'reject')}
                >
                  Reject selected
                </button>
              </div>
            </div>

            <div class="moderation-question-table-shell">
              <table class="moderation-question-table">
                <thead>
                  <tr>
                    <th class="moderation-checkbox-column">
                      <input
                        type="checkbox"
                        aria-label={`Select all pending questions in ${group.moduleFullSlug}`}
                        checked={allQuestionsSelected(group)}
                        disabled={Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                        on:change={(event) => toggleModuleQuestionSelection(group, (event.currentTarget as HTMLInputElement).checked)}
                      />
                    </th>
                    <th>Prompt</th>
                    <th>Answers</th>
                    <th>By</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {#each group.questions as question (question.question_id)}
                    <tr>
                      <td class="moderation-checkbox-column">
                        <input
                          type="checkbox"
                          aria-label={`Select pending question ${question.prompt}`}
                          value={question.question_id}
                          disabled={Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                          bind:group={selectedQuestionIds}
                        />
                      </td>
                      <td>
                        <strong>{question.prompt}</strong>
                      </td>
                      <td>{question.accepted_answers.map((answers) => answers.join(' / ')).join(' | ')}</td>
                      <td>{question.creator_display_name ?? 'Unknown'}</td>
                      <td>
                        <div class="moderation-row-actions">
                          <button
                            class="primary-button"
                            type="button"
                            disabled={Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                            on:click={() => void handleModeration('question', question.question_id, 'approve')}
                          >
                            Approve
                          </button>
                          <button
                            class="ghost-button"
                            type="button"
                            disabled={Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                            on:click={() => void handleModeration('question', question.question_id, 'changes_requested')}
                          >
                            Request changes
                          </button>
                          <button
                            class="ghost-button"
                            type="button"
                            disabled={Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                            on:click={() => void handleModeration('question', question.question_id, 'reject')}
                          >
                            Reject
                          </button>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </section>
        {/each}
      </div>
    {/if}
  </ModerationOverlay>

  <ModerationOverlay
    open={openOverlay === 'revisions'}
    eyebrow="Moderation"
    title="Pending revisions"
    titleId="pending-revisions-title"
    copy="Revision and delete proposals still require individual review."
    onClose={closeModerationOverlay}
  >
    {#if pendingRevisions.length === 0}
      <p class="muted-copy">No pending revisions right now.</p>
    {:else}
      <div class="moderation-overlay-stack">
        {#each pendingRevisions as revision (revision.proposal_id)}
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
              <button
                class="primary-button"
                type="button"
                disabled={Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                on:click={() => void handleModeration('revision', revision.proposal_id, 'approve')}
              >
                Approve
              </button>
              <button
                class="ghost-button"
                type="button"
                disabled={Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                on:click={() => void handleModeration('revision', revision.proposal_id, 'changes_requested')}
              >
                Request changes
              </button>
              <button
                class="ghost-button"
                type="button"
                disabled={Boolean(moderationBusyKey) || Boolean(bulkBusyModuleSlug)}
                on:click={() => void handleModeration('revision', revision.proposal_id, 'reject')}
              >
                Reject
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </ModerationOverlay>
{/if}
