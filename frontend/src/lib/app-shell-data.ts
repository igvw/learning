import { clearLegacySelectionStorage, moduleIdExists, restoreSelectedModuleId } from './app-state';
import type { ImportUiState } from './app-shell-import';
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

export interface RefreshedShellState {
  modules: ModuleNode[];
  selectedModuleId: number | null;
  importTargetModuleId: number | null;
  users: User[];
  moderationQueue: ModerationQueue | null;
  contributions: MyContributions | null;
  stats: StatsResponse | null;
  statsErrorMessage: string;
}

export async function refreshAuthenticatedShellData({
  actor,
  currentRoute,
  selectedModuleId,
  importState,
  instanceKey,
  storage,
  getModulesTree,
  getUsers,
  getModerationQueue,
  getMyContributions,
  getStats
}: {
  actor: AuthActor | null;
  currentRoute: RouteName;
  selectedModuleId: number | null;
  importState: Pick<ImportUiState, 'targetModuleId'>;
  instanceKey: string;
  storage: Storage;
  getModulesTree: () => Promise<ModuleNode[]>;
  getUsers: () => Promise<User[]>;
  getModerationQueue: () => Promise<ModerationQueue>;
  getMyContributions: () => Promise<MyContributions>;
  getStats: (moduleId: number | null) => Promise<StatsResponse>;
}): Promise<RefreshedShellState> {
  const loadedModules = await loadModulesForActor({
    actor,
    getModulesTree,
    selectedModuleId,
    importTargetModuleId: importState.targetModuleId,
    instanceKey,
    storage
  });
  const roleData = await loadRoleDataForActor({
    actor,
    getUsers,
    getModerationQueue,
    getMyContributions
  });
  const loadedStats =
    currentRoute === 'stats'
      ? await loadStatsForActor({
          actor,
          selectedModuleId: loadedModules.selectedModuleId,
          getStats
        })
      : { stats: null, errorMessage: '' };

  return {
    modules: loadedModules.modules,
    selectedModuleId: loadedModules.selectedModuleId,
    importTargetModuleId: loadedModules.importTargetModuleId,
    users: roleData.users,
    moderationQueue: roleData.moderationQueue,
    contributions: roleData.contributions,
    stats: loadedStats.stats,
    statsErrorMessage: loadedStats.errorMessage
  };
}

export interface ResolvedAuthSessionState extends RefreshedShellState {
  health: HealthResponse;
  instanceKey: string;
  currentActor: AuthActor | null;
}

function emptyShellState(health: HealthResponse, instanceKey: string): ResolvedAuthSessionState {
  return {
    health,
    instanceKey,
    currentActor: null,
    modules: [],
    selectedModuleId: null,
    importTargetModuleId: null,
    users: [],
    moderationQueue: null,
    contributions: null,
    stats: null,
    statsErrorMessage: ''
  };
}

export async function resolveAuthSessionState({
  currentRoute,
  selectedModuleId,
  importState,
  storage,
  getHealth,
  getCurrentActor,
  getModulesTree,
  getUsers,
  getModerationQueue,
  getMyContributions,
  getStats
}: {
  currentRoute: RouteName;
  selectedModuleId: number | null;
  importState: Pick<ImportUiState, 'targetModuleId'>;
  storage: Storage;
  getHealth: () => Promise<HealthResponse>;
  getCurrentActor: () => Promise<AuthActor>;
  getModulesTree: () => Promise<ModuleNode[]>;
  getUsers: () => Promise<User[]>;
  getModerationQueue: () => Promise<ModerationQueue>;
  getMyContributions: () => Promise<MyContributions>;
  getStats: (moduleId: number | null) => Promise<StatsResponse>;
}): Promise<ResolvedAuthSessionState> {
  const healthContext = await resolveHealthContext(getHealth);
  clearLegacySelectionStorage(storage);

  try {
    const currentActor = await getCurrentActor();
    const refreshed = await refreshAuthenticatedShellData({
      actor: currentActor,
      currentRoute,
      selectedModuleId,
      importState,
      instanceKey: healthContext.instanceKey,
      storage,
      getModulesTree,
      getUsers,
      getModerationQueue,
      getMyContributions,
      getStats
    });

    return {
      health: healthContext.health,
      instanceKey: healthContext.instanceKey,
      currentActor,
      ...refreshed
    };
  } catch {
    return emptyShellState(healthContext.health, healthContext.instanceKey);
  }
}
