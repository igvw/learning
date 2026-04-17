import type { ModuleNode, PendingQuestion } from './types';

export type FlatModule = {
  id: number;
  title: string;
  full_slug: string;
  instruction: string;
  depth: number;
  isLeaf: boolean;
  admin_verified: boolean;
  created_by_user_id: number | null;
};

export type PendingQuestionGroup = {
  moduleFullSlug: string;
  moduleId: number;
  questions: PendingQuestion[];
};

export function flattenModules(nodes: ModuleNode[], depth = 0): FlatModule[] {
  return nodes.flatMap((node) => [
    {
      id: node.id,
      title: node.title,
      full_slug: node.full_slug,
      instruction: node.instruction,
      depth,
      isLeaf: node.children.length === 0,
      admin_verified: node.admin_verified,
      created_by_user_id: node.created_by_user_id
    },
    ...flattenModules(node.children, depth + 1)
  ]);
}

export function reviewBadge(status: string, verified: boolean): string {
  return verified ? 'Verified' : status.replace('_', ' ');
}

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
