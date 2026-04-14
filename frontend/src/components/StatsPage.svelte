<script lang="ts">
  import type { QuestionRow, StatsResponse } from '../lib/types';
  import {
    buildAuxiliaryStageGraph,
    buildFirstSeenGraph,
    buildRecoveryStageGraph,
    buildRetryEligibilityGraph,
    buildSessionGraph,
    emptyAuxiliaryStageGraph,
    emptyFirstSeenGraph,
    emptyRecoveryStageGraph,
    emptyRetryEligibilityGraph,
    emptySessionGraph,
    formatBucketLabel,
    formatLastSeen,
    formatScore,
    sortDefinitions,
    sortQuestions,
    type SortDirection,
    type SortKey
  } from '../lib/stats-page';

  export let moduleLabel = 'All Modules';
  export let activeUserLabel = 'Current User';
  export let stats: StatsResponse | null = null;
  export let loading = false;
  export let reviewOnly = false;
  export let errorMessage = '';
  export let onToggleReviewOnly: (value: boolean) => void = () => {};
  export let onOpenCreate: () => void = () => {};
  export let onOpenEdit: (question: QuestionRow) => void = () => {};

  let sortKey: SortKey | null = null;
  let sortDirection: SortDirection = 'asc';

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

  function sortIndicator(candidateKey: SortKey): string {
    if (sortKey !== candidateKey) {
      return '';
    }
    return sortDirection === 'asc' ? ' ↑' : ' ↓';
  }

  $: mainQuestions = stats ? stats.questions.filter((question) => !question.review_flag) : [];
  $: reviewQuestions = stats ? stats.questions.filter((question) => question.review_flag) : [];
  $: displayedQuestions = reviewOnly ? reviewQuestions : mainQuestions;
  $: sortedDisplayedQuestions = sortQuestions(displayedQuestions, sortKey, sortDirection);
  $: emptyMessage = reviewOnly ? 'No review questions in this scope.' : 'No non-review questions in this scope.';
  $: sessionGraph = stats ? buildSessionGraph(stats.recent_sessions) : emptySessionGraph;
  $: recoveryStageGraph = stats ? buildRecoveryStageGraph(stats.questions) : emptyRecoveryStageGraph;
  $: auxiliaryStageGraph = stats ? buildAuxiliaryStageGraph(stats.questions) : emptyAuxiliaryStageGraph;
  $: retryEligibilityGraph = stats ? buildRetryEligibilityGraph(stats.questions) : emptyRetryEligibilityGraph;
  $: firstSeenGraph = stats ? buildFirstSeenGraph(stats.questions) : emptyFirstSeenGraph;
</script>

<section class="page stats-page">
  <div class="page-intro">
    <div>
      <p class="eyebrow">Stats scope</p>
      <h2>{moduleLabel}</h2>
      <p class="muted-copy">Progress for {activeUserLabel}.</p>
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
        <p class="eyebrow">Question bank</p>
        <h3>{stats.summary.total_questions}</h3>
        <p>{stats.summary.reviewed_questions} flagged for review by this user.</p>
      </article>
      <article class="panel stat-card">
        <p class="eyebrow">Attempts</p>
        <h3>{stats.summary.total_attempts}</h3>
        <p>{formatScore(stats.summary.total_correct)}/{formatScore(stats.summary.total_possible)} points earned.</p>
      </article>
      <article class="panel stat-card">
        <p class="eyebrow">Accuracy</p>
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

      <div class="panel stats-chart-panel stats-chart-panel-entry">
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

      <div class="panel stats-chart-panel stats-chart-panel-stages">
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

      <div class="panel stats-chart-panel stats-chart-panel-retry">
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

    <div class="panel table-panel">
      <div class="panel-header">
        <div>
          <h3>Questions</h3>
        </div>
      </div>

      {#if sortedDisplayedQuestions.length === 0}
        <p class="muted-copy">{emptyMessage}</p>
      {:else}
        <div class="table-shell">
          <table>
            <thead>
              <tr>
                {#each sortDefinitions as definition (definition.key)}
                  <th>
                    <button
                      class="table-sort-button"
                      type="button"
                      on:click={() => handleSort(definition.key)}
                    >
                      {definition.label}{sortIndicator(definition.key)}
                    </button>
                  </th>
                {/each}
              </tr>
            </thead>
            <tbody>
              {#each sortedDisplayedQuestions as question (question.question_id)}
                <tr
                  class:flagged-review={question.review_flag}
                  class:hot0-row={!question.review_flag && question.schedule.bucket === 'hot0'}
                  class:hot1-row={!question.review_flag && (question.schedule.bucket === 'hot1' || question.schedule.bucket === 'hot1_sit_out')}
                  on:click={() => onOpenEdit(question)}
                >
                  <td>{question.rank}</td>
                  <td>
                    <div class="question-cell">
                      <span>{question.prompt_preview}</span>
                    </div>
                  </td>
                  <td>{formatBucketLabel(question)}</td>
                  <td>{formatLastSeen(question.last_asked_at)}</td>
                  <td>{question.attempts}</td>
                  <td>{Math.round(question.correct_percentage * 100)}%</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
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
