import type { QuestionRow } from '../types';

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

export type RecoveryStageGraph = ReturnType<typeof buildRecoveryStageGraph>;
export type AuxiliaryStageGraph = ReturnType<typeof buildAuxiliaryStageGraph>;
