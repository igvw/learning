import type { QuestionRow } from '../types';
import { getDisplayBucketKey } from './table';

export function formatScore(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(/\.0$/, '');
}

export function formatScorePair(earned: number, possible: number): string {
  return `${formatScore(earned)}/${formatScore(possible)}`;
}

export function formatBucketLabel(question: QuestionRow): string {
  switch (getDisplayBucketKey(question)) {
    case 'review':
      return 'Review';
    case 'active':
      return 'Active';
    case 'unseen':
      return 'Unseen';
    case 'mastery':
      return 'Mastery';
    default:
      return getDisplayBucketKey(question);
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
    minute: '2-digit',
    hour12: false
  });
}
