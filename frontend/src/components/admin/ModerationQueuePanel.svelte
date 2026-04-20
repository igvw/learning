<script lang="ts">
  import {
    groupPendingQuestionsByModule,
    groupPendingRevisionsByModule,
    reviewBadge,
    revisionSectionsForModule
  } from '../../lib/admin-page';
  import type {
    PendingQuestionGroup,
    PendingRevisionModuleGroup,
    PendingRevisionPrimaryKind,
    PendingRevisionSection
  } from '../../lib/admin-page';
  import type {
    BulkRevisionModerationItem,
    BulkModerationResult,
    ModerationActionPayload,
    ModerationKind,
    ModerationQueue,
    ModerationRevisionActionPayload,
    QuestionRevisionProposal
  } from '../../lib/types';
  import ModerationOverlay from './ModerationOverlay.svelte';
  import RevisionSnapshot from './RevisionSnapshot.svelte';

  type ModerationOverlayKind = 'modules' | 'questions' | 'revisions' | null;
  type StatusTone = 'success' | 'error' | 'info';

  export let moderationQueue: ModerationQueue | null = null;
  export let onModerationAction: (
    kind: ModerationKind,
    id: number,
    payload: ModerationRevisionActionPayload
  ) => Promise<void> = async () => {
    throw new Error('Moderation handler is not configured.');
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

  let moderationBusyKey = '';
  let openOverlay: ModerationOverlayKind = null;

  let selectedQuestionIds: number[] = [];
  let questionBulkBusyKey = '';
  let questionBulkStatusMessage = '';
  let questionBulkStatusTone: StatusTone = 'info';

  let selectedRevisionModuleSlug = '';
  let expandedRevisionSections: PendingRevisionPrimaryKind[] = [];
  let selectedRevisionProposalIds: number[] = [];
  let revisionResetStates: Record<number, boolean> = {};
  let revisionBulkBusyKey = '';
  let revisionBulkStatusMessage = '';
  let revisionBulkStatusTone: StatusTone = 'info';

  $: pendingModules = moderationQueue?.pending_modules ?? [];
  $: pendingQuestions = moderationQueue?.pending_questions ?? [];
  $: pendingRevisions = moderationQueue?.pending_revisions ?? [];
  $: groupedPendingQuestions = groupPendingQuestionsByModule(pendingQuestions);
  $: groupedPendingRevisions = groupPendingRevisionsByModule(pendingRevisions);
  $: totalPendingCount = pendingModules.length + pendingQuestions.length + pendingRevisions.length;
  $: moderationLocked = Boolean(moderationBusyKey) || Boolean(questionBulkBusyKey) || Boolean(revisionBulkBusyKey);
  $: visibleQuestionIds = new Set(pendingQuestions.map((question) => question.question_id));
  $: if (selectedQuestionIds.some((questionId) => !visibleQuestionIds.has(questionId))) {
    selectedQuestionIds = selectedQuestionIds.filter((questionId) => visibleQuestionIds.has(questionId));
  }
  $: if (
    selectedRevisionModuleSlug &&
    !groupedPendingRevisions.some((group) => group.moduleFullSlug === selectedRevisionModuleSlug)
  ) {
    selectedRevisionModuleSlug = '';
    expandedRevisionSections = [];
    selectedRevisionProposalIds = [];
  }
  $: selectedRevisionGroup =
    groupedPendingRevisions.find((group) => group.moduleFullSlug === selectedRevisionModuleSlug) ?? null;
  $: revisionSections = selectedRevisionGroup ? revisionSectionsForModule(selectedRevisionGroup) : [];
  $: visibleRevisionIds = new Set(
    (selectedRevisionGroup?.revisions ?? []).map((entry) => entry.proposal.proposal_id)
  );
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

  function resetQuestionOverlayState(): void {
    selectedQuestionIds = [];
    questionBulkBusyKey = '';
    questionBulkStatusMessage = '';
    questionBulkStatusTone = 'info';
  }

  function resetRevisionOverlayState(): void {
    selectedRevisionModuleSlug = '';
    expandedRevisionSections = [];
    selectedRevisionProposalIds = [];
    revisionResetStates = {};
    revisionBulkBusyKey = '';
    revisionBulkStatusMessage = '';
    revisionBulkStatusTone = 'info';
  }

  function openModerationOverlay(kind: Exclude<ModerationOverlayKind, null>): void {
    if (kind === 'questions') {
      resetQuestionOverlayState();
    }
    if (kind === 'revisions') {
      resetRevisionOverlayState();
    }
    openOverlay = kind;
  }

  function closeModerationOverlay(): void {
    openOverlay = null;
    moderationBusyKey = '';
    resetQuestionOverlayState();
    resetRevisionOverlayState();
  }

  function toggleModuleQuestionSelection(group: PendingQuestionGroup, selected: boolean): void {
    const groupQuestionIds = group.questions.map((question) => question.question_id);
    if (selected) {
      selectedQuestionIds = [...new Set([...selectedQuestionIds, ...groupQuestionIds])];
      return;
    }
    selectedQuestionIds = selectedQuestionIds.filter((questionId) => !groupQuestionIds.includes(questionId));
  }

  function openRevisionModule(group: PendingRevisionModuleGroup): void {
    selectedRevisionModuleSlug = group.moduleFullSlug;
    expandedRevisionSections = [];
    selectedRevisionProposalIds = [];
    revisionBulkBusyKey = '';
    revisionBulkStatusMessage = '';
    revisionBulkStatusTone = 'info';
  }

  function closeRevisionModule(): void {
    selectedRevisionModuleSlug = '';
    expandedRevisionSections = [];
    selectedRevisionProposalIds = [];
    revisionBulkBusyKey = '';
    revisionBulkStatusMessage = '';
    revisionBulkStatusTone = 'info';
  }

  function setRevisionSectionExpanded(sectionKey: PendingRevisionPrimaryKind, expanded: boolean): void {
    if (expanded) {
      if (!expandedRevisionSections.includes(sectionKey)) {
        expandedRevisionSections = [...expandedRevisionSections, sectionKey];
      }
      return;
    }
    expandedRevisionSections = expandedRevisionSections.filter((key) => key !== sectionKey);
  }

  function toggleRevisionSelection(section: PendingRevisionSection, selected: boolean): void {
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

  async function handleModeration(
    kind: ModerationKind,
    id: number,
    action: ModerationActionPayload['action']
  ): Promise<void> {
    moderationBusyKey = `${kind}:${id}:${action}`;
    questionBulkStatusMessage = '';
    revisionBulkStatusMessage = '';
    try {
      await onModerationAction(kind, id, { action, note: '' });
    } finally {
      moderationBusyKey = '';
    }
  }

  async function handleRevisionModeration(
    proposalId: number,
    action: ModerationActionPayload['action']
  ): Promise<void> {
    moderationBusyKey = `revision:${proposalId}:${action}`;
    questionBulkStatusMessage = '';
    revisionBulkStatusMessage = '';
    try {
      await onModerationAction('revision', proposalId, {
        action,
        note: '',
        ...(action === 'approve' ? { reset_stats: revisionResetState(proposalId) } : {})
      });
    } finally {
      moderationBusyKey = '';
    }
  }

  async function handleBulkQuestionModeration(
    group: PendingQuestionGroup,
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

    questionBulkBusyKey = group.moduleFullSlug;
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
      questionBulkBusyKey = '';
    }
  }

  async function handleBulkRevisionModeration(
    section: PendingRevisionSection,
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

    revisionBulkBusyKey = section.key;
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
      revisionBulkBusyKey = '';
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
        <strong>Modules</strong>
        <span class="moderation-summary-count">{pendingModules.length}</span>
      </button>

      <button
        type="button"
        class="dynamic-card moderation-summary-card"
        aria-haspopup="dialog"
        on:click={() => openModerationOverlay('questions')}
      >
        <strong>Uploads</strong>
        <span class="moderation-summary-count">{pendingQuestions.length}</span>
      </button>

      <button
        type="button"
        class="dynamic-card moderation-summary-card"
        aria-haspopup="dialog"
        on:click={() => openModerationOverlay('revisions')}
      >
        <strong>Revisions</strong>
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
                disabled={moderationLocked}
                on:click={() => void handleModeration('module', module.id, 'approve')}
              >
                Approve
              </button>
              <button
                class="ghost-button"
                type="button"
                disabled={moderationLocked}
                on:click={() => void handleModeration('module', module.id, 'changes_requested')}
              >
                Request changes
              </button>
              <button
                class="ghost-button"
                type="button"
                disabled={moderationLocked}
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
    {#if questionBulkStatusMessage}
      <div
        class={`banner ${questionBulkStatusTone === 'success' ? 'success' : questionBulkStatusTone === 'error' ? 'error' : 'info'}`}
      >
        {questionBulkStatusMessage}
      </div>
    {/if}

    {#if groupedPendingQuestions.length === 0}
      <p class="muted-copy">No pending uploaded questions right now.</p>
    {:else}
      <div class="moderation-overlay-stack">
        {#each groupedPendingQuestions as group (group.moduleFullSlug)}
          {@const allQuestionsInGroupSelected =
            group.questions.length > 0 && group.questions.every((question) => selectedQuestionIds.includes(question.question_id))}
          {@const selectedQuestionsInGroup =
            group.questions.filter((question) => selectedQuestionIds.includes(question.question_id)).length}
          <section class="dynamic-card moderation-question-group">
            <div class="subsection-header">
              <div>
                <strong>{group.moduleFullSlug}</strong>
                <p class="muted-copy">{group.questions.length} pending uploaded questions.</p>
              </div>
              {#if questionBulkBusyKey === group.moduleFullSlug}
                <span class="muted-copy">Processing selection...</span>
              {/if}
            </div>

            <div class="moderation-question-toolbar">
              <p class="muted-copy">{selectedQuestionsInGroup} selected.</p>
              <div class="drawer-actions">
                <button
                  class="primary-button"
                  type="button"
                  disabled={group.questions.length === 0 || moderationLocked}
                  on:click={() => void handleBulkQuestionModeration(group, 'approve')}
                >
                  Approve selected
                </button>
                <button
                  class="ghost-button"
                  type="button"
                  disabled={group.questions.length === 0 || moderationLocked}
                  on:click={() => void handleBulkQuestionModeration(group, 'reject')}
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
                            on:click={() => void handleModeration('question', question.question_id, 'approve')}
                          >
                            Approve
                          </button>
                          <button
                            class="ghost-button"
                            type="button"
                            disabled={moderationLocked}
                            on:click={() => void handleModeration('question', question.question_id, 'changes_requested')}
                          >
                            Request changes
                          </button>
                          <button
                            class="ghost-button"
                            type="button"
                            disabled={moderationLocked}
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
    copy={
      selectedRevisionGroup
        ? 'Open a change section to review that batch. Click any snapshot card to edit and approve it in the drawer.'
        : 'Choose a module to review its pending revisions.'
    }
    onClose={closeModerationOverlay}
  >
    {#if revisionBulkStatusMessage}
      <div
        class={`banner ${revisionBulkStatusTone === 'success' ? 'success' : revisionBulkStatusTone === 'error' ? 'error' : 'info'}`}
      >
        {revisionBulkStatusMessage}
      </div>
    {/if}

    {#if groupedPendingRevisions.length === 0}
      <p class="muted-copy">No pending revisions right now.</p>
    {:else if !selectedRevisionGroup}
      <div class="moderation-summary-grid revision-module-grid">
        {#each groupedPendingRevisions as group (group.moduleFullSlug)}
          <button
            type="button"
            class="dynamic-card moderation-summary-card revision-module-card"
            aria-label={`Open pending revisions for ${group.moduleFullSlug}`}
            on:click={() => openRevisionModule(group)}
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
          {@const sectionExpanded = expandedRevisionSections.includes(section.key)}
          {@const allRevisionsInSectionSelected =
            section.revisions.length > 0 &&
            section.revisions.every((entry) => selectedRevisionProposalIds.includes(entry.proposal.proposal_id))}
          {@const selectedRevisionsInSection =
            section.revisions.filter((entry) => selectedRevisionProposalIds.includes(entry.proposal.proposal_id)).length}
          <section class="dynamic-card moderation-revision-section">
            <button
              type="button"
              class="moderation-section-toggle"
              aria-expanded={sectionExpanded}
              on:click={() => setRevisionSectionExpanded(section.key, !sectionExpanded)}
            >
              <div>
                <strong>{section.title}</strong>
                <p class="muted-copy">{section.revisions.length} proposals.</p>
              </div>
              <span class="moderation-summary-count">{section.revisions.length}</span>
            </button>

            {#if sectionExpanded}
              <div class="moderation-question-toolbar">
                <p class="muted-copy">{selectedRevisionsInSection} selected.</p>
                <div class="drawer-actions">
                  <button
                    class="primary-button"
                    type="button"
                    disabled={section.revisions.length === 0 || moderationLocked}
                    on:click={() => void handleBulkRevisionModeration(section, 'approve')}
                  >
                    Approve selected
                  </button>
                  <button
                    class="ghost-button"
                    type="button"
                    disabled={section.revisions.length === 0 || moderationLocked}
                    on:click={() => void handleBulkRevisionModeration(section, 'reject')}
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
                          on:change={(event) => toggleRevisionSelection(section, (event.currentTarget as HTMLInputElement).checked)}
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
                              on:click={() => void handleModeration('revision', revision.proposal_id, 'reject')}
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
        {/each}
      </div>
    {/if}
  </ModerationOverlay>
{/if}
