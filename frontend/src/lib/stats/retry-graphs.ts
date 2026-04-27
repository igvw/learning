import type { QuestionRow } from '../types';
import { parseRetryDueAt, startOfLocalHour, timeConstants, zonedDayNumber } from './timezone';

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

const fixedRetryBucketLabels = ['1h', '3h', '6h', '12h', '1d', '3d', '7d', '14d', '30d', '60d'] as const;
const fixedRetryBuckets = new Set(fixedRetryBucketLabels);
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
const hourlyDetailWindowCount = 24;
const weeklyDetailWindowCount = 52;

type RetryEligibilityCategory = (typeof retryEligibilityDayDefinitions)[number]['key'];
type RetryEligibilityEntry = {
  dueAt: Date | null;
  category: RetryEligibilityCategory;
};

function isFixedRetryBucket(
  logicalBucket: QuestionRow['schedule']['logical_bucket']
): logicalBucket is (typeof fixedRetryBucketLabels)[number] {
  return fixedRetryBuckets.has(logicalBucket as (typeof fixedRetryBucketLabels)[number]);
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
    const hourOffset = Math.floor((dueHourStart.getTime() - referenceHourStart.getTime()) / timeConstants.hourInMs);
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
    if (diffMs <= 7 * timeConstants.dayInMs) {
      continue;
    }
    const weekIndex = Math.max(0, Math.ceil((diffMs - 7 * timeConstants.dayInMs) / (7 * timeConstants.dayInMs)) - 1);
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
      const rangeStart = new Date(reference.getTime() + (7 + index * 7) * timeConstants.dayInMs);
      const rangeEnd = new Date(reference.getTime() + (14 + index * 7) * timeConstants.dayInMs);
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

export type RetryEligibilityGraph = ReturnType<typeof buildRetryEligibilityGraph>;
export type RetryEligibilityHourlyGraph = ReturnType<typeof buildRetryEligibilityHourlyGraph>;
export type RetryEligibilityLongRangeGraph = ReturnType<typeof buildRetryEligibilityLongRangeGraph>;
