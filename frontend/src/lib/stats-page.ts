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
export type RetryEligibilityGraph = ReturnType<typeof buildRetryEligibilityGraph>;
export type RetryEligibilityHourlyGraph = ReturnType<typeof buildRetryEligibilityHourlyGraph>;
export type RetryEligibilityLongRangeGraph = ReturnType<typeof buildRetryEligibilityLongRangeGraph>;
export type FirstSeenGraph = ReturnType<typeof buildFirstSeenGraph>;
export type StageDueMatrixGraph = ReturnType<typeof buildStageDueMatrixGraph>;

export const sortDefinitions: SortDefinition[] = [
  { key: 'rank', label: 'Order', defaultDirection: 'asc' },
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
  chartWidth: 360,
  chartHeight: 220,
  axisY: 168,
  plotLeft: 20,
  plotRight: 340
};

export const emptyAuxiliaryStageGraph = {
  stages: [],
  chartWidth: 360,
  chartHeight: 220,
  axisY: 168,
  plotLeft: 20,
  plotRight: 340
};

export const emptyRetryEligibilityGraph = {
  days: [],
  chartWidth: 360,
  chartHeight: 220,
  axisY: 168,
  plotLeft: 20,
  plotRight: 340
};

export const emptyRetryEligibilityHourlyGraph = {
  hours: [],
  chartWidth: 960,
  chartHeight: 240,
  axisY: 188,
  plotLeft: 24,
  plotRight: 936
};

export const emptyRetryEligibilityLongRangeGraph = {
  weeks: [],
  chartWidth: 1320,
  chartHeight: 240,
  axisY: 188,
  plotLeft: 24,
  plotRight: 1296
};

export const emptyFirstSeenGraph = {
  days: [],
  chartWidth: 360,
  chartHeight: 220,
  axisY: 168,
  plotLeft: 20,
  plotRight: 340
};

export const emptyStageDueMatrixGraph = {
  columns: [],
  rows: [],
  cells: [],
  maxCount: 0,
  chartWidth: 640,
  chartHeight: 94,
  plotLeft: 84,
  plotRight: 620,
  plotTop: 52,
  plotBottom: 74
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
    case '30d':
      return [8, question.prompt_preview];
    case '60d':
      return [9, question.prompt_preview];
    case 'unseen':
      return [10, question.prompt_preview];
    case 'mastery':
      return [11, question.prompt_preview];
    case 'review':
      return [12, question.prompt_preview];
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

const recoveryStageDefinitions = [
  { key: '1h', label: '1h', fillColor: 'hsl(20, 90%, 58%)' },
  { key: '3h', label: '3h', fillColor: 'hsl(30, 90%, 58%)' },
  { key: '6h', label: '6h', fillColor: 'hsl(40, 90%, 58%)' },
  { key: '12h', label: '12h', fillColor: 'hsl(52, 90%, 58%)' },
  { key: '1d', label: '1d', fillColor: 'hsl(166, 76%, 56%)' },
  { key: '3d', label: '3d', fillColor: 'hsl(188, 76%, 56%)' },
  { key: '7d', label: '7d', fillColor: 'hsl(204, 80%, 58%)' },
  { key: '14d', label: '14d', fillColor: 'hsl(220, 82%, 60%)' },
  { key: '30d', label: '30d', fillColor: 'hsl(236, 78%, 66%)' },
  { key: '60d', label: '60d', fillColor: 'hsl(252, 72%, 70%)' }
] as const;
const stageDueMatrixColumnDefinitions = [
  { key: 'lt1d', label: '<1d' },
  { key: '1d', label: '1d' },
  { key: '3d', label: '3d' },
  { key: '7d', label: '7d' },
  { key: '14d', label: '14d' },
  { key: '30d', label: '30d' },
  { key: '60d', label: '60d' }
] as const;

const fixedRetryBucketLabels = recoveryStageDefinitions.map((stage) => stage.key);
const fixedRetryBuckets = new Set(fixedRetryBucketLabels);
const stageDueMatrixDayCount = 61;
const retryEligibilityDayDefinitions = [
  { key: 'lt1', label: '<1', fillColor: 'hsl(22, 92%, 58%)' },
  { key: 'day1', label: '1', fillColor: 'hsl(34, 90%, 58%)' },
  { key: 'day2', label: '2', fillColor: 'hsl(46, 90%, 58%)' },
  { key: 'day3', label: '3', fillColor: 'hsl(166, 76%, 56%)' },
  { key: 'day4', label: '4', fillColor: 'hsl(188, 76%, 56%)' },
  { key: 'day5', label: '5', fillColor: 'hsl(204, 80%, 58%)' },
  { key: 'day6', label: '6', fillColor: 'hsl(220, 82%, 60%)' },
  { key: 'day7', label: '7', fillColor: 'hsl(238, 78%, 66%)' },
  { key: 'gt7', label: '>7', fillColor: 'hsl(260, 70%, 70%)' }
] as const;
type RetryEligibilityCategory = (typeof retryEligibilityDayDefinitions)[number]['key'];
type StageDueMatrixColumnKey = (typeof stageDueMatrixColumnDefinitions)[number]['key'];
type RetryEligibilityEntry = {
  dueAt: Date | null;
  category: RetryEligibilityCategory;
};
const dayInMs = 24 * 60 * 60 * 1000;
const hourInMs = 60 * 60 * 1000;
const hourlyDetailWindowCount = 24;
const weeklyDetailWindowCount = 52;
const zonedDatePartFormatters = new Map<string, Intl.DateTimeFormat>();

function isFixedRetryBucket(logicalBucket: QuestionRow['schedule']['logical_bucket']): logicalBucket is (typeof fixedRetryBucketLabels)[number] {
  return fixedRetryBuckets.has(logicalBucket as (typeof fixedRetryBucketLabels)[number]);
}

type ZonedDateParts = {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
};

function zonedDatePartFormatter(timeZone: string): Intl.DateTimeFormat {
  const cached = zonedDatePartFormatters.get(timeZone);
  if (cached) {
    return cached;
  }

  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23'
  });
  zonedDatePartFormatters.set(timeZone, formatter);
  return formatter;
}

function zonedDateParts(value: Date, timeZone: string): ZonedDateParts {
  const parts = zonedDatePartFormatter(timeZone).formatToParts(value);
  const values = Object.fromEntries(parts.filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]));
  return {
    year: Number(values.year),
    month: Number(values.month),
    day: Number(values.day),
    hour: Number(values.hour),
    minute: Number(values.minute)
  };
}

function zonedDayNumber(value: Date, timeZone: string): number {
  const parts = zonedDateParts(value, timeZone);
  return Math.floor(Date.UTC(parts.year, parts.month - 1, parts.day) / dayInMs);
}

function dayNumberDate(dayNumber: number): Date {
  return new Date(dayNumber * dayInMs);
}

function formatCalendarDay(dayNumber: number, options: Intl.DateTimeFormatOptions): string {
  return dayNumberDate(dayNumber).toLocaleDateString(undefined, { ...options, timeZone: 'UTC' });
}

export function buildRecoveryStageGraph(questions: QuestionRow[]) {
  const counts = {
    '1h': 0,
    '3h': 0,
    '6h': 0,
    '12h': 0,
    '1d': 0,
    '3d': 0,
    '7d': 0,
    '14d': 0,
    '30d': 0,
    '60d': 0
  };
  const coolingCounts = {
    '1h': 0,
    '3h': 0,
    '6h': 0,
    '12h': 0,
    '1d': 0,
    '3d': 0,
    '7d': 0,
    '14d': 0,
    '30d': 0,
    '60d': 0
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

  const chartWidth = 360;
  const chartHeight = 220;
  const padding = { top: 28, right: 20, bottom: 52, left: 20 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;
  const axisY = padding.top + plotHeight;
  const stepWidth = plotWidth / recoveryStageDefinitions.length;
  const barWidth = stepWidth;
  const maxCount = Math.max(...Object.values(counts), 1);

  return {
    stages: recoveryStageDefinitions.map((stage, index) => {
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

function stageDueMatrixColumnKey(logicalBucket: QuestionRow['schedule']['logical_bucket']): StageDueMatrixColumnKey | null {
  switch (logicalBucket) {
    case '1h':
    case '3h':
    case '6h':
    case '12h':
      return 'lt1d';
    case '1d':
    case '3d':
    case '7d':
    case '14d':
    case '30d':
    case '60d':
      return logicalBucket;
    default:
      return null;
  }
}

function formatLongDate(dayNumber: number): string {
  return formatCalendarDay(dayNumber, { weekday: 'short', month: 'short', day: 'numeric' });
}

function heatmapCellFill(count: number, maxCount: number): string {
  if (count <= 0 || maxCount <= 0) {
    return 'rgba(148, 163, 184, 0.12)';
  }
  const intensity = Math.sqrt(count / maxCount);
  const lightness = 82 - intensity * 42;
  const alpha = 0.34 + intensity * 0.56;
  return `hsla(201, 88%, ${lightness}%, ${alpha})`;
}

function heatmapCellTextColor(count: number, maxCount: number): string {
  if (count <= 0 || maxCount <= 0) {
    return 'rgba(15, 23, 42, 0.82)';
  }
  return count / maxCount >= 0.4 ? '#f8fafc' : 'rgba(15, 23, 42, 0.9)';
}

export function buildStageDueMatrixGraph(questions: QuestionRow[], referenceTime: Date = new Date(), timeZone = 'UTC') {
  const reference = new Date(referenceTime);
  const referenceDayNumber = zonedDayNumber(reference, timeZone);
  const columnDefinitions = stageDueMatrixColumnDefinitions.map((column, index) => ({
    ...column,
    index
  }));
  const rowDefinitions = Array.from({ length: stageDueMatrixDayCount }, (_, dayOffset) => {
    const dayNumber = referenceDayNumber + dayOffset;
    return {
      key: `day-${dayOffset}`,
      dayOffset,
      dayNumber,
      label: dayOffset === 0 ? 'Today' : formatCalendarDay(dayNumber, { month: 'short', day: 'numeric' }),
      fullLabel: dayOffset === 0 ? `Today (${formatLongDate(dayNumber)})` : formatLongDate(dayNumber)
    };
  });
  const counts = Array.from({ length: rowDefinitions.length }, () =>
    Array.from({ length: columnDefinitions.length }, () => 0)
  );

  for (const question of questions) {
    const columnKey = stageDueMatrixColumnKey(question.schedule.logical_bucket);
    if (!columnKey) {
      continue;
    }

    const columnIndex = columnDefinitions.findIndex((column) => column.key === columnKey);
    if (columnIndex < 0) {
      continue;
    }

    const dueAt = parseRetryDueAt(question.schedule.next_due_at);
    if (!dueAt) {
      continue;
    }

    let rowIndex = 0;
    const dayOffset = zonedDayNumber(dueAt, timeZone) - referenceDayNumber;
    if (dayOffset > 0) {
      if (dayOffset >= rowDefinitions.length) {
        continue;
      }
      rowIndex = dayOffset;
    }

    counts[rowIndex]![columnIndex] += 1;
  }

  const lastNonEmptyRowIndex = counts.reduce((lastIndex, rowCounts, rowIndex) => {
    return rowCounts.some((count) => count > 0) ? rowIndex : lastIndex;
  }, -1);

  const maxCount = Math.max(...counts.flat(), 0);
  const chartWidth = 640;
  const padding = { top: 52, right: 20, bottom: 20, left: 84 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const columnWidth = plotWidth / columnDefinitions.length;
  const cellWidth = Math.max(columnWidth - 4, 20);
  const rowHeight = 22;
  const visibleRowCount = lastNonEmptyRowIndex >= 0 ? lastNonEmptyRowIndex + 1 : 0;
  const visibleRows = rowDefinitions.slice(0, visibleRowCount);
  const chartHeight = padding.top + visibleRows.length * rowHeight + padding.bottom;

  return {
    columns: columnDefinitions.map((column) => {
      const x = padding.left + columnWidth * column.index + (columnWidth - cellWidth) / 2;
      return {
        key: column.key,
        label: column.label,
        x,
        width: cellWidth,
        labelX: x + cellWidth / 2
      };
    }),
    rows: visibleRows.map((row, index) => {
      const y = padding.top + index * rowHeight;
      return {
        key: row.key,
        label: row.label,
        fullLabel: row.fullLabel,
        y,
        height: rowHeight,
        labelY: y + rowHeight / 2 + 4
      };
    }),
    cells: visibleRows.flatMap((row, rowIndex) =>
      columnDefinitions.map((column) => {
        const count = counts[rowIndex]![column.index];
        const x = padding.left + columnWidth * column.index + (columnWidth - cellWidth) / 2;
        const y = padding.top + rowIndex * rowHeight;
        return {
          key: `${row.key}-${column.key}`,
          rowKey: row.key,
          columnKey: column.key,
          count,
          x,
          y,
          width: cellWidth,
          height: rowHeight - 2,
          fillColor: heatmapCellFill(count, maxCount),
          textColor: heatmapCellTextColor(count, maxCount),
          labelX: x + cellWidth / 2,
          labelY: y + (rowHeight - 2) / 2 + 4,
          title: `${column.label} due ${row.fullLabel}: ${count} question${count === 1 ? '' : 's'}`
        };
      })
    ),
    maxCount,
    chartWidth,
    chartHeight,
    plotLeft: padding.left,
    plotRight: chartWidth - padding.right,
    plotTop: padding.top,
    plotBottom: chartHeight - padding.bottom
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

  const chartWidth = 360;
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

function startOfLocalHour(value: Date): Date {
  const date = new Date(value);
  date.setMinutes(0, 0, 0);
  return date;
}

function parseRetryDueAt(value: string | null | undefined): Date | null {
  if (!value) {
    return null;
  }
  const dueAt = new Date(value);
  return Number.isNaN(dueAt.getTime()) ? null : dueAt;
}

function classifyRetryEligibilityQuestion(
  question: QuestionRow,
  referenceDayNumber: number,
  timeZone: string
): RetryEligibilityEntry | null {
  const logicalBucket = question.schedule.logical_bucket;
  if (!isFixedRetryBucket(logicalBucket)) {
    return null;
  }

  const dueAt = parseRetryDueAt(question.schedule.next_due_at);
  if (!dueAt) {
    return null;
  }

  const dayOffset = zonedDayNumber(dueAt, timeZone) - referenceDayNumber;
  if (dayOffset <= 0) {
    return { dueAt, category: 'lt1' };
  }
  if (dayOffset <= 7) {
    return { dueAt, category: `day${dayOffset}` as RetryEligibilityCategory };
  }
  return { dueAt, category: 'gt7' };
}

function retryEligibilityEntries(questions: QuestionRow[], referenceTime: Date, timeZone: string): RetryEligibilityEntry[] {
  const referenceDayNumber = zonedDayNumber(referenceTime, timeZone);
  return questions
    .map((question) => classifyRetryEligibilityQuestion(question, referenceDayNumber, timeZone))
    .filter((entry): entry is RetryEligibilityEntry => entry !== null);
}

export function buildRetryEligibilityGraph(questions: QuestionRow[], referenceTime: Date = new Date(), timeZone = 'UTC') {
  const reference = new Date(referenceTime);
  const counts = Array.from({ length: retryEligibilityDayDefinitions.length }, () => 0);

  for (const entry of retryEligibilityEntries(questions, reference, timeZone)) {
    const index = retryEligibilityDayDefinitions.findIndex((day) => day.key === entry.category);
    if (index >= 0) {
      counts[index] += 1;
    }
  }

  const chartWidth = 360;
  const chartHeight = 220;
  const padding = { top: 28, right: 20, bottom: 52, left: 20 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;
  const axisY = padding.top + plotHeight;
  const stepWidth = plotWidth / retryEligibilityDayDefinitions.length;
  const barWidth = Math.max(stepWidth - 4, 20);
  const maxCount = Math.max(...counts, 1);

  return {
    days: retryEligibilityDayDefinitions.map((day, index) => {
      const count = counts[index];
      const barHeight = count > 0 ? Math.max((plotHeight * count) / maxCount, 8) : 0;
      const x = padding.left + stepWidth * index + (stepWidth - barWidth) / 2;
      const y = axisY - barHeight;
      return {
        key: day.key,
        label: day.label,
        count,
        fillColor: day.fillColor,
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

function formatTwentyFourHourLabel(value: Date): string {
  return `${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}`;
}

function formatDayRangeLabel(startTime: Date, endTime: Date): string {
  return `${startTime.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric'
  })} ${formatTwentyFourHourLabel(startTime)} - ${endTime.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric'
  })} ${formatTwentyFourHourLabel(endTime)}`;
}

export function buildRetryEligibilityHourlyGraph(
  questions: QuestionRow[],
  referenceTime: Date = new Date(),
  timeZone = 'UTC'
) {
  const reference = new Date(referenceTime);
  const referenceHourStart = startOfLocalHour(reference);
  const counts = Array.from({ length: hourlyDetailWindowCount }, () => 0);

  for (const entry of retryEligibilityEntries(questions, reference, timeZone)) {
    if (entry.category !== 'lt1') {
      continue;
    }
    if (!entry.dueAt || entry.dueAt.getTime() <= reference.getTime()) {
      counts[0] += 1;
      continue;
    }

    const dueHourStart = startOfLocalHour(entry.dueAt);
    const hourOffset = Math.floor((dueHourStart.getTime() - referenceHourStart.getTime()) / hourInMs);
    if (hourOffset >= 0 && hourOffset < counts.length) {
      counts[hourOffset] += 1;
    }
  }

  const chartWidth = 960;
  const chartHeight = 240;
  const padding = { top: 28, right: 24, bottom: 52, left: 24 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;
  const axisY = padding.top + plotHeight;
  const stepWidth = plotWidth / hourlyDetailWindowCount;
  const barWidth = Math.max(stepWidth - 2, 8);
  const maxCount = Math.max(...counts, 1);

  return {
    hours: Array.from({ length: hourlyDetailWindowCount }, (_, index) => {
      const count = counts[index];
      const barHeight = count > 0 ? Math.max((plotHeight * count) / maxCount, 8) : 0;
      const x = padding.left + stepWidth * index + (stepWidth - barWidth) / 2;
      const y = axisY - barHeight;
      const rangeStart = new Date(referenceHourStart);
      rangeStart.setHours(referenceHourStart.getHours() + index);
      const rangeEnd = new Date(rangeStart);
      rangeEnd.setHours(rangeStart.getHours() + 1);
      return {
        key: `hour-${index}`,
        label: index === 0 || index % 4 === 0 ? formatTwentyFourHourLabel(rangeStart) : '',
        fullLabel: formatDayRangeLabel(rangeStart, rangeEnd),
        count,
        fillColor: `hsl(${20 + index * 4}, 88%, ${58 - Math.min(index, 10)}%)`,
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

function formatShortDate(value: Date): string {
  return value.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function buildRetryEligibilityLongRangeGraph(
  questions: QuestionRow[],
  referenceTime: Date = new Date(),
  timeZone = 'UTC'
) {
  const reference = new Date(referenceTime);
  const counts = Array.from({ length: weeklyDetailWindowCount }, () => 0);

  for (const entry of retryEligibilityEntries(questions, reference, timeZone)) {
    if (entry.category !== 'gt7' || !entry.dueAt) {
      continue;
    }

    const diffMs = entry.dueAt.getTime() - reference.getTime();
    if (diffMs <= 7 * dayInMs) {
      continue;
    }
    const weekIndex = Math.max(0, Math.ceil((diffMs - 7 * dayInMs) / (7 * dayInMs)) - 1);
    if (weekIndex < counts.length) {
      counts[weekIndex] += 1;
    }
  }

  const chartWidth = 1320;
  const chartHeight = 240;
  const padding = { top: 28, right: 24, bottom: 52, left: 24 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;
  const axisY = padding.top + plotHeight;
  const stepWidth = plotWidth / weeklyDetailWindowCount;
  const barWidth = Math.max(stepWidth - 2, 6);
  const maxCount = Math.max(...counts, 1);

  return {
    weeks: Array.from({ length: weeklyDetailWindowCount }, (_, index) => {
      const count = counts[index];
      const barHeight = count > 0 ? Math.max((plotHeight * count) / maxCount, 8) : 0;
      const x = padding.left + stepWidth * index + (stepWidth - barWidth) / 2;
      const y = axisY - barHeight;
      const rangeStart = new Date(reference.getTime() + (7 + index * 7) * dayInMs);
      const rangeEnd = new Date(reference.getTime() + (14 + index * 7) * dayInMs);
      return {
        key: `week-${index + 2}`,
        label: index === 0 || (index + 1) % 4 === 0 ? `W${index + 2}` : '',
        fullLabel: `Week ${index + 2}: ${formatShortDate(rangeStart)} - ${formatShortDate(rangeEnd)}`,
        count,
        fillColor: `hsl(${200 + Math.min(index, 12) * 3}, 72%, ${58 + Math.min(index, 8)}%)`,
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

export function buildFirstSeenGraph(questions: QuestionRow[], referenceTime: Date = new Date(), timeZone = 'UTC') {
  const reference = new Date(referenceTime);
  const referenceDayNumber = zonedDayNumber(reference, timeZone);
  const dayDefinitions = Array.from({ length: 7 }, (_, index) => {
    const dayOffset = 6 - index;
    const dayNumber = referenceDayNumber - dayOffset;
    return {
      key: `day-${index}`,
      label: formatCalendarDay(dayNumber, { weekday: 'short' }),
      fullLabel: formatCalendarDay(dayNumber, { month: 'short', day: 'numeric' }),
      fillColor: `hsl(${170 + index * 8}, 74%, ${62 - index * 3}%)`,
      dayNumber
    };
  });
  const counts = Array.from({ length: dayDefinitions.length }, () => 0);

  for (const question of questions) {
    if (!question.first_asked_at) {
      continue;
    }

    const firstAskedAt = new Date(question.first_asked_at);
    if (Number.isNaN(firstAskedAt.getTime())) {
      continue;
    }

    const daysAgo = referenceDayNumber - zonedDayNumber(firstAskedAt, timeZone);
    if (daysAgo < 0 || daysAgo >= dayDefinitions.length) {
      continue;
    }
    counts[dayDefinitions.length - 1 - daysAgo] += 1;
  }

  const chartWidth = 360;
  const chartHeight = 220;
  const padding = { top: 28, right: 20, bottom: 52, left: 20 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;
  const axisY = padding.top + plotHeight;
  const stepWidth = plotWidth / dayDefinitions.length;
  const barWidth = Math.max(stepWidth - 4, 20);
  const maxCount = Math.max(...counts, 1);

  return {
    days: dayDefinitions.map((day, index) => {
      const count = counts[index];
      const barHeight = count > 0 ? Math.max((plotHeight * count) / maxCount, 8) : 0;
      const x = padding.left + stepWidth * index + (stepWidth - barWidth) / 2;
      const y = axisY - barHeight;
      return {
        key: day.key,
        label: day.label,
        fullLabel: day.fullLabel,
        count,
        fillColor: day.fillColor,
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
