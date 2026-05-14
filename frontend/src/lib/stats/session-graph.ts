import type { RecentSession } from '../types';
import { formatScorePair } from './format';

export const emptySessionGraph = {
  bars: [],
  averageAccuracy: 0,
  averageY: 0,
  axisY: 0,
  chartWidth: 360,
  chartHeight: 220,
  plotLeft: 20,
  plotRight: 340
};

export function buildSessionGraph(recentSessions: RecentSession[]) {
  const orderedSessions = [...recentSessions].sort((left, right) => left.created_at.localeCompare(right.created_at));
  const chartWidth = 360;
  const chartHeight = 220;
  const padding = { top: 28, right: 20, bottom: 52, left: 20 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;
  const step = plotWidth / Math.max(orderedSessions.length, 1);
  const barWidth = Math.max(Math.min(step * 0.72, 34), 16);
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

export type SessionGraph = ReturnType<typeof buildSessionGraph>;
