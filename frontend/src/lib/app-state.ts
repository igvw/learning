import { findModuleNode } from './module-paths';
import type { ModuleNode, User } from './types';

const LEGACY_ACTIVE_USER_STORAGE_KEY = 'learning.active-user-id';
const LEGACY_ACTIVE_MODULE_STORAGE_KEY = 'learning.selected-module-id';

export function storageKey(instanceKey: string, suffix: string): string {
  return `learning.${instanceKey}.${suffix}`;
}

export function clearLegacySelectionStorage(storage: Storage): void {
  storage.removeItem(LEGACY_ACTIVE_USER_STORAGE_KEY);
  storage.removeItem(LEGACY_ACTIVE_MODULE_STORAGE_KEY);
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

export function findUser(users: User[], userId: number | null): User | null {
  if (userId === null) {
    return null;
  }
  return users.find((user) => user.id === userId) ?? null;
}

export function findUserIdByHandle(users: User[], handle: string | null): number | null {
  if (!handle) {
    return null;
  }
  return users.find((user) => user.handle === handle)?.id ?? null;
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

export function persistActiveUser(
  storage: Storage,
  {
    instanceKey,
    users,
    userId
  }: {
    instanceKey: string;
    users: User[];
    userId: number | null;
  }
): void {
  const key = storageKey(instanceKey, 'active-user-handle');
  if (userId === null) {
    storage.removeItem(key);
    return;
  }

  const user = findUser(users, userId);
  if (!user) {
    storage.removeItem(key);
    return;
  }
  storage.setItem(key, user.handle);
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

export function restoreActiveUserId(
  storage: Storage,
  {
    instanceKey,
    users,
    activeUserId
  }: {
    instanceKey: string;
    users: User[];
    activeUserId: number | null;
  }
): number | null {
  const currentUser = findUser(users, activeUserId);
  if (currentUser) {
    return currentUser.id;
  }

  const savedUserHandle = storage.getItem(storageKey(instanceKey, 'active-user-handle'));
  const savedUserId = findUserIdByHandle(users, savedUserHandle);
  if (savedUserId !== null && findUser(users, savedUserId)) {
    return savedUserId;
  }
  if (users.length > 0) {
    return users[0].id;
  }
  return null;
}
