<script lang="ts">
  import StatsAllQuestionsOverlay from './StatsAllQuestionsOverlay.svelte';
  import StatsQuestionTable from './StatsQuestionTable.svelte';
  import RetryEligibilityOverlay from './RetryEligibilityOverlay.svelte';
  import StageDueMatrixOverlay from './StageDueMatrixOverlay.svelte';
  import type { QuestionRow, StatsResponse } from '../lib/types';
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
  import {
    groupQuestionsByBucket,
    sortDefinitions,
    visibleQuestionSortDefinitions,
    type SortDirection,
    type SortKey
  } from '../lib/stats/table';

  export let moduleLabel = 'All Modules';
  export let stats: StatsResponse | null = null;
  export let loading = false;
  export let reviewOnly = false;
  export let errorMessage = '';
  export let onToggleReviewOnly: (value: boolean) => void = () => {};
  export let onOpenCreate: () => void = () => {};
  export let onOpenEdit: (question: QuestionRow) => void = () => {};

  let sortKey: SortKey | null = null;
  let sortDirection: SortDirection = 'asc';
  let entryDetailOpen = false;
  let retryDetailOpen = false;
  let stageDetailOpen = false;
  let expandedBuckets: Record<string, boolean> = {};
  let bucketResetSignature = '';

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
    stageDetailOpen = false;
    entryDetailOpen = true;
  }

  function handleEntryDetailKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openEntryDetail();
    }
  }

  function toggleBucket(bucketKey: string): void {
    expandedBuckets = {
      ...expandedBuckets,
      [bucketKey]: !expandedBuckets[bucketKey]
    };
  }

  $: mainQuestions = stats ? stats.questions.filter((question) => !question.review_flag) : [];
  $: reviewQuestions = stats ? stats.questions.filter((question) => question.review_flag) : [];
  $: displayedQuestions = reviewOnly ? reviewQuestions : mainQuestions;
  $: bucketGroups = groupQuestionsByBucket(displayedQuestions);
  $: emptyMessage = reviewOnly ? 'No review questions in this scope.' : 'No non-review questions in this scope.';
  $: sessionGraph = stats ? buildSessionGraph(stats.recent_sessions) : emptySessionGraph;
  $: recoveryStageGraph = stats ? buildRecoveryStageGraph(stats.questions) : emptyRecoveryStageGraph;
  $: auxiliaryStageGraph = stats ? buildAuxiliaryStageGraph(stats.questions) : emptyAuxiliaryStageGraph;
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
    retryDetailOpen = false;
    stageDetailOpen = false;
  }
  $: {
    const nextBucketResetSignature = stats
      ? `${moduleLabel}:${reviewOnly}:${displayedQuestions.map((question) => question.question_id).join('|')}`
      : '';
    if (nextBucketResetSignature !== bucketResetSignature) {
      bucketResetSignature = nextBucketResetSignature;
      expandedBuckets = {};
    }
  }
</script>

<section class="page stats-page">
  <div class="page-intro">
    <div>
      <h2>{moduleLabel}</h2>
    </div>
    <div class="stats-page-actions">
      <label class="review-filter">
        <input
          type="checkbox"
          checked={reviewOnly}
          on:change={(event) => onToggleReviewOnly((event.currentTarget as HTMLInputElement).checked)}
        />
        Review only
      </label>
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
        <p>{stats.summary.reviewed_questions} flagged for review by this user.</p>
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
                    class="graph-cooling-overlay"
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

    <div class="panel table-panel question-bucket-panel">
      <div class="panel-header">
        <div>
          <h3>Questions</h3>
        </div>
      </div>

      {#if displayedQuestions.length === 0}
        <p class="muted-copy">{emptyMessage}</p>
      {/if}

      <div class="question-bucket-stack">
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
              <span class="question-bucket-caret" aria-hidden="true">{expandedBuckets[group.key] ? '-' : '+'}</span>
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
      </div>
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
<RetryEligibilityOverlay
  open={retryDetailOpen}
  hourlyGraph={retryEligibilityHourlyGraph}
  longRangeGraph={retryEligibilityLongRangeGraph}
  onClose={() => (retryDetailOpen = false)}
/>
