import type { QuestionRow } from '../types';

export type SortDirection = 'asc' | 'desc';
export type SortKey = 'prompt' | 'bucket' | 'last_seen' | 'rank' | 'attempts' | 'correct_percentage';

export type SortDefinition = {
  key: SortKey;
  label: string;
  defaultDirection: SortDirection;
};

export const sortDefinitions: SortDefinition[] = [
  { key: 'rank', label: 'Order', defaultDirection: 'asc' },
  { key: 'prompt', label: 'Prompt', defaultDirection: 'asc' },
  { key: 'bucket', label: 'Bucket', defaultDirection: 'asc' },
  { key: 'last_seen', label: 'Last seen', defaultDirection: 'desc' },
  { key: 'attempts', label: 'Attempts', defaultDirection: 'desc' },
  { key: 'correct_percentage', label: 'Correct', defaultDirection: 'desc' }
];

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
