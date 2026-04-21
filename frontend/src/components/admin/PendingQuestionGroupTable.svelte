<script lang="ts">
  import type { PendingQuestionGroup } from '../../lib/pending-questions';
  import type { BulkModerationResult, ModerationActionPayload } from '../../lib/types';

  type StatusTone = 'success' | 'error' | 'info';

  export let group: PendingQuestionGroup;
  export let onQuestionModeration: (questionId: number, payload: ModerationActionPayload) => Promise<void> = async () => {
    throw new Error('Question moderation handler is not configured.');
  };
  export let onBulkQuestionModeration: (
    questionIds: number[],
    payload: ModerationActionPayload
  ) => Promise<BulkModerationResult> = async () => {
    throw new Error('Bulk question moderation handler is not configured.');
  };

  let moderationBusyKey = '';
  let questionBulkBusy = false;
  let questionBulkStatusMessage = '';
  let questionBulkStatusTone: StatusTone = 'info';
  let selectedQuestionIds: number[] = [];

  $: moderationLocked = Boolean(moderationBusyKey) || questionBulkBusy;
  $: visibleQuestionIds = new Set(group.questions.map((question) => question.question_id));
  $: if (selectedQuestionIds.some((questionId) => !visibleQuestionIds.has(questionId))) {
    selectedQuestionIds = selectedQuestionIds.filter((questionId) => visibleQuestionIds.has(questionId));
  }
  $: allQuestionsInGroupSelected =
    group.questions.length > 0 && group.questions.every((question) => selectedQuestionIds.includes(question.question_id));
  $: selectedQuestionsInGroup =
    group.questions.filter((question) => selectedQuestionIds.includes(question.question_id)).length;

  function toggleModuleQuestionSelection(selected: boolean): void {
    const groupQuestionIds = group.questions.map((question) => question.question_id);
    if (selected) {
      selectedQuestionIds = [...new Set([...selectedQuestionIds, ...groupQuestionIds])];
      return;
    }
    selectedQuestionIds = selectedQuestionIds.filter((questionId) => !groupQuestionIds.includes(questionId));
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

  async function handleModeration(questionId: number, action: ModerationActionPayload['action']): Promise<void> {
    moderationBusyKey = `question:${questionId}:${action}`;
    questionBulkStatusMessage = '';
    try {
      await onQuestionModeration(questionId, { action, note: '' });
    } finally {
      moderationBusyKey = '';
    }
  }

  async function handleBulkModeration(
    action: Extract<ModerationActionPayload['action'], 'approve' | 'reject'>
  ): Promise<void> {
    const selectedQuestionIdsInGroup = group.questions
      .map((question) => question.question_id)
      .filter((questionId) => selectedQuestionIds.includes(questionId));
    const questionIds =
      selectedQuestionIdsInGroup.length > 0
        ? selectedQuestionIdsInGroup
        : group.questions.map((question) => question.question_id);
    if (questionIds.length === 0) {
      return;
    }

    questionBulkBusy = true;
    questionBulkStatusMessage = '';

    try {
      const result = await onBulkQuestionModeration(questionIds, { action, note: '' });
      const status = bulkStatus(result, action, 'question');
      questionBulkStatusTone = status.tone;
      questionBulkStatusMessage = status.message;

      if (result.failed === 0) {
        selectedQuestionIds = selectedQuestionIds.filter((questionId) => !questionIds.includes(questionId));
      }
    } finally {
      questionBulkBusy = false;
    }
  }
</script>

<section class="dynamic-card moderation-question-group">
  <div class="subsection-header">
    <div>
      <strong>{group.moduleFullSlug}</strong>
      <p class="muted-copy">{group.questions.length} pending uploaded questions.</p>
    </div>
    {#if questionBulkBusy}
      <span class="muted-copy">Processing selection...</span>
    {/if}
  </div>

  {#if questionBulkStatusMessage}
    <div
      class={`banner ${questionBulkStatusTone === 'success' ? 'success' : questionBulkStatusTone === 'error' ? 'error' : 'info'}`}
    >
      {questionBulkStatusMessage}
    </div>
  {/if}

  <div class="moderation-question-toolbar">
    <p class="muted-copy">{selectedQuestionsInGroup} selected.</p>
    <div class="drawer-actions">
      <button
        class="primary-button"
        type="button"
        disabled={group.questions.length === 0 || moderationLocked}
        on:click={() => void handleBulkModeration('approve')}
      >
        Approve selected
      </button>
      <button
        class="ghost-button"
        type="button"
        disabled={group.questions.length === 0 || moderationLocked}
        on:click={() => void handleBulkModeration('reject')}
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
              checked={allQuestionsInGroupSelected}
              disabled={moderationLocked}
              on:change={(event) => toggleModuleQuestionSelection((event.currentTarget as HTMLInputElement).checked)}
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
                disabled={moderationLocked}
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
                  disabled={moderationLocked}
                  on:click={() => void handleModeration(question.question_id, 'approve')}
                >
                  Approve
                </button>
                <button
                  class="ghost-button"
                  type="button"
                  disabled={moderationLocked}
                  on:click={() => void handleModeration(question.question_id, 'reject')}
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
