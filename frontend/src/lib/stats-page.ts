import type { QuestionRow, RecentSession } from './types';

export type SortDirection = 'asc' | 'desc';
export type SortKey = 'prompt' | 'bucket' | 'last_seen' | 'rank' | 'attempts' | 'correct_percentage';

export type SortDefinition = {
  key: SortKey;
  label: string;
  defaultDirection: SortDirection;
};

export type SessionGraph = ReturnType<typeof buildSessionGraph>;
export type RecoveryStageGraph = ReturnType<typeof buildRecoveryStageGraph>;
export type AuxiliaryStageGraph = ReturnType<typeof buildAuxiliaryStageGraph>;

export const sortDefinitions: SortDefinition[] = [
  { key: 'rank', label: 'Rank', defaultDirection: 'asc' },
  { key: 'prompt', label: 'Prompt', defaultDirection: 'asc' },
  { key: 'bucket', label: 'Bucket', defaultDirection: 'asc' },
  { key: 'last_seen', label: 'Last seen', defaultDirection: 'desc' },
  { key: 'attempts', label: 'Attempts', defaultDirection: 'desc' },
  { key: 'correct_percentage', label: 'Correct', defaultDirection: 'desc' }
];

export const emptySessionGraph = {
  bars: [],
  averageAccuracy: 0,
  averageY: 0,
  axisY: 0,
  chartWidth: 640,
  chartHeight: 220,
  plotLeft: 28,
  plotRight: 612
};

export const emptyRecoveryStageGraph = {
  stages: [],
  chartWidth: 560,
  chartHeight: 220,
  axisY: 168,
  plotLeft: 20,
  plotRight: 540
};

export const emptyAuxiliaryStageGraph = {
  stages: [],
  chartWidth: 280,
  chartHeight: 220,
  axisY: 168,
  plotLeft: 20,
  plotRight: 260
};

export function formatScore(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(/\.0$/, '');
}

export function formatScorePair(earned: number, possible: number): string {
  return `${formatScore(earned)}/${formatScore(possible)}`;
}

export function formatBucketLabel(question: QuestionRow): string {
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

export function formatLastSeen(value: string | null): string {
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

function compareLastSeen(left: QuestionRow, right: QuestionRow, direction: SortDirection): number {
  if (!left.last_asked_at && !right.last_asked_at) {
    return 0;
  }
  if (!left.last_asked_at) {
    return 1;
  }
  if (!right.last_asked_at) {
    return -1;
  }
  const comparison = new Date(left.last_asked_at).getTime() - new Date(right.last_asked_at).getTime();
  return direction === 'asc' ? comparison : -comparison;
}

function compareQuestions(left: QuestionRow, right: QuestionRow, key: SortKey): number {
  switch (key) {
    case 'prompt':
      return left.prompt_preview.localeCompare(right.prompt_preview);
    case 'bucket':
      return compareBucket(left, right);
    case 'last_seen':
      return compareLastSeen(left, right, 'asc');
    case 'rank':
      return left.rank - right.rank;
    case 'attempts':
      return left.attempts - right.attempts;
    case 'correct_percentage':
      return left.correct_percentage - right.correct_percentage;
  }
}

export function sortQuestions(
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

export function buildSessionGraph(recentSessions: RecentSession[]) {
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

export function buildRecoveryStageGraph(questions: QuestionRow[]) {
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

export function buildAuxiliaryStageGraph(questions: QuestionRow[]) {
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
