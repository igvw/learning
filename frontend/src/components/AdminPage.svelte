<script lang="ts">
  import AccountsPanel from './admin/AccountsPanel.svelte';
  import AdminSummaryCard from './admin/AdminSummaryCard.svelte';
  import ContributionsPanel from './admin/ContributionsPanel.svelte';
  import ModerationOverlay from './admin/ModerationOverlay.svelte';
  import ModerationQueuePanel from './admin/ModerationQueuePanel.svelte';
  import ModuleManagementPanel from './admin/ModuleManagementPanel.svelte';
  import { flattenModules } from '../lib/module-tree';
  import type {
    AuthActor,
    BulkRevisionModerationItem,
    BulkModerationResult,
    CreateModulePayload,
    ModerationActionPayload,
    ModerationKind,
    ModerationRevisionActionPayload,
    ModerationQueue,
    ModuleNode,
    MyContributions,
    QuestionRevisionProposal,
    UpdateModulePayload,
    User
  } from '../lib/types';

  export let currentActor: AuthActor | null = {
    id: 1,
    handle: 'admin',
    display_name: 'Admin',
    role: 'admin',
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
  export let onExportContent: () => Promise<void> = async () => {
    throw new Error('Content export handler is not configured.');
  };
  export let onModerationAction: (
    kind: ModerationKind,
    id: number,
    payload: ModerationRevisionActionPayload
  ) => Promise<void> = async () => {
    throw new Error('Moderation handler is not configured.');
  };
  export let onDeleteRejectedModule: (moduleId: number) => Promise<void> = async () => {
    throw new Error('Rejected module delete handler is not configured.');
  };
  export let onBulkQuestionModeration: (
    questionIds: number[],
    payload: ModerationActionPayload
  ) => Promise<BulkModerationResult> = async () => {
    throw new Error('Bulk moderation handler is not configured.');
  };
  export let onBulkRevisionModeration: (
    items: BulkRevisionModerationItem[],
    payload: ModerationActionPayload
  ) => Promise<BulkModerationResult> = async () => {
    throw new Error('Bulk revision moderation handler is not configured.');
  };
  export let onOpenRevisionEditor: (proposal: QuestionRevisionProposal) => void = () => {};

  let openOverlay: 'accounts' | 'modules' | 'import' | 'export' | null = null;

  $: isAdmin = currentActor?.role === 'admin';
  $: flatModules = flattenModules(modules);
  $: selectedFlatModule = flatModules.find((module) => module.id === selectedModuleId) ?? null;
</script>

<section class="page admin-page">
  <div class="page-intro">
    <div>
      <p class="eyebrow">{isAdmin ? 'Admin' : 'Contributor'}</p>
      <h2>{isAdmin ? 'Catalog and moderation' : 'Contributions and pending content'}</h2>
    </div>
  </div>

  <div class="admin-stack">
    {#if isAdmin}
      <div class="admin-summary-grid">
        <AdminSummaryCard
          title="Accounts"
          detail={`${users.length} account${users.length === 1 ? '' : 's'}`}
          countLabel={String(users.length)}
          onClick={() => {
            openOverlay = 'accounts';
          }}
        />
        <AdminSummaryCard
          title="Modules"
          detail={`${flatModules.length} module${flatModules.length === 1 ? '' : 's'} in the tree`}
          countLabel={String(flatModules.length)}
          onClick={() => {
            openOverlay = 'modules';
          }}
        />
      </div>

      <div class="admin-summary-grid">
        <AdminSummaryCard
          title="Import"
          detail="Validate and commit QML into a verified leaf."
          onClick={() => {
            openOverlay = 'import';
          }}
        />
        <AdminSummaryCard
          title="Export"
          detail="Download the full verified module tree."
          onClick={() => {
            openOverlay = 'export';
          }}
        />
      </div>
    {:else}
      <div class="admin-summary-grid">
        <AdminSummaryCard
          title="Modules"
          detail={
            selectedFlatModule
              ? `Selected: ${selectedFlatModule.full_slug}`
              : `${flatModules.length} module${flatModules.length === 1 ? '' : 's'} available`
          }
          countLabel={String(flatModules.length)}
          onClick={() => {
            openOverlay = 'modules';
          }}
        />
      </div>
    {/if}

    {#if isAdmin}
      <ModerationQueuePanel
        moderationQueue={moderationQueue}
        onModerationAction={onModerationAction}
        onDeleteRejectedModule={onDeleteRejectedModule}
        onBulkQuestionModeration={onBulkQuestionModeration}
        onBulkRevisionModeration={onBulkRevisionModeration}
        onOpenRevisionEditor={onOpenRevisionEditor}
      />
    {:else}
      <ContributionsPanel contributions={contributions} />
    {/if}
  </div>
</section>

<ModerationOverlay
  open={openOverlay === 'accounts'}
  eyebrow=""
  title="Accounts"
  titleId="accounts-overlay-title"
  onClose={() => {
    openOverlay = null;
  }}
>
  <AccountsPanel
    users={users}
    showHeading={false}
    onCreateUser={onCreateUser}
    onUpdateUserRole={onUpdateUserRole}
    onUpdateUserPassword={onUpdateUserPassword}
  />
</ModerationOverlay>

<ModerationOverlay
  open={openOverlay === 'modules'}
  eyebrow=""
  title={isAdmin ? 'Modules' : 'Pending modules'}
  titleId="modules-overlay-title"
  onClose={() => {
    openOverlay = null;
  }}
>
  <ModuleManagementPanel
    currentActorId={currentActor?.id ?? null}
    isAdmin={isAdmin}
    mode="modules"
    showHeading={false}
    flatModules={flatModules}
    selectedModuleId={selectedModuleId}
    onCreateModule={onCreateModule}
    onUpdateModule={onUpdateModule}
    onOpenImport={onOpenImport}
    onExportContent={onExportContent}
  />
</ModerationOverlay>

<ModerationOverlay
  open={openOverlay === 'import'}
  eyebrow=""
  title="Import"
  titleId="import-overlay-title"
  onClose={() => {
    openOverlay = null;
  }}
>
  <ModuleManagementPanel
    currentActorId={currentActor?.id ?? null}
    isAdmin={isAdmin}
    mode="import"
    showHeading={false}
    flatModules={flatModules}
    selectedModuleId={selectedModuleId}
    onCreateModule={onCreateModule}
    onUpdateModule={onUpdateModule}
    onOpenImport={onOpenImport}
    onExportContent={onExportContent}
  />
</ModerationOverlay>

<ModerationOverlay
  open={openOverlay === 'export'}
  eyebrow=""
  title="Export"
  titleId="export-overlay-title"
  onClose={() => {
    openOverlay = null;
  }}
>
  <ModuleManagementPanel
    currentActorId={currentActor?.id ?? null}
    isAdmin={isAdmin}
    mode="export"
    showHeading={false}
    flatModules={flatModules}
    selectedModuleId={selectedModuleId}
    onCreateModule={onCreateModule}
    onUpdateModule={onUpdateModule}
    onOpenImport={onOpenImport}
    onExportContent={onExportContent}
  />
</ModerationOverlay>
