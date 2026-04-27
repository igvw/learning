import { findModuleNode } from './module-paths';
import type { ModuleNode } from './types';

export function storageKey(instanceKey: string, suffix: string): string {
  return `learning.${instanceKey}.${suffix}`;
}

export function routeFromPath(pathname: string): 'quiz' | 'stats' | 'admin' {
  if (pathname.startsWith('/stats')) {
    return 'stats';
  }
  if (pathname.startsWith('/admin')) {
    return 'admin';
  }
  return 'quiz';
}

export function moduleIdExists(nodes: ModuleNode[], moduleId: number): boolean {
  return findModuleNode(nodes, moduleId) !== null;
}

export function findModuleTitle(nodes: ModuleNode[], moduleId: number): string | null {
  return findModuleNode(nodes, moduleId)?.title ?? null;
}

export function findModuleIdByFullSlug(nodes: ModuleNode[], fullSlug: string | null): number | null {
  if (!fullSlug) {
    return null;
  }

  const stack = [...nodes];
  while (stack.length > 0) {
    const node = stack.pop();
    if (!node) {
      continue;
    }
    if (node.full_slug === fullSlug) {
      return node.id;
    }
    stack.push(...node.children);
  }
  return null;
}

export function persistSelectedModule(
  storage: Storage,
  {
    instanceKey,
    modules,
    moduleId
  }: {
    instanceKey: string;
    modules: ModuleNode[];
    moduleId: number | null;
  }
): void {
  const key = storageKey(instanceKey, 'selected-module-full-slug');
  if (moduleId === null) {
    storage.removeItem(key);
    return;
  }

  const module = findModuleNode(modules, moduleId);
  if (!module) {
    storage.removeItem(key);
    return;
  }
  storage.setItem(key, module.full_slug);
}

export function restoreSelectedModuleId(
  storage: Storage,
  {
    instanceKey,
    modules,
    selectedModuleId
  }: {
    instanceKey: string;
    modules: ModuleNode[];
    selectedModuleId: number | null;
  }
): number | null {
  if (modules.length === 0) {
    return null;
  }

  const savedModuleFullSlug = storage.getItem(storageKey(instanceKey, 'selected-module-full-slug'));
  const savedModuleId = findModuleIdByFullSlug(modules, savedModuleFullSlug);
  if (selectedModuleId !== null && moduleIdExists(modules, selectedModuleId)) {
    return selectedModuleId;
  }
  if (savedModuleId !== null && moduleIdExists(modules, savedModuleId)) {
    return savedModuleId;
  }
  return modules[0].id;
}
