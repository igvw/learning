<script lang="ts">
  import type { CreateModulePayload, ModuleNode, User } from '../lib/types';

  type FlatModule = {
    id: number;
    title: string;
    full_slug: string;
    instruction: string;
    depth: number;
    isLeaf: boolean;
  };

  export let modules: ModuleNode[] = [];
  export let users: User[] = [];
  export let activeUser: User | null = null;
  export let onCreateUser: (payload: { handle: string; display_name: string }) => Promise<User> = async () => {
    throw new Error('User creation handler is not configured.');
  };
  export let onCreateModule: (payload: CreateModulePayload) => Promise<ModuleNode> = async () => {
    throw new Error('Module creation handler is not configured.');
  };
  export let onOpenImport: (moduleId: number) => void = () => {};

  let userHandle = '';
  let userDisplayName = '';
  let userSaving = false;
  let userError = '';
  let userSuccess = '';

  let title = '';
  let parentId = '';
  let importModuleId: number | null = null;
  let instruction = '';
  let saving = false;
  let formError = '';
  let formSuccess = '';

  function flattenModules(nodes: ModuleNode[], depth = 0): FlatModule[] {
    return nodes.flatMap((node) => [
      {
        id: node.id,
        title: node.title,
        full_slug: node.full_slug,
        instruction: node.instruction,
        depth,
        isLeaf: node.children.length === 0
      },
      ...flattenModules(node.children, depth + 1)
    ]);
  }

  async function handleCreateUser(): Promise<void> {
    userError = '';
    userSuccess = '';
    userSaving = true;
    try {
      if (!userHandle.trim()) {
        throw new Error('User handle is required.');
      }
      if (!userDisplayName.trim()) {
        throw new Error('Display name is required.');
      }
      const created = await onCreateUser({
        handle: userHandle.trim(),
        display_name: userDisplayName.trim()
      });
      userSuccess = `User ready: ${created.display_name}.`;
      userHandle = '';
      userDisplayName = '';
    } catch (error) {
      userError = error instanceof Error ? error.message : 'Unable to create this user.';
    } finally {
      userSaving = false;
    }
  }

  async function handleCreateModule(): Promise<void> {
    formError = '';
    formSuccess = '';
    saving = true;
    try {
      if (!title.trim()) {
        throw new Error('Module title is required.');
      }
      const created = await onCreateModule({
        title: title.trim(),
        parent_id: parentId ? Number(parentId) : null,
        instruction: instruction.trim()
      });
      formSuccess = `Module path ready: ${created.full_slug}.`;
      title = '';
      instruction = '';
    } catch (error) {
      formError = error instanceof Error ? error.message : 'Unable to create this module.';
    } finally {
      saving = false;
    }
  }

  function handleOpenImport(): void {
    formError = '';
    formSuccess = '';
    if (importModuleId === null) {
      formError = 'Select a leaf module before importing.';
      return;
    }
    onOpenImport(importModuleId);
  }

  $: flatModules = flattenModules(modules);
  $: leafModules = flatModules.filter((module) => module.isLeaf);
  $: if (leafModules.length > 0 && !leafModules.some((module) => module.id === importModuleId)) {
    importModuleId = leafModules[0].id;
  }
  $: if (leafModules.length === 0) {
    importModuleId = null;
  }
</script>

<section class="page admin-page">
  <div class="page-intro">
    <div>
      <p class="eyebrow">Admin</p>
      <h2>Module Management</h2>
    </div>
  </div>

  {#if formError}
    <div class="banner error">{formError}</div>
  {/if}

  {#if formSuccess}
    <div class="banner success">{formSuccess}</div>
  {/if}

  <div class="admin-stack">
    <article class="panel admin-bar-panel">
      <div class="panel-header">
        <div>
          <p class="eyebrow">Create module</p>
          <h3>New module path</h3>
        </div>
      </div>

      <div class="admin-bar-form module-bar-form">
        <label class="field">
          <span>Module path</span>
          <input type="text" bind:value={title} placeholder="norwegian/vocabulary/nouns_to_english" />
        </label>

        <label class="field">
          <span>Parent module</span>
          <select bind:value={parentId}>
            <option value="">Top level</option>
            {#each flatModules as module}
              <option value={module.id}>
                {'\u00A0'.repeat(module.depth * 2)}{module.full_slug}
              </option>
            {/each}
          </select>
        </label>

        <label class="field admin-wide-field">
          <span>Instruction</span>
          <textarea
            rows="4"
            bind:value={instruction}
            placeholder="Translate each Norwegian noun into English."
          ></textarea>
        </label>

        <div class="admin-action-slot">
          <button class="primary-button" type="button" disabled={saving} on:click={() => void handleCreateModule()}>
            {saving ? 'Creating...' : 'Create Module'}
          </button>
        </div>
      </div>

      <div class="admin-bar-notes">
        <p class="muted-copy">
          Use <code>/</code> to create nested modules in one go. Existing segments are reused, like <code>mkdir -p</code>.
        </p>
        <p class="muted-copy">
          The optional parent acts as a base path, and child modules can only be added under modules that do not already contain direct questions.
        </p>
      </div>
    </article>

    <article class="panel admin-bar-panel">
      <div class="panel-header">
        <div>
          <p class="eyebrow">Users</p>
          <h3>Create user</h3>
        </div>
      </div>

      {#if userError}
        <div class="banner error">{userError}</div>
      {/if}

      {#if userSuccess}
        <div class="banner success">{userSuccess}</div>
      {/if}

      <div class="admin-bar-form user-bar-form">
        <label class="field">
          <span>Handle</span>
          <input type="text" bind:value={userHandle} placeholder="ignazio" />
        </label>

        <label class="field">
          <span>Display name</span>
          <input type="text" bind:value={userDisplayName} placeholder="Ignazio" />
        </label>

        <div class="admin-status-slot">
          {#if activeUser}
            <p class="muted-copy">Currently studying as <strong>{activeUser.display_name}</strong>.</p>
          {:else if users.length > 0}
            <p class="muted-copy">Pick an active user from the menu on the top right.</p>
          {:else}
            <p class="muted-copy">Create the first user here, then switch users from the menu on the top right.</p>
          {/if}
        </div>

        <div class="admin-action-slot">
          <button class="secondary-button" type="button" disabled={userSaving} on:click={() => void handleCreateUser()}>
            {userSaving ? 'Creating...' : 'Create User'}
          </button>
        </div>
      </div>
    </article>

    <article class="panel admin-bar-panel">
      <div class="panel-header">
        <div>
          <p class="eyebrow">Question import</p>
          <h3>Choose a leaf module</h3>
        </div>
      </div>

      <div class="admin-bar-form import-bar-form">
        <label class="field">
          <span>Import target</span>
          <select bind:value={importModuleId} disabled={leafModules.length === 0}>
            {#if leafModules.length === 0}
              <option value={null}>No leaf modules available</option>
            {:else}
              {#each leafModules as module}
                <option value={module.id}>{module.full_slug}</option>
              {/each}
            {/if}
          </select>
        </label>

        <div class="admin-status-slot">
          {#if importModuleId !== null}
            {@const selectedLeaf = leafModules.find((module) => module.id === importModuleId)}
            {#if selectedLeaf}
              <p class="muted-copy">Uploads will create questions directly in <code>{selectedLeaf.full_slug}</code>.</p>
              {#if selectedLeaf.instruction}
                <p class="muted-copy">{selectedLeaf.instruction}</p>
              {/if}
            {/if}
          {/if}
        </div>

        <div class="admin-action-slot">
          <button class="secondary-button" type="button" disabled={importModuleId === null} on:click={handleOpenImport}>
            Import CSV
          </button>
        </div>
      </div>
    </article>
  </div>
</section>
