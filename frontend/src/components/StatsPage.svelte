<script lang="ts">
  import type { QuestionRow, RecentSession, StatsResponse } from '../lib/types';

  type SortDirection = 'asc' | 'desc';
  type SortKey = 'prompt' | 'question_type' | 'module_title' | 'rank' | 'attempts' | 'correct_percentage';

  type SortDefinition = {
    key: SortKey;
    label: string;
    defaultDirection: SortDirection;
  };

  const sortDefinitions: SortDefinition[] = [
    { key: 'rank', label: 'Rank', defaultDirection: 'asc' },
    { key: 'prompt', label: 'Prompt', defaultDirection: 'asc' },
    { key: 'question_type', label: 'Type', defaultDirection: 'asc' },
    { key: 'module_title', label: 'Module', defaultDirection: 'asc' },
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

  function formatScore(value: number): string {
    return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(/\.0$/, '');
  }

  function formatScorePair(earned: number, possible: number): string {
    return `${formatScore(earned)}/${formatScore(possible)}`;
  }

  function formatScheduleLabel(question: QuestionRow): string {
    switch (question.schedule.bucket) {
      case 'hot':
        return `Hot · recovery ${question.schedule.recovery_streak ?? 0}/${2}`;
      case 'due_review':
        return `Due review · step ${(question.schedule.interval_step ?? 0) + 1}`;
      case 'unseen':
        return 'Unseen';
      case 'one_shot_easy':
        return 'First pass correct';
      case 'not_due_recovered':
        return question.schedule.next_due_at
          ? `Cooling · due ${new Date(question.schedule.next_due_at).toLocaleDateString()}`
          : 'Cooling';
      default:
        return 'Seen correct';
    }
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
      case 'question_type':
        return left.question_type.localeCompare(right.question_type);
      case 'module_title':
        return left.module_title.localeCompare(right.module_title);
      case 'rank':
        return left.rank - right.rank;
      case 'attempts':
        return left.attempts - right.attempts;
      case 'correct_percentage':
        return left.correct_percentage - right.correct_percentage;
    }
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
      const comparison = compareQuestions(left, right, activeSortKey);
      if (comparison !== 0) {
        return comparison * directionMultiplier;
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
    const barWidth = Math.min(42, Math.max(step * 0.58, 16));
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
        const x = padding.left + step * index + (step - barWidth) / 2;
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

    <div class="panel">
      <div class="panel-header">
        <div>
          <p class="eyebrow">Recent sessions</p>
          <h3>Latest quiz performance</h3>
        </div>
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
                <tr class:flagged-review={question.review_flag} on:click={() => onOpenEdit(question)}>
                  <td>{question.rank}</td>
                  <td>
                    <div class="question-cell">
                      <span>{question.prompt_preview}</span>
                      <span class="question-schedule">{formatScheduleLabel(question)}</span>
                    </div>
                  </td>
                  <td>{question.question_type}</td>
                  <td>{question.module_title}</td>
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
