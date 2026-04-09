import type { CreateModulePayload, ModuleNode } from './types';

export function normalizeModuleTitleKey(value: string): string {
  return slugifyModuleSegment(value);
}

export function slugifyModuleSegment(value: string): string {
  return value
    .trim()
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

export function splitModulePath(value: string): string[] {
  return value
    .split('/')
    .map((segment) => segment.trim())
    .filter(Boolean);
}

export function findModuleNode(nodes: ModuleNode[], moduleId: number): ModuleNode | null {
  for (const node of nodes) {
    if (node.id === moduleId) {
      return node;
    }
    const child = findModuleNode(node.children, moduleId);
    if (child) {
      return child;
    }
  }
  return null;
}

export function findDirectChildModule(
  nodes: ModuleNode[],
  parentId: number | null,
  title: string
): ModuleNode | null {
  const siblings = parentId === null ? nodes : findModuleNode(nodes, parentId)?.children ?? [];
  const candidateKey = normalizeModuleTitleKey(title);
  return siblings.find((node) => normalizeModuleTitleKey(node.title) === candidateKey) ?? null;
}

type EnsureModulePathOptions = {
  modules: ModuleNode[];
  parentId: number | null;
  titlePath: string;
  instruction: string;
  createModule: (payload: CreateModulePayload) => Promise<ModuleNode>;
  reloadModules: () => Promise<ModuleNode[]>;
};

export async function ensureModulePath({
  modules,
  parentId,
  titlePath,
  instruction,
  createModule,
  reloadModules
}: EnsureModulePathOptions): Promise<ModuleNode> {
  const pathSegments = splitModulePath(titlePath);
  if (pathSegments.length === 0) {
    throw new Error('Module title is required.');
  }

  let workingModules = modules;
  let currentParentId = parentId;
  let finalModule: ModuleNode | null = null;

  for (const [index, segment] of pathSegments.entries()) {
    const isFinalSegment = index === pathSegments.length - 1;
    const existing = findDirectChildModule(workingModules, currentParentId, segment);
    if (existing) {
      finalModule = existing;
      currentParentId = existing.id;
      continue;
    }

    const created = await createModule({
      title: segment,
      parent_id: currentParentId,
      instruction: isFinalSegment ? instruction : ''
    });
    workingModules = await reloadModules();
    finalModule = findModuleNode(workingModules, created.id) ?? created;
    currentParentId = finalModule.id;
  }

  if (!finalModule) {
    throw new Error('Unable to resolve the created module path.');
  }
  return findModuleNode(workingModules, finalModule.id) ?? finalModule;
}
