import { findModuleNode } from './module-paths';
import { cloneImportRows } from './import-session';
import type { ModuleNode, QuestionImportResult, QuestionImportRowPayload, User } from './types';

const LEGACY_ACTIVE_USER_STORAGE_KEY = 'learning.active-user-id';
const LEGACY_ACTIVE_MODULE_STORAGE_KEY = 'learning.selected-module-id';
const IMPORT_SESSION_STORAGE_SUFFIX = 'import-drawer-session';

export interface ImportSessionSnapshot {
  targetModuleId: number;
  qmlText: string;
  rows: QuestionImportRowPayload[];
  result: QuestionImportResult | null;
}

export function storageKey(instanceKey: string, suffix: string): string {
  return `learning.${instanceKey}.${suffix}`;
}

function isQuestionImportRowPayload(value: unknown): value is QuestionImportRowPayload {
  return Boolean(
    value &&
      typeof value === 'object' &&
      typeof (value as QuestionImportRowPayload).row_number === 'number' &&
      typeof (value as QuestionImportRowPayload).qml_line === 'string'
  );
}

function normalizeImportRows(value: unknown): QuestionImportRowPayload[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter(isQuestionImportRowPayload)
    .map((row) => ({
      row_number: row.row_number,
      qml_line: row.qml_line
    }))
    .sort((left, right) => left.row_number - right.row_number);
}

function isQuestionImportResult(value: unknown): value is QuestionImportResult {
  const result = value as QuestionImportResult;
  return Boolean(
    value &&
      typeof value === 'object' &&
      Array.isArray(result.rows) &&
      Array.isArray(result.review_rows) &&
      typeof result.valid_row_count === 'number' &&
      typeof result.exact_duplicate_count === 'number' &&
      (result.committable_row_numbers === undefined || Array.isArray(result.committable_row_numbers))
  );
}

export function clearLegacySelectionStorage(storage: Storage): void {
  storage.removeItem(LEGACY_ACTIVE_USER_STORAGE_KEY);
  storage.removeItem(LEGACY_ACTIVE_MODULE_STORAGE_KEY);
}

export function clearImportSessionStorage(storage: Storage, instanceKey: string): void {
  storage.removeItem(storageKey(instanceKey, IMPORT_SESSION_STORAGE_SUFFIX));
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

export function persistImportSession(
  storage: Storage,
  {
    instanceKey,
    modules,
    open,
    targetModuleId,
    qmlText,
    rows,
    result
  }: {
    instanceKey: string;
    modules: ModuleNode[];
    open: boolean;
    targetModuleId: number | null;
    qmlText: string;
    rows: QuestionImportRowPayload[];
    result: QuestionImportResult | null;
  }
): void {
  if (!open || targetModuleId === null) {
    clearImportSessionStorage(storage, instanceKey);
    return;
  }

  const targetModule = findModuleNode(modules, targetModuleId);
  if (!targetModule) {
    clearImportSessionStorage(storage, instanceKey);
    return;
  }

  storage.setItem(
    storageKey(instanceKey, IMPORT_SESSION_STORAGE_SUFFIX),
    JSON.stringify({
      target_module_full_slug: targetModule.full_slug,
      qml_text: qmlText,
      rows: cloneImportRows(rows),
      result
    })
  );
}

export function restoreImportSession(
  storage: Storage,
  {
    instanceKey,
    modules
  }: {
    instanceKey: string;
    modules: ModuleNode[];
  }
): ImportSessionSnapshot | null {
  const rawValue = storage.getItem(storageKey(instanceKey, IMPORT_SESSION_STORAGE_SUFFIX));
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as {
      target_module_full_slug?: string;
      qml_text?: string;
      rows?: unknown;
      result?: unknown;
    };
    const targetModuleId = findModuleIdByFullSlug(modules, parsed.target_module_full_slug ?? null);
    if (targetModuleId === null) {
      clearImportSessionStorage(storage, instanceKey);
      return null;
    }

    const result = isQuestionImportResult(parsed.result) ? parsed.result : null;
    const rows = normalizeImportRows(parsed.rows);

    return {
      targetModuleId,
      qmlText: typeof parsed.qml_text === 'string' ? parsed.qml_text : '',
      rows: rows.length > 0 ? rows : result ? cloneImportRows(result.rows) : [],
      result
    };
  } catch {
    clearImportSessionStorage(storage, instanceKey);
    return null;
  }
}
