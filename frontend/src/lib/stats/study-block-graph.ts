import type { StudyBlock } from '../types';

export const emptyStudyBlockGraph = {
  bars: [],
  axisY: 0,
  chartWidth: 360,
  chartHeight: 220,
  plotLeft: 20,
  plotRight: 340
};

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  });
}

function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
}

function formatStudyBlockTitle(block: StudyBlock): string {
  const questionLabel = block.answered_count === 1 ? 'question' : 'questions';
  const startDate = formatDate(block.started_at);
  const endDate = formatDate(block.ended_at);
  const timeRange =
    startDate === endDate
      ? `${startDate}, ${formatTime(block.started_at)}-${formatTime(block.ended_at)}`
      : `${startDate}, ${formatTime(block.started_at)} - ${endDate}, ${formatTime(block.ended_at)}`;
  return `${timeRange}: ${block.answered_count} ${questionLabel}`;
}

export function buildStudyBlockGraph(studyBlocks: StudyBlock[]) {
  const orderedBlocks = [...studyBlocks]
    .sort((left, right) => left.ended_at.localeCompare(right.ended_at))
    .slice(-10);
  const chartWidth = 360;
  const chartHeight = 220;
  const padding = { top: 28, right: 20, bottom: 52, left: 20 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;
  const axisY = padding.top + plotHeight;
  const stepWidth = plotWidth / Math.max(orderedBlocks.length, 1);
  const barWidth = Math.max(Math.min(stepWidth * 0.72, 34), 12);
  const maxCount = Math.max(...orderedBlocks.map((block) => block.answered_count), 1);

  return {
    bars: orderedBlocks.map((block, index) => {
      const barHeight = Math.max((plotHeight * block.answered_count) / maxCount, 8);
      const x = padding.left + stepWidth * index + (stepWidth - barWidth) / 2;
      const y = axisY - barHeight;
      return {
        startedAt: block.started_at,
        endedAt: block.ended_at,
        answeredCount: block.answered_count,
        dayLabel: block.day_label,
        title: formatStudyBlockTitle(block),
        x,
        y,
        width: barWidth,
        height: barHeight,
        labelX: x + barWidth / 2
      };
    }),
    axisY,
    chartWidth,
    chartHeight,
    plotLeft: padding.left,
    plotRight: chartWidth - padding.right
  };
}

export type StudyBlockGraph = ReturnType<typeof buildStudyBlockGraph>;
