<script lang="ts">
  import type { QuestionRow, RecentSession, StatsResponse } from '../lib/types';

  type SortDirection = 'asc' | 'desc';
  type SortKey = 'prompt' | 'bucket' | 'last_seen' | 'rank' | 'attempts' | 'correct_percentage';

  type SortDefinition = {
    key: SortKey;
    label: string;
    defaultDirection: SortDirection;
  };

  const sortDefinitions: SortDefinition[] = [
    { key: 'rank', label: 'Rank', defaultDirection: 'asc' },
    { key: 'prompt', label: 'Prompt', defaultDirection: 'asc' },
    { key: 'bucket', label: 'Bucket', defaultDirection: 'asc' },
    { key: 'last_seen', label: 'Last seen', defaultDirection: 'desc' },
    { key: 'attempts', label: 'Attempts', defaultDirection: 'desc' },
    { key: 'correct_percentage', label: 'Correct', defaultDirection: 'desc' }
  ];

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
  const intervalLabels = ['1h', '3h', '6h', '12h', '1d', '3d', '7d', '14d'];

  function formatScore(value: number): string {
    return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(/\.0$/, '');
  }

  function formatScorePair(earned: number, possible: number): string {
    return `${formatScore(earned)}/${formatScore(possible)}`;
  }

  function scheduleIntervalLabel(intervalStep: number | null): string {
    if (intervalStep === null) {
      return '';
    }
    return intervalLabels[intervalStep] ?? '';
  }

  function formatBucketLabel(question: QuestionRow): string {
    switch (question.schedule.logical_bucket) {
      case 'review':
        return 'Review';
      case 'unseen':
        return 'Unseen';
      case 'mastery':
        return 'Mastery';
      default:
        return question.schedule.logical_bucket;
    }
  }

  function formatLastSeen(value: string | null): string {
    if (!value) {
      return 'Never';
    }
    return new Date(value).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

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

  function compareQuestions(left: QuestionRow, right: QuestionRow, key: SortKey): number {
    switch (key) {
      case 'prompt':
        return left.prompt_preview.localeCompare(right.prompt_preview);
      case 'bucket':
        return compareBucket(left, right);
      case 'last_seen':
        return compareLastSeen(left, right);
      case 'rank':
        return left.rank - right.rank;
      case 'attempts':
        return left.attempts - right.attempts;
      case 'correct_percentage':
        return left.correct_percentage - right.correct_percentage;
    }
  }

  function bucketSortTuple(question: QuestionRow): [number, string] {
    switch (question.schedule.logical_bucket) {
      case '1h':
        return [0, question.prompt_preview];
      case '3h':
        return [1, question.prompt_preview];
      case '6h':
        return [2, question.prompt_preview];
      case '12h':
        return [3, question.prompt_preview];
      case '1d':
        return [4, question.prompt_preview];
      case '3d':
        return [5, question.prompt_preview];
      case '7d':
        return [6, question.prompt_preview];
      case '14d':
        return [7, question.prompt_preview];
      case 'unseen':
        return [8, question.prompt_preview];
      case 'mastery':
        return [9, question.prompt_preview];
      case 'review':
        return [10, question.prompt_preview];
      default:
        return [99, question.prompt_preview];
    }
  }

  function compareBucket(left: QuestionRow, right: QuestionRow): number {
    const leftTuple = bucketSortTuple(left);
    const rightTuple = bucketSortTuple(right);
    if (leftTuple[0] !== rightTuple[0]) {
      return leftTuple[0] - rightTuple[0];
    }
    return leftTuple[1].localeCompare(rightTuple[1]);
  }

  function compareLastSeen(
    left: QuestionRow,
    right: QuestionRow,
    direction: SortDirection
  ): number {
    if (!left.last_asked_at && !right.last_asked_at) {
      return 0;
    }
    if (!left.last_asked_at) {
      return 1;
    }
    if (!right.last_asked_at) {
      return -1;
    }
    const comparison =
      new Date(left.last_asked_at).getTime() - new Date(right.last_asked_at).getTime();
    return direction === 'asc' ? comparison : -comparison;
  }

  function sortQuestions(
    questions: QuestionRow[],
    activeSortKey: SortKey | null,
    activeSortDirection: SortDirection
  ): QuestionRow[] {
    if (!activeSortKey) {
      return questions;
    }

    const directionMultiplier = activeSortDirection === 'asc' ? 1 : -1;
    return [...questions].sort((left, right) => {
      const comparison =
        activeSortKey === 'last_seen'
          ? compareLastSeen(left, right, activeSortDirection)
          : compareQuestions(left, right, activeSortKey) * directionMultiplier;
      if (comparison !== 0) {
        return comparison;
      }
      return left.question_id - right.question_id;
    });
  }

  function buildSessionGraph(recentSessions: RecentSession[]): {
    bars: Array<{
      sessionId: number;
      accuracyPercent: number;
      scoreLabel: string;
      fillColor: string;
      x: number;
      y: number;
      width: number;
      height: number;
      labelX: number;
    }>;
    averageAccuracy: number;
    averageY: number;
    axisY: number;
    chartWidth: number;
    chartHeight: number;
    plotLeft: number;
    plotRight: number;
  } {
    const orderedSessions = [...recentSessions].sort((left, right) => left.created_at.localeCompare(right.created_at));
    const chartWidth = 640;
    const chartHeight = 220;
    const padding = { top: 28, right: 28, bottom: 52, left: 28 };
    const plotWidth = chartWidth - padding.left - padding.right;
    const plotHeight = chartHeight - padding.top - padding.bottom;
    const step = plotWidth / Math.max(orderedSessions.length, 1);
    const barWidth = Math.max(step, 16);
    const averageAccuracy =
      orderedSessions.reduce((total, recent) => total + recent.accuracy, 0) / Math.max(orderedSessions.length, 1);
    const axisY = padding.top + plotHeight;
    const averageY = padding.top + (plotHeight - plotHeight * averageAccuracy);

    const colorForAccuracy = (accuracy: number): string => {
      const clamped = Math.max(0, Math.min(accuracy, 1));
      if (clamped < 0.5) {
        const orangeProgress = clamped / 0.5;
        const hue = 18 + orangeProgress * 14;
        return `hsl(${hue}, 90%, 54%)`;
      }
      if (clamped === 0.5) {
        return 'hsl(48, 92%, 56%)';
      }
      const greenProgress = (clamped - 0.5) / 0.5;
      const hue = 48 + greenProgress * 88;
      const saturation = 86;
      const lightness = 56 - greenProgress * 8;
      return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
    };

    return {
      bars: orderedSessions.map((recent, index) => {
        const accuracyPercent = Math.round(recent.accuracy * 100);
        const barHeight = Math.max(plotHeight * recent.accuracy, 6);
        const x = padding.left + step * index;
        const y = padding.top + (plotHeight - barHeight);
        return {
          sessionId: recent.session_id,
          accuracyPercent,
          scoreLabel: formatScorePair(recent.correct_count, recent.score_possible),
          fillColor: colorForAccuracy(recent.accuracy),
          x,
          y,
          width: barWidth,
          height: barHeight,
          labelX: x + barWidth / 2
        };
      }),
      averageAccuracy,
      averageY,
      axisY,
      chartWidth,
      chartHeight,
      plotLeft: padding.left,
      plotRight: chartWidth - padding.right
    };
  }

  function buildRecoveryStageGraph(questions: QuestionRow[]): {
    stages: Array<{
      key: string;
      label: string;
      count: number;
      coolingCount: number;
      fillColor: string;
      x: number;
      y: number;
      width: number;
      height: number;
      coolingY: number;
      coolingHeight: number;
      labelX: number;
    }>;
    chartWidth: number;
    chartHeight: number;
    axisY: number;
    plotLeft: number;
    plotRight: number;
  } {
    const stageDefinitions = [
      { key: '1h', label: '1h', fillColor: 'hsl(20, 90%, 58%)' },
      { key: '3h', label: '3h', fillColor: 'hsl(30, 90%, 58%)' },
      { key: '6h', label: '6h', fillColor: 'hsl(40, 90%, 58%)' },
      { key: '12h', label: '12h', fillColor: 'hsl(52, 90%, 58%)' },
      { key: '1d', label: '1d', fillColor: 'hsl(166, 76%, 56%)' },
      { key: '3d', label: '3d', fillColor: 'hsl(188, 76%, 56%)' },
      { key: '7d', label: '7d', fillColor: 'hsl(204, 80%, 58%)' },
      { key: '14d', label: '14d', fillColor: 'hsl(220, 82%, 60%)' }
    ] as const;

    const counts = {
      '1h': 0,
      '3h': 0,
      '6h': 0,
      '12h': 0,
      '1d': 0,
      '3d': 0,
      '7d': 0,
      '14d': 0
    };
    const coolingCounts = {
      '1h': 0,
      '3h': 0,
      '6h': 0,
      '12h': 0,
      '1d': 0,
      '3d': 0,
      '7d': 0,
      '14d': 0
    };

    for (const question of questions) {
      if (question.schedule.logical_bucket in counts) {
        const label = question.schedule.logical_bucket as keyof typeof counts;
        counts[label] += 1;
        if (question.schedule.bucket === 'cooling') {
          coolingCounts[label] += 1;
        }
      }
    }

    const chartWidth = 560;
    const chartHeight = 220;
    const padding = { top: 28, right: 20, bottom: 52, left: 20 };
    const plotWidth = chartWidth - padding.left - padding.right;
    const plotHeight = chartHeight - padding.top - padding.bottom;
    const axisY = padding.top + plotHeight;
    const stepWidth = plotWidth / stageDefinitions.length;
    const barWidth = stepWidth;
    const maxCount = Math.max(...Object.values(counts), 1);

    return {
      stages: stageDefinitions.map((stage, index) => {
        const count = counts[stage.key as keyof typeof counts];
        const coolingCount = coolingCounts[stage.key as keyof typeof coolingCounts];
        const barHeight = count > 0 ? Math.max((plotHeight * count) / maxCount, 8) : 0;
        const coolingHeight =
          count > 0 && coolingCount > 0 ? Math.max((plotHeight * coolingCount) / maxCount, 8) : 0;
        const x = padding.left + stepWidth * index;
        const y = axisY - barHeight;
        const coolingY = axisY - coolingHeight;
        return {
          key: stage.key,
          label: stage.label,
          count,
          coolingCount,
          fillColor: stage.fillColor,
          x,
          y,
          width: barWidth,
          height: barHeight,
          coolingY,
          coolingHeight,
          labelX: x + barWidth / 2
        };
      }),
      chartWidth,
      chartHeight,
      axisY,
      plotLeft: padding.left,
      plotRight: chartWidth - padding.right
    };
  }

  function buildAuxiliaryStageGraph(questions: QuestionRow[]): {
    stages: Array<{
      key: string;
      label: string;
      count: number;
      fillColor: string;
      x: number;
      y: number;
      width: number;
      height: number;
      labelX: number;
    }>;
    chartWidth: number;
    chartHeight: number;
    axisY: number;
    plotLeft: number;
    plotRight: number;
  } {
    const stageDefinitions = [
      { key: 'unseen', label: 'Unseen', fillColor: 'hsl(276, 72%, 62%)' },
      { key: 'review', label: 'Review', fillColor: 'hsl(220, 10%, 72%)' },
      { key: 'bucketed', label: 'Bucketed', fillColor: 'hsl(208, 70%, 58%)' },
      { key: 'mastery', label: 'Mastery', fillColor: 'hsl(134, 62%, 54%)' }
    ] as const;

    const counts = {
      unseen: 0,
      review: 0,
      bucketed: 0,
      mastery: 0
    };

    for (const question of questions) {
      if (question.schedule.logical_bucket === 'review') {
        counts.review += 1;
      } else if (question.schedule.logical_bucket === 'unseen') {
        counts.unseen += 1;
      } else if (question.schedule.logical_bucket === 'mastery') {
        counts.mastery += 1;
      } else {
        counts.bucketed += 1;
      }
    }

    const chartWidth = 280;
    const chartHeight = 220;
    const padding = { top: 28, right: 20, bottom: 52, left: 20 };
    const plotWidth = chartWidth - padding.left - padding.right;
    const plotHeight = chartHeight - padding.top - padding.bottom;
    const axisY = padding.top + plotHeight;
    const stepWidth = plotWidth / stageDefinitions.length;
    const barWidth = stepWidth;
    const maxCount = Math.max(...Object.values(counts), 1);

    return {
      stages: stageDefinitions.map((stage, index) => {
        const count = counts[stage.key as keyof typeof counts];
        const barHeight = count > 0 ? Math.max((plotHeight * count) / maxCount, 8) : 0;
        const x = padding.left + stepWidth * index;
        const y = axisY - barHeight;
        return {
          key: stage.key,
          label: stage.label,
          count,
          fillColor: stage.fillColor,
          x,
          y,
          width: barWidth,
          height: barHeight,
          labelX: x + barWidth / 2
        };
      }),
      chartWidth,
      chartHeight,
      axisY,
      plotLeft: padding.left,
      plotRight: chartWidth - padding.right
    };
  }

  $: sortedQuestions = stats ? sortQuestions(stats.questions, sortKey, sortDirection) : [];
  $: sessionGraph = stats
    ? buildSessionGraph(stats.recent_sessions)
    : {
        bars: [],
        averageAccuracy: 0,
        averageY: 0,
        axisY: 0,
        chartWidth: 640,
        chartHeight: 220,
        plotLeft: 28,
        plotRight: 612
      };
  $: recoveryStageGraph = stats
    ? buildRecoveryStageGraph(stats.questions)
    : {
        stages: [],
        chartWidth: 560,
        chartHeight: 220,
        axisY: 168,
        plotLeft: 20,
        plotRight: 540
      };
  $: auxiliaryStageGraph = stats
    ? buildAuxiliaryStageGraph(stats.questions)
    : {
        stages: [],
        chartWidth: 280,
        chartHeight: 220,
        axisY: 168,
        plotLeft: 20,
        plotRight: 260
      };
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
      <div class="panel stats-chart-panel stats-chart-panel-wide">
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

      <div class="panel stats-chart-panel">
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

      <div class="panel stats-chart-panel">
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
    </div>

    <div class="panel table-panel">
      <div class="panel-header">
        <div>
          <h3>Questions</h3>
        </div>
      </div>

      {#if sortedQuestions.length === 0}
        <p class="muted-copy">No questions match this filter.</p>
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
              {#each sortedQuestions as question (question.question_id)}
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
