import type { QuestionRow } from '../types';
import { formatCalendarDay, parseRetryDueAt, zonedDayNumber } from './timezone';

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

const stageDueMatrixColumnDefinitions = [
  { key: 'lt1d', label: '<1d' },
  { key: '1d', label: '1d' },
  { key: '3d', label: '3d' },
  { key: '7d', label: '7d' },
  { key: '14d', label: '14d' },
  { key: '30d', label: '30d' },
  { key: '60d', label: '60d' }
] as const;
const stageDueMatrixDayCount = 61;

type StageDueMatrixColumnKey = (typeof stageDueMatrixColumnDefinitions)[number]['key'];

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

export type FirstSeenGraph = ReturnType<typeof buildFirstSeenGraph>;
export type StageDueMatrixGraph = ReturnType<typeof buildStageDueMatrixGraph>;
