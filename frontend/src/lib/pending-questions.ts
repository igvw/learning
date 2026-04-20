import type { PendingQuestion } from './types';

export type PendingQuestionGroup = {
  moduleFullSlug: string;
  moduleId: number;
  questions: PendingQuestion[];
};

export function groupPendingQuestionsByModule(questions: PendingQuestion[]): PendingQuestionGroup[] {
  const grouped = new Map<string, PendingQuestionGroup>();

  for (const question of questions) {
    const existing = grouped.get(question.module_full_slug);
    if (existing) {
      existing.questions.push(question);
      continue;
    }
    grouped.set(question.module_full_slug, {
      moduleFullSlug: question.module_full_slug,
      moduleId: question.module_id,
      questions: [question]
    });
  }

  return [...grouped.values()];
}
