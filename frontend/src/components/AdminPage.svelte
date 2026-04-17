<script lang="ts">
  import AccountsPanel from './admin/AccountsPanel.svelte';
  import ContributionsPanel from './admin/ContributionsPanel.svelte';
  import ModerationQueuePanel from './admin/ModerationQueuePanel.svelte';
  import ModuleManagementPanel from './admin/ModuleManagementPanel.svelte';
  import { flattenModules } from '../lib/admin-page';
  import type {
    AuthActor,
    BulkModerationResult,
    CreateModulePayload,
    ModerationActionPayload,
    ModerationKind,
    ModerationQueue,
    ModuleNode,
    MyContributions,
    UpdateModulePayload,
    User
  } from '../lib/types';

  export let currentActor: AuthActor | null = {
    id: 1,
    handle: 'admin',
    display_name: 'Admin',
    role: 'admin',
    is_demo: false,
    created_at: null
  };
  export let modules: ModuleNode[] = [];
  export let users: User[] = [];
  export let selectedModuleId: number | null = null;
  export let moderationQueue: ModerationQueue | null = null;
  export let contributions: MyContributions | null = null;
  export let onCreateUser: (payload: {
    handle: string;
    display_name: string;
    role: 'admin' | 'user';
    password: string;
  }) => Promise<User> = async () => {
    throw new Error('User creation handler is not configured.');
  };
  export let onUpdateUserRole: (userId: number, role: 'admin' | 'user') => Promise<User> = async () => {
    throw new Error('User role update handler is not configured.');
  };
  export let onUpdateUserPassword: (userId: number, password: string) => Promise<void> = async () => {
    throw new Error('Password update handler is not configured.');
  };
  export let onCreateModule: (payload: CreateModulePayload) => Promise<ModuleNode> = async () => {
    throw new Error('Module creation handler is not configured.');
  };
  export let onUpdateModule: (moduleId: number, payload: UpdateModulePayload) => Promise<ModuleNode> = async () => {
    throw new Error('Module update handler is not configured.');
  };
  export let onOpenImport: (moduleId: number) => void = () => {};
  export let onModerationAction: (
    kind: ModerationKind,
    id: number,
    payload: ModerationActionPayload
  ) => Promise<void> = async () => {
    throw new Error('Moderation handler is not configured.');
  };
  export let onBulkQuestionModeration: (
    questionIds: number[],
    payload: ModerationActionPayload
  ) => Promise<BulkModerationResult> = async () => {
    throw new Error('Bulk moderation handler is not configured.');
  };

  $: isAdmin = currentActor?.role === 'admin';
  $: isDemo = currentActor?.role === 'demo';
  $: flatModules = flattenModules(modules);
</script>

<section class="page admin-page">
  <div class="page-intro">
    <div>
      <p class="eyebrow">{isAdmin ? 'Admin' : isDemo ? 'Demo' : 'Contributor'}</p>
      <h2>{isAdmin ? 'Catalog and moderation' : 'Contributions and pending content'}</h2>
    </div>
  </div>

  {#if isDemo}
    <div class="banner info">Demo mode shows the contribution workflow, but authoring actions do not save.</div>
  {/if}

  <div class="admin-stack">
    {#if isAdmin}
      <AccountsPanel
        users={users}
        isDemo={isDemo}
        onCreateUser={onCreateUser}
        onUpdateUserRole={onUpdateUserRole}
        onUpdateUserPassword={onUpdateUserPassword}
      />
    {/if}

    <ModuleManagementPanel
      currentActorId={currentActor?.id ?? null}
      isAdmin={isAdmin}
      isDemo={isDemo}
      flatModules={flatModules}
      selectedModuleId={selectedModuleId}
      onCreateModule={onCreateModule}
      onUpdateModule={onUpdateModule}
      onOpenImport={onOpenImport}
    />

    {#if isAdmin}
      <ModerationQueuePanel
        moderationQueue={moderationQueue}
        onModerationAction={onModerationAction}
        onBulkQuestionModeration={onBulkQuestionModeration}
      />
    {:else}
      <ContributionsPanel contributions={contributions} />
    {/if}
  </div>
</section>
