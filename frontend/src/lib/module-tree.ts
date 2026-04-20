import type { ModuleNode } from './types';

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
