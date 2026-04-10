<script lang="ts">
  import type { CreateModulePayload, ModuleNode, UpdateModulePayload, User } from '../lib/types';

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
  export let selectedModuleId: number | null = null;
  export let onCreateUser: (payload: { handle: string; display_name: string }) => Promise<User> = async () => {
    throw new Error('User creation handler is not configured.');
  };
  export let onCreateModule: (payload: CreateModulePayload) => Promise<ModuleNode> = async () => {
    throw new Error('Module creation handler is not configured.');
  };
  export let onUpdateModule: (moduleId: number, payload: UpdateModulePayload) => Promise<ModuleNode> = async () => {
    throw new Error('Module update handler is not configured.');
  };
  export let onOpenImport: (moduleId: number) => void = () => {};

  let userHandle = '';
  let userDisplayName = '';
  let userSaving = false;
  let userError = '';
  let userSuccess = '';

  let createTitle = '';
  let createParentId = '';
  let importModuleId: number | string | null = null;
  let createInstruction = '';
  let createSaving = false;
  let createError = '';
  let createSuccess = '';

  let editTitle = '';
  let editInstruction = '';
  let editSaving = false;
  let editError = '';
  let editSuccess = '';
  let syncedLeafSignature = '';

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
    createError = '';
    createSuccess = '';
    createSaving = true;
    try {
      if (!createTitle.trim()) {
        throw new Error('Module title is required.');
      }
      const created = await onCreateModule({
        title: createTitle.trim(),
        parent_id: createParentId ? Number(createParentId) : null,
        instruction: createInstruction.trim()
      });
      createSuccess = `Module path ready: ${created.full_slug}.`;
      createTitle = '';
      createInstruction = '';
    } catch (error) {
      createError = error instanceof Error ? error.message : 'Unable to create this module.';
    } finally {
      createSaving = false;
    }
  }

  async function handleUpdateModule(): Promise<void> {
    editError = '';
    editSuccess = '';
    editSaving = true;
    try {
      if (!selectedLeafModule) {
        throw new Error('Select a leaf module before updating it.');
      }
      if (!editTitle.trim()) {
        throw new Error('Module title is required.');
      }
      const updated = await onUpdateModule(selectedLeafModule.id, {
        title: editTitle.trim(),
        instruction: editInstruction.trim()
      });
      editSuccess = `Module ready: ${updated.full_slug}.`;
    } catch (error) {
      editError = error instanceof Error ? error.message : 'Unable to update this module.';
    } finally {
      editSaving = false;
    }
  }

  function handleOpenImport(): void {
    createError = '';
    createSuccess = '';
    editError = '';
    editSuccess = '';
    if (importModuleId === null) {
      createError = 'Select a leaf module before importing.';
      return;
    }
    onOpenImport(Number(importModuleId));
  }

  $: flatModules = flattenModules(modules);
  $: selectedModule = flatModules.find((module) => module.id === selectedModuleId) ?? null;
  $: selectedLeafModule = selectedModule?.isLeaf ? selectedModule : null;
  $: selectedImportModule = flatModules.find((module) => module.id === Number(importModuleId)) ?? null;
  $: if (flatModules.length > 0 && !flatModules.some((module) => module.id === Number(importModuleId))) {
    importModuleId =
      selectedModuleId !== null && flatModules.some((module) => module.id === selectedModuleId)
        ? selectedModuleId
        : flatModules[0].id;
  }
  $: if (flatModules.length === 0) {
    importModuleId = null;
  }
  $: {
    const nextLeafSignature = selectedLeafModule
      ? `${selectedLeafModule.id}:${selectedLeafModule.title}:${selectedLeafModule.instruction}`
      : '';
    if (nextLeafSignature !== syncedLeafSignature) {
      syncedLeafSignature = nextLeafSignature;
      editTitle = selectedLeafModule?.title ?? '';
      editInstruction = selectedLeafModule?.instruction ?? '';
      editError = '';
      editSuccess = '';
    }
  }
</script>

<section class="page admin-page">
  <div class="page-intro">
    <div>
      <p class="eyebrow">Admin</p>
      <h2>Module Management</h2>
    </div>
  </div>

  <div class="admin-stack">
    <article class="panel admin-bar-panel">
      <div class="panel-header">
        <div><h3>Module</h3></div>
      </div>

      {#if editError}
        <div class="banner error">{editError}</div>
      {/if}

      {#if editSuccess}
        <div class="banner success">{editSuccess}</div>
      {/if}

      <div class="admin-bar-form module-bar-form">
        <div class="admin-wide-field">
          <h4>Selected Leaf Module</h4>
          {#if selectedLeafModule}
            <p class="muted-copy">
              Renaming this leaf keeps its questions and progress in place. Current path:
              <code>{selectedLeafModule.full_slug}</code>
            </p>
          {:else if selectedModule}
            <p class="muted-copy">
              <code>{selectedModule.full_slug}</code> has child modules. Select a leaf module from the menu before renaming it.
            </p>
          {:else}
            <p class="muted-copy">Select a leaf module from the module menu before renaming it or updating its instruction.</p>
          {/if}
        </div>

        <label class="field">
          <span>Module title</span>
          <input type="text" bind:value={editTitle} placeholder="nouns_to_english" disabled={!selectedLeafModule || editSaving} />
        </label>

        <label class="field admin-wide-field">
          <span>Module instruction</span>
          <textarea
            rows="4"
            bind:value={editInstruction}
            placeholder="Translate each Norwegian noun into English."
            disabled={!selectedLeafModule || editSaving}
          ></textarea>
        </label>

        <div class="admin-action-slot">
          <button
            class="primary-button"
            type="button"
            disabled={!selectedLeafModule || editSaving}
            on:click={() => void handleUpdateModule()}
          >
            {editSaving ? 'Saving...' : 'Save Module'}
          </button>
        </div>
      </div>

      <div class="admin-bar-notes">
        <p class="muted-copy">Leaf module edits only rename the selected leaf segment. Parent paths stay unchanged.</p>
      </div>

      {#if createError}
        <div class="banner error">{createError}</div>
      {/if}

      {#if createSuccess}
        <div class="banner success">{createSuccess}</div>
      {/if}

      <div class="admin-bar-form module-bar-form">
        <div class="admin-wide-field">
          <h4>Create Module</h4>
        </div>

        <label class="field">
          <span>Module path</span>
          <input type="text" bind:value={createTitle} placeholder="norwegian/vocabulary/nouns_to_english" />
        </label>

        <label class="field">
          <span>Parent module</span>
          <select bind:value={createParentId}>
            <option value="">Top level</option>
            {#each flatModules as module}
              <option value={module.id}>
                {'\u00A0'.repeat(module.depth * 2)}{module.full_slug}
              </option>
            {/each}
          </select>
        </label>

        <label class="field admin-wide-field">
          <span>Create instruction</span>
          <textarea
            rows="4"
            bind:value={createInstruction}
            placeholder="Translate each Norwegian noun into English."
          ></textarea>
        </label>

        <div class="admin-action-slot">
          <button
            class="primary-button"
            type="button"
            disabled={createSaving}
            on:click={() => void handleCreateModule()}
          >
            {createSaving ? 'Creating...' : 'Create Module'}
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
        <div><h3>Create User</h3></div>
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
          <button class="primary-button" type="button" disabled={userSaving} on:click={() => void handleCreateUser()}>
            {userSaving ? 'Creating...' : 'Create User'}
          </button>
        </div>
      </div>
    </article>

    <article class="panel admin-bar-panel">
      <div class="panel-header">
        <div><h3>Import QML</h3></div>
      </div>

      <div class="admin-bar-form import-bar-form">
        <label class="field">
          <span>Import target</span>
          <select bind:value={importModuleId} disabled={flatModules.length === 0}>
            {#if flatModules.length === 0}
              <option value={null}>No modules available</option>
            {:else}
              {#each flatModules as module}
                <option value={module.id}>{module.full_slug}</option>
              {/each}
            {/if}
          </select>
        </label>

        <div class="admin-status-slot">
          {#if selectedImportModule}
            {#if selectedImportModule.isLeaf}
              <p class="muted-copy">Imports will create questions directly in <code>{selectedImportModule.full_slug}</code>.</p>
            {:else}
              <p class="muted-copy">Select a leaf module before importing QML.</p>
            {/if}
            {#if selectedImportModule.instruction}
              <p class="muted-copy">{selectedImportModule.instruction}</p>
            {/if}
          {/if}
        </div>

        <div class="admin-action-slot">
          <button class="primary-button" type="button" disabled={!selectedImportModule?.isLeaf} on:click={handleOpenImport}>
            Import QML
          </button>
        </div>
      </div>
    </article>
  </div>
</section>
