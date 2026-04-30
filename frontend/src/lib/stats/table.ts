import type { LogicalBucket, QuestionRow } from '../types';

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

export const visibleQuestionSortDefinitions = sortDefinitions.filter((definition) => definition.key !== 'bucket');

export type QuestionBucketDefinition = {
  key: LogicalBucket;
  label: string;
};

export type QuestionBucketGroup = QuestionBucketDefinition & {
  questions: QuestionRow[];
};

export const questionBucketDefinitions: QuestionBucketDefinition[] = [
  { key: 'review', label: 'Review' },
  { key: '1h', label: '1h' },
  { key: '3h', label: '3h' },
  { key: '6h', label: '6h' },
  { key: '12h', label: '12h' },
  { key: '1d', label: '1d' },
  { key: '3d', label: '3d' },
  { key: '7d', label: '7d' },
  { key: '14d', label: '14d' },
  { key: '30d', label: '30d' },
  { key: '60d', label: '60d' },
  { key: 'unseen', label: 'Unseen' },
  { key: 'mastery', label: 'Mastery' }
];

function bucketOrder(logicalBucket: LogicalBucket): number {
  switch (logicalBucket) {
    case 'review':
      return 0;
    case '1h':
      return 1;
    case '3h':
      return 2;
    case '6h':
      return 3;
    case '12h':
      return 4;
    case '1d':
      return 5;
    case '3d':
      return 6;
    case '7d':
      return 7;
    case '14d':
      return 8;
    case '30d':
      return 9;
    case '60d':
      return 10;
    case 'unseen':
      return 11;
    case 'mastery':
      return 12;
    default:
      return 99;
  }
}

function bucketSortTuple(question: QuestionRow): [number, string] {
  return [bucketOrder(question.schedule.logical_bucket), question.prompt_preview];
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

export function groupQuestionsByBucket(questions: QuestionRow[]): QuestionBucketGroup[] {
  return questionBucketDefinitions.map((definition) => ({
    ...definition,
    questions: questions.filter((question) => question.schedule.logical_bucket === definition.key)
  }));
}
