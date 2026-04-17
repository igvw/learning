import { moduleIdExists, restoreSelectedModuleId } from './app-state';
import type {
  AuthActor,
  HealthResponse,
  ModerationQueue,
  ModuleNode,
  MyContributions,
  RouteName,
  StatsResponse,
  User
} from './types';

export function pathForRoute(route: RouteName): string {
  if (route === 'stats') {
    return '/stats';
  }
  if (route === 'admin') {
    return '/admin';
  }
  return '/quiz';
}

export async function resolveHealthContext(
  getHealth: () => Promise<HealthResponse>
): Promise<{ health: HealthResponse; instanceKey: string }> {
  try {
    const health = await getHealth();
    return {
      health,
      instanceKey: health?.instance_key?.trim() || 'default'
    };
  } catch (error) {
    console.error(error);
    return {
      health: { status: 'ok', instance_key: 'default', bootstrap_required: false },
      instanceKey: 'default'
    };
  }
}

export async function loadModulesForActor({
  actor,
  getModulesTree,
  selectedModuleId,
  importTargetModuleId,
  instanceKey,
  storage
}: {
  actor: AuthActor | null;
  getModulesTree: () => Promise<ModuleNode[]>;
  selectedModuleId: number | null;
  importTargetModuleId: number | null;
  instanceKey: string;
  storage: Storage;
}): Promise<{
  modules: ModuleNode[];
  selectedModuleId: number | null;
  importTargetModuleId: number | null;
}> {
  if (!actor) {
    return {
      modules: [],
      selectedModuleId: null,
      importTargetModuleId: null
    };
  }

  const modules = await getModulesTree();
  const nextImportTargetModuleId =
    importTargetModuleId !== null && !moduleIdExists(modules, importTargetModuleId) ? null : importTargetModuleId;
  if (modules.length === 0) {
    return {
      modules,
      selectedModuleId: null,
      importTargetModuleId: nextImportTargetModuleId
    };
  }

  return {
    modules,
    selectedModuleId: restoreSelectedModuleId(storage, {
      instanceKey,
      modules,
      selectedModuleId
    }),
    importTargetModuleId: nextImportTargetModuleId
  };
}

export async function loadRoleDataForActor({
  actor,
  getUsers,
  getModerationQueue,
  getMyContributions
}: {
  actor: AuthActor | null;
  getUsers: () => Promise<User[]>;
  getModerationQueue: () => Promise<ModerationQueue>;
  getMyContributions: () => Promise<MyContributions>;
}): Promise<{
  users: User[];
  moderationQueue: ModerationQueue | null;
  contributions: MyContributions | null;
}> {
  if (!actor || actor.is_demo) {
    return {
      users: [],
      moderationQueue: null,
      contributions: null
    };
  }

  if (actor.role === 'admin') {
    return {
      users: await getUsers(),
      moderationQueue: await getModerationQueue(),
      contributions: null
    };
  }

  return {
    users: [],
    moderationQueue: null,
    contributions: await getMyContributions()
  };
}

export async function loadStatsForActor({
  actor,
  selectedModuleId,
  getStats
}: {
  actor: AuthActor | null;
  selectedModuleId: number | null;
  getStats: (moduleId: number | null) => Promise<StatsResponse>;
}): Promise<{
  stats: StatsResponse | null;
  errorMessage: string;
}> {
  if (!actor) {
    return {
      stats: null,
      errorMessage: ''
    };
  }

  try {
    return {
      stats: await getStats(selectedModuleId),
      errorMessage: ''
    };
  } catch (error) {
    return {
      stats: null,
      errorMessage: error instanceof Error ? error.message : 'Unable to load stats.'
    };
  }
}
