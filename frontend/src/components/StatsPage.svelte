<script lang="ts">
  import StatsAllQuestionsOverlay from './StatsAllQuestionsOverlay.svelte';
  import StatsQuestionTable from './StatsQuestionTable.svelte';
  import StudyBlockDetailOverlay from './StudyBlockDetailOverlay.svelte';
  import RevisionProposalCard from './RevisionProposalCard.svelte';
  import RetryEligibilityOverlay from './RetryEligibilityOverlay.svelte';
  import StageDueMatrixOverlay from './StageDueMatrixOverlay.svelte';
  import type {
    AuthActor,
    ModerationRevisionActionPayload,
    QuestionRevisionProposal,
    QuestionRow,
    StatsResponse
  } from '../lib/types';
  import { formatScore } from '../lib/stats/format';
  import {
    buildAuxiliaryStageGraph,
    buildRecoveryStageGraph,
    emptyAuxiliaryStageGraph,
    emptyRecoveryStageGraph
  } from '../lib/stats/stage-graphs';
  import { buildSessionGraph, emptySessionGraph } from '../lib/stats/session-graph';
  import {
    buildRetryEligibilityGraph,
    buildRetryEligibilityHourlyGraph,
    buildRetryEligibilityLongRangeGraph,
    emptyRetryEligibilityGraph,
    emptyRetryEligibilityHourlyGraph,
    emptyRetryEligibilityLongRangeGraph
  } from '../lib/stats/retry-graphs';
  import {
    buildFirstSeenGraph,
    buildStageDueMatrixGraph,
    emptyFirstSeenGraph,
    emptyStageDueMatrixGraph,
  } from '../lib/stats/due-graphs';
  import { buildStudyBlockGraph, emptyStudyBlockGraph } from '../lib/stats/study-block-graph';
  import {
    groupQuestionsByBucket,
    sortDefinitions,
    visibleQuestionSortDefinitions,
    type SortDirection,
    type SortKey
  } from '../lib/stats/table';

  const REVIEW_PROPOSAL_PAGE_SIZE = 12;

  export let moduleLabel = 'All Modules';
  export let stats: StatsResponse | null = null;
  export let loading = false;
  export let reviewOnly = false;
  export let errorMessage = '';
  export let currentActor: AuthActor | null = null;
  export let onToggleReviewOnly: (value: boolean) => void = () => {};
  export let onOpenCreate: () => void = () => {};
  export let onOpenEdit: (question: QuestionRow) => void = () => {};
  export let onOpenUserRevisionEditor: (proposal: QuestionRevisionProposal) => void = () => {};
  export let onOpenAdminRevisionEditor: (proposal: QuestionRevisionProposal) => void = () => {};
  export let onRevisionModeration: (proposalId: number, payload: ModerationRevisionActionPayload) => Promise<void> | void = () => {};
  export let onWithdrawRevision: (questionId: number) => Promise<void> | void = () => {};

  let sortKey: SortKey | null = null;
  let sortDirection: SortDirection = 'asc';
  let entryDetailOpen = false;
  let studyBlockDetailOpen = false;
  let retryDetailOpen = false;
  let stageDetailOpen = false;
  let activeReviewOnly = reviewOnly;
  let reviewModeTouched = false;
  let reviewModeContext = '';
  let expandedBuckets: Record<string, boolean> = {};
  let bucketResetSignature = '';
  let reviewActionBusyKey = '';
  let reviewActionError = '';
  let visibleReviewProposalCount = REVIEW_PROPOSAL_PAGE_SIZE;

  function handleSort(nextSortKey: SortKey): void {
    const definition = sortDefinitions.find((candidate) => candidate.key === nextSortKey);
    if (!definition) {
      return;
    }
    if (sortKey === nextSortKey) {
      sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    sortKey = nextSortKey;
    sortDirection = definition.defaultDirection;
  }

  function openRetryDetail(): void {
    stageDetailOpen = false;
    entryDetailOpen = false;
    studyBlockDetailOpen = false;
    retryDetailOpen = true;
  }

  function handleRetryDetailKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openRetryDetail();
    }
  }

  function openStageDetail(): void {
    retryDetailOpen = false;
    entryDetailOpen = false;
    studyBlockDetailOpen = false;
    stageDetailOpen = true;
  }

  function handleStageDetailKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openStageDetail();
    }
  }

  function openEntryDetail(): void {
    retryDetailOpen = false;
    studyBlockDetailOpen = false;
    stageDetailOpen = false;
    entryDetailOpen = true;
  }

  function handleEntryDetailKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openEntryDetail();
    }
  }

  function openStudyBlockDetail(): void {
    retryDetailOpen = false;
    stageDetailOpen = false;
    entryDetailOpen = false;
    studyBlockDetailOpen = true;
  }

  function handleStudyBlockDetailKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openStudyBlockDetail();
    }
  }

  function toggleBucket(bucketKey: string): void {
    expandedBuckets = {
      ...expandedBuckets,
      [bucketKey]: !expandedBuckets[bucketKey]
    };
  }

  function selectReviewMode(value: boolean): void {
    activeReviewOnly = value;
    reviewModeTouched = true;
    onToggleReviewOnly(value);
  }

  function showMoreReviewProposals(): void {
    visibleReviewProposalCount += REVIEW_PROPOSAL_PAGE_SIZE;
  }

  async function handleRevisionModeration(proposalId: number, payload: ModerationRevisionActionPayload): Promise<void> {
    reviewActionBusyKey = `revision:${proposalId}:${payload.action}`;
    reviewActionError = '';
    try {
      await onRevisionModeration(proposalId, payload);
    } catch (error) {
      reviewActionError = error instanceof Error ? error.message : 'Unable to update this revision proposal.';
    } finally {
      reviewActionBusyKey = '';
    }
  }

  async function handleWithdrawRevision(questionId: number, proposalId: number): Promise<void> {
    reviewActionBusyKey = `revision:${proposalId}:withdraw`;
    reviewActionError = '';
    try {
      await onWithdrawRevision(questionId);
    } catch (error) {
      reviewActionError = error instanceof Error ? error.message : 'Unable to remove this review item.';
    } finally {
      reviewActionBusyKey = '';
    }
  }

  $: displayedQuestions = stats
    ? stats.questions.filter((question) =>
        activeReviewOnly ? false : question.schedule.logical_bucket !== 'review'
      )
    : [];
  $: bucketGroups = groupQuestionsByBucket(displayedQuestions).filter((group) =>
    activeReviewOnly ? group.key === 'review' : group.key !== 'review'
  );
  $: revisionProposals = stats?.revision_proposals ?? [];
  $: visibleReviewProposals = revisionProposals.slice(0, visibleReviewProposalCount);
  $: hiddenReviewProposalCount = Math.max(0, revisionProposals.length - visibleReviewProposals.length);
  $: emptyMessage = activeReviewOnly ? 'No review proposals in this scope.' : 'No non-review questions in this scope.';
  $: isAdmin = currentActor?.role === 'admin';
  $: sessionGraph = stats ? buildSessionGraph(stats.recent_sessions) : emptySessionGraph;
  $: studyBlockGraph = stats ? buildStudyBlockGraph(stats.study_blocks) : emptyStudyBlockGraph;
  $: recoveryStageGraph = stats ? buildRecoveryStageGraph(stats.questions) : emptyRecoveryStageGraph;
  $: auxiliaryStageGraph = stats ? buildAuxiliaryStageGraph(stats.questions, revisionProposals.length) : emptyAuxiliaryStageGraph;
  $: retryEligibilityGraph = stats
    ? buildRetryEligibilityGraph(stats.questions, new Date(), stats.schedule_timezone)
    : emptyRetryEligibilityGraph;
  $: retryEligibilityHourlyGraph = stats
    ? buildRetryEligibilityHourlyGraph(stats.questions, new Date(), stats.schedule_timezone)
    : emptyRetryEligibilityHourlyGraph;
  $: retryEligibilityLongRangeGraph = stats
    ? buildRetryEligibilityLongRangeGraph(stats.questions, new Date(), stats.schedule_timezone)
    : emptyRetryEligibilityLongRangeGraph;
  $: firstSeenGraph = stats ? buildFirstSeenGraph(stats.questions, new Date(), stats.schedule_timezone) : emptyFirstSeenGraph;
  $: stageDueMatrixGraph = stats
    ? buildStageDueMatrixGraph(stats.questions, new Date(), stats.schedule_timezone)
    : emptyStageDueMatrixGraph;
  $: if (!stats) {
    entryDetailOpen = false;
    studyBlockDetailOpen = false;
    retryDetailOpen = false;
    stageDetailOpen = false;
  }
  $: {
    const nextReviewModeContext = moduleLabel;
    if (nextReviewModeContext !== reviewModeContext) {
      reviewModeContext = nextReviewModeContext;
      reviewModeTouched = false;
      activeReviewOnly = reviewOnly;
    }
  }
  $: if (!reviewModeTouched && activeReviewOnly !== reviewOnly) {
    activeReviewOnly = reviewOnly;
  }
  $: {
    const nextBucketResetSignature = stats ? `${moduleLabel}:${activeReviewOnly}` : '';
    if (nextBucketResetSignature !== bucketResetSignature) {
      bucketResetSignature = nextBucketResetSignature;
      expandedBuckets = {};
      visibleReviewProposalCount = REVIEW_PROPOSAL_PAGE_SIZE;
    }
  }
  $: if (visibleReviewProposalCount > REVIEW_PROPOSAL_PAGE_SIZE && visibleReviewProposalCount > revisionProposals.length) {
    visibleReviewProposalCount = Math.max(REVIEW_PROPOSAL_PAGE_SIZE, revisionProposals.length);
  }
</script>

<section class="page stats-page">
  <div class="page-intro">
    <div>
      <h2>{moduleLabel}</h2>
    </div>
    <div class="stats-page-actions">
      <div class="stats-view-toggle" role="group" aria-label="Stats question view">
        <button
          type="button"
          class:active={!activeReviewOnly}
          aria-pressed={!activeReviewOnly}
          on:click={() => selectReviewMode(false)}
        >
          Questions
        </button>
        <button
          type="button"
          class:active={activeReviewOnly}
          aria-pressed={activeReviewOnly}
          on:click={() => selectReviewMode(true)}
        >
          Review
        </button>
      </div>
    </div>
  </div>

  {#if errorMessage}
    <div class="banner error">{errorMessage}</div>
  {/if}

  {#if loading && !stats}
    <div class="panel empty-state">
      <h3>Loading stats...</h3>
    </div>
  {:else if stats}
    <div class="stats-grid">
      <article class="panel stat-card">
        <h3>{stats.summary.total_questions}</h3>
        <p>{stats.summary.reviewed_questions} pending review proposals.</p>
      </article>
      <article class="panel stat-card">
        <h3>{stats.summary.total_attempts}</h3>
        <p>{formatScore(stats.summary.total_correct)}/{formatScore(stats.summary.total_possible)} points earned.</p>
      </article>
      <article class="panel stat-card">
        <h3>{Math.round(stats.summary.accuracy * 100)}%</h3>
        <p>Across the selected module scope.</p>
      </article>
    </div>

    <div class="stats-chart-grid">
      <div class="panel stats-chart-panel stats-chart-panel-performance">
        <div class="panel-header">
          <div><h3>Latest quiz performance</h3></div>
        </div>
        {#if stats.recent_sessions.length === 0}
          <p class="muted-copy">No completed sessions yet for this scope.</p>
        {:else}
          <div class="session-graph-shell">
            <svg
              class="session-graph"
              viewBox={`0 0 ${sessionGraph.chartWidth} ${sessionGraph.chartHeight}`}
              role="img"
              aria-label="Recent session accuracy graph"
            >
              <line
                x1={sessionGraph.plotLeft}
                y1={sessionGraph.averageY}
                x2={sessionGraph.plotRight}
                y2={sessionGraph.averageY}
                class="graph-average-line"
              >
                <title>{Math.round(sessionGraph.averageAccuracy * 100)}%</title>
              </line>
              <line
                x1={sessionGraph.plotLeft}
                y1={sessionGraph.axisY}
                x2={sessionGraph.plotRight}
                y2={sessionGraph.axisY}
                class="graph-axis"
              />
              {#each sessionGraph.bars as bar}
                <g class="session-bar">
                  <title>Session #{bar.sessionId}: {bar.scoreLabel}, {bar.accuracyPercent}% accuracy</title>
                  <rect
                    x={bar.x}
                    y={bar.y}
                    width={bar.width}
                    height={bar.height}
                    rx="10"
                    ry="10"
                    fill={bar.fillColor}
                  />
                  <text x={bar.labelX} y={sessionGraph.chartHeight - 18} text-anchor="middle">{bar.scoreLabel}</text>
                </g>
              {/each}
            </svg>
          </div>
        {/if}
      </div>

      <div
        class="panel stats-chart-panel stats-chart-panel-study-blocks graph-launch-panel"
        role="button"
        tabindex="0"
        aria-haspopup="dialog"
        aria-label="Open study block details"
        on:click={openStudyBlockDetail}
        on:keydown={handleStudyBlockDetailKeydown}
      >
        <div class="panel-header">
          <div><h3>Questions per study block</h3></div>
        </div>
        {#if stats.study_blocks.length === 0}
          <p class="muted-copy">No study blocks yet for this scope.</p>
        {:else}
          <div class="session-graph-shell">
            <svg
              class="session-graph"
              viewBox={`0 0 ${studyBlockGraph.chartWidth} ${studyBlockGraph.chartHeight}`}
              role="img"
              aria-label="Questions per study block"
            >
              <line
                x1={studyBlockGraph.plotLeft}
                y1={studyBlockGraph.axisY}
                x2={studyBlockGraph.plotRight}
                y2={studyBlockGraph.axisY}
                class="graph-axis"
              />
              {#each studyBlockGraph.bars as bar}
                <g class="session-bar">
                  <title>{bar.title}</title>
                  <rect
                    x={bar.x}
                    y={bar.y}
                    width={bar.width}
                    height={bar.height}
                    rx="10"
                    ry="10"
                    fill="hsl(188, 76%, 56%)"
                  />
                  <text x={bar.labelX} y={bar.y - 8} text-anchor="middle" class="stage-count-label">
                    {bar.answeredCount}
                  </text>
                  <text x={bar.labelX} y={studyBlockGraph.chartHeight - 18} text-anchor="middle">{bar.dayLabel}</text>
                </g>
              {/each}
            </svg>
          </div>
        {/if}
      </div>

      <div
        class="panel stats-chart-panel stats-chart-panel-entry graph-launch-panel"
        role="button"
        tabindex="0"
        aria-haspopup="dialog"
        aria-label="Open all questions"
        on:click={openEntryDetail}
        on:keydown={handleEntryDetailKeydown}
      >
        <div class="panel-header">
          <div><h3>Entry states</h3></div>
        </div>
        <div class="session-graph-shell">
          <svg
            class="session-graph"
            viewBox={`0 0 ${auxiliaryStageGraph.chartWidth} ${auxiliaryStageGraph.chartHeight}`}
            role="img"
            aria-label="Entry state counts"
          >
            <line
              x1={auxiliaryStageGraph.plotLeft}
              y1={auxiliaryStageGraph.axisY}
              x2={auxiliaryStageGraph.plotRight}
              y2={auxiliaryStageGraph.axisY}
              class="graph-axis"
            />
            {#each auxiliaryStageGraph.stages as stage}
              <g class="session-bar">
                <title>{stage.label}: {stage.count} questions</title>
                <rect
                  x={stage.x}
                  y={stage.y}
                  width={stage.width}
                  height={stage.height}
                  rx="10"
                  ry="10"
                  fill={stage.fillColor}
                />
                <text x={stage.labelX} y={stage.y - 8} text-anchor="middle" class="stage-count-label">
                  {stage.count}
                </text>
                <text x={stage.labelX} y={auxiliaryStageGraph.chartHeight - 18} text-anchor="middle">{stage.label}</text>
              </g>
            {/each}
          </svg>
        </div>
      </div>

      <div
        class="panel stats-chart-panel stats-chart-panel-stages graph-launch-panel"
        role="button"
        tabindex="0"
        aria-haspopup="dialog"
        aria-label="Open spaced repetition stage details"
        on:click={openStageDetail}
        on:keydown={handleStageDetailKeydown}
      >
        <div class="panel-header">
          <div><h3>Spaced repetition stages</h3></div>
        </div>
        <div class="session-graph-shell">
          <svg
            class="session-graph"
            viewBox={`0 0 ${recoveryStageGraph.chartWidth} ${recoveryStageGraph.chartHeight}`}
            role="img"
            aria-label="Spaced repetition stage counts"
          >
            <line
              x1={recoveryStageGraph.plotLeft}
              y1={recoveryStageGraph.axisY}
              x2={recoveryStageGraph.plotRight}
              y2={recoveryStageGraph.axisY}
              class="graph-axis"
            />
            {#each recoveryStageGraph.stages as stage}
              <g class="session-bar">
                <title>{stage.label}: {stage.count} questions, {stage.coolingCount} pending cooldown</title>
                <clipPath id={`recovery-stage-clip-${stage.key}`}>
                  <rect
                    x={stage.x}
                    y={stage.y}
                    width={stage.width}
                    height={stage.height}
                    rx="10"
                    ry="10"
                  />
                </clipPath>
                <rect
                  x={stage.x}
                  y={stage.y}
                  width={stage.width}
                  height={stage.height}
                  rx="10"
                  ry="10"
                  fill={stage.fillColor}
                />
                {#if stage.coolingHeight > 0}
                  <rect
                    x={stage.x}
                    y={stage.coolingY}
                    width={stage.width}
                    height={stage.coolingHeight}
                    class="graph-cooling-shade"
                    clip-path={`url(#recovery-stage-clip-${stage.key})`}
                  />
                {/if}
                <text x={stage.labelX} y={stage.y - 8} text-anchor="middle" class="stage-count-label">
                  {stage.count}
                </text>
                <text x={stage.labelX} y={recoveryStageGraph.chartHeight - 18} text-anchor="middle">{stage.label}</text>
              </g>
            {/each}
          </svg>
        </div>
      </div>

      <div
        class="panel stats-chart-panel stats-chart-panel-retry graph-launch-panel"
        role="button"
        tabindex="0"
        aria-haspopup="dialog"
        aria-label="Open retry eligibility details"
        on:click={openRetryDetail}
        on:keydown={handleRetryDetailKeydown}
      >
        <div class="panel-header">
          <div><h3>Retry eligibility</h3></div>
        </div>
        <div class="session-graph-shell">
          <svg
            class="session-graph"
            viewBox={`0 0 ${retryEligibilityGraph.chartWidth} ${retryEligibilityGraph.chartHeight}`}
            role="img"
            aria-label="Retry eligibility by day"
          >
            <line
              x1={retryEligibilityGraph.plotLeft}
              y1={retryEligibilityGraph.axisY}
              x2={retryEligibilityGraph.plotRight}
              y2={retryEligibilityGraph.axisY}
              class="graph-axis"
            />
            {#each retryEligibilityGraph.days as day}
              <g class="session-bar">
                <title>{day.label}: {day.count} questions</title>
                <rect
                  x={day.x}
                  y={day.y}
                  width={day.width}
                  height={day.height}
                  rx="10"
                  ry="10"
                  fill={day.fillColor}
                />
                <text x={day.labelX} y={day.y - 8} text-anchor="middle" class="stage-count-label">
                  {day.count}
                </text>
                <text x={day.labelX} y={retryEligibilityGraph.chartHeight - 18} text-anchor="middle">{day.label}</text>
              </g>
            {/each}
          </svg>
        </div>
      </div>

      <div class="panel stats-chart-panel stats-chart-panel-first-seen">
        <div class="panel-header">
          <div><h3>First-time questions answered</h3></div>
        </div>
        <div class="session-graph-shell">
          <svg
            class="session-graph"
            viewBox={`0 0 ${firstSeenGraph.chartWidth} ${firstSeenGraph.chartHeight}`}
            role="img"
            aria-label="First-time questions answered by day"
          >
            <line
              x1={firstSeenGraph.plotLeft}
              y1={firstSeenGraph.axisY}
              x2={firstSeenGraph.plotRight}
              y2={firstSeenGraph.axisY}
              class="graph-axis"
            />
            {#each firstSeenGraph.days as day}
              <g class="session-bar">
                <title>{day.fullLabel}: {day.count} questions first answered</title>
                <rect
                  x={day.x}
                  y={day.y}
                  width={day.width}
                  height={day.height}
                  rx="10"
                  ry="10"
                  fill={day.fillColor}
                />
                <text x={day.labelX} y={day.y - 8} text-anchor="middle" class="stage-count-label">
                  {day.count}
                </text>
                <text x={day.labelX} y={firstSeenGraph.chartHeight - 18} text-anchor="middle">{day.label}</text>
              </g>
            {/each}
          </svg>
        </div>
      </div>
    </div>

    <div class="question-bucket-stack stats-question-buckets">
      {#if reviewActionError}
        <div class="banner error">{reviewActionError}</div>
      {/if}

      {#if activeReviewOnly}
        <section class="question-bucket-card">
          <div class="question-bucket-toggle question-bucket-toggle-static">
            <span class="question-bucket-title">Review</span>
            <span class="question-bucket-count">{revisionProposals.length}</span>
          </div>

          {#if revisionProposals.length === 0}
            <p class="muted-copy question-bucket-empty">No review proposals in this scope.</p>
          {:else}
            <div class="revision-proposal-stack">
              {#each visibleReviewProposals as proposal (proposal.proposal_id)}
                <RevisionProposalCard
                  {proposal}
                  {isAdmin}
                  busyKey={reviewActionBusyKey}
                  onOpenEditor={isAdmin ? onOpenAdminRevisionEditor : onOpenUserRevisionEditor}
                  onWithdraw={(questionId) => handleWithdrawRevision(questionId, proposal.proposal_id)}
                  onModeration={handleRevisionModeration}
                />
              {/each}
            </div>
            {#if hiddenReviewProposalCount > 0}
              <div class="review-proposal-pagination">
                <span class="muted-copy">
                  Showing {visibleReviewProposals.length} of {revisionProposals.length}
                </span>
                <button class="ghost-button" type="button" on:click={showMoreReviewProposals}>
                  Show {Math.min(REVIEW_PROPOSAL_PAGE_SIZE, hiddenReviewProposalCount)} more
                </button>
              </div>
            {/if}
          {/if}
        </section>
      {:else}
        {#if displayedQuestions.length === 0}
          <p class="muted-copy question-bucket-summary-empty">{emptyMessage}</p>
        {/if}
        {#each bucketGroups as group (group.key)}
          <section class="question-bucket-card">
            <button
              class="question-bucket-toggle"
              type="button"
              aria-expanded={expandedBuckets[group.key] ?? false}
              on:click={() => toggleBucket(group.key)}
            >
              <span class="question-bucket-title">{group.label}</span>
              <span class="question-bucket-count">{group.questions.length}</span>
              <span
                class="question-bucket-caret"
                class:expanded={expandedBuckets[group.key] ?? false}
                aria-hidden="true"
              ></span>
            </button>

            {#if expandedBuckets[group.key]}
              {#if group.questions.length === 0}
                <p class="muted-copy question-bucket-empty">No questions in this bucket.</p>
              {:else}
                <StatsQuestionTable
                  questions={group.questions}
                  definitions={visibleQuestionSortDefinitions}
                  sortKey={sortKey}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  onOpenEdit={onOpenEdit}
                />
              {/if}
            {/if}
          </section>
        {/each}
      {/if}
    </div>
  {:else}
    <div class="panel empty-state">
      <h3>No stats to show yet.</h3>
      <p>Create seed data or finish a quiz to populate this view.</p>
    </div>
  {/if}

  <button class="floating-action" type="button" aria-label="Create question" on:click={onOpenCreate}>+</button>
</section>

<StageDueMatrixOverlay
  open={stageDetailOpen}
  graph={stageDueMatrixGraph}
  onClose={() => (stageDetailOpen = false)}
/>
<StatsAllQuestionsOverlay
  open={entryDetailOpen}
  questions={displayedQuestions}
  emptyMessage={emptyMessage}
  sortKey={sortKey}
  sortDirection={sortDirection}
  onSort={handleSort}
  onOpenEdit={onOpenEdit}
  onClose={() => (entryDetailOpen = false)}
/>
<StudyBlockDetailOverlay
  open={studyBlockDetailOpen}
  studyBlocks={stats?.study_blocks ?? []}
  onClose={() => (studyBlockDetailOpen = false)}
/>
<RetryEligibilityOverlay
  open={retryDetailOpen}
  hourlyGraph={retryEligibilityHourlyGraph}
  longRangeGraph={retryEligibilityLongRangeGraph}
  onClose={() => (retryDetailOpen = false)}
/>
