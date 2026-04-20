<script lang="ts">
  import type { CreateModulePayload, ModuleNode, UpdateModulePayload } from '../../lib/types';
  import type { FlatModule } from '../../lib/module-tree';

  export let currentActorId: number | null = null;
  export let isAdmin = false;
  export let isDemo = false;
  export let mode: 'all' | 'modules' | 'import' | 'export' = 'all';
  export let showHeading = true;
  export let flatModules: FlatModule[] = [];
  export let selectedModuleId: number | null = null;
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
  let exportSaving = false;
  let exportError = '';
  let exportSuccess = '';
  let syncedLeafSignature = '';

  async function handleCreateModule(): Promise<void> {
    createError = '';
    createSuccess = '';
    createSaving = true;
    try {
      const created = await onCreateModule({
        title: createTitle.trim(),
        parent_id: createParentId ? Number(createParentId) : null,
        instruction: createInstruction.trim()
      });
      createSuccess = `${created.admin_verified ? 'Module ready' : 'Pending module ready'}: ${created.full_slug}.`;
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
      if (!selectedEditableLeafModule) {
        throw new Error('Select an editable leaf module first.');
      }
      const updated = await onUpdateModule(selectedEditableLeafModule.id, {
        title: editTitle.trim(),
        instruction: editInstruction.trim()
      });
      editSuccess = `${updated.admin_verified ? 'Module ready' : 'Pending module updated'}: ${updated.full_slug}.`;
    } catch (error) {
      editError = error instanceof Error ? error.message : 'Unable to update this module.';
    } finally {
      editSaving = false;
    }
  }

  function handleOpenImport(): void {
    if (importModuleId === null) {
      createError = 'Select a leaf module before importing.';
      return;
    }
    onOpenImport(Number(importModuleId));
  }

  async function handleExportContent(): Promise<void> {
    exportError = '';
    exportSuccess = '';
    exportSaving = true;
    try {
      await onExportContent();
      exportSuccess = 'Verified content export ready: modules-export.zip.';
    } catch (error) {
      exportError = error instanceof Error ? error.message : 'Unable to export verified content.';
    } finally {
      exportSaving = false;
    }
  }

  $: editableParentModules = isAdmin
    ? flatModules.filter((module) => !module.isLeaf)
    : flatModules.filter((module) => !module.isLeaf && module.admin_verified);
  $: showModuleSection = mode === 'all' || mode === 'modules';
  $: showExportSection = isAdmin && (mode === 'all' || mode === 'export');
  $: showImportSection = isAdmin && (mode === 'all' || mode === 'import');
  $: selectedModule = flatModules.find((module) => module.id === selectedModuleId) ?? null;
  $: selectedEditableLeafModule =
    selectedModule?.isLeaf && (isAdmin || (!!currentActorId && !selectedModule.admin_verified && selectedModule.created_by_user_id === currentActorId))
      ? selectedModule
      : null;
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
    const nextLeafSignature = selectedEditableLeafModule
      ? `${selectedEditableLeafModule.id}:${selectedEditableLeafModule.title}:${selectedEditableLeafModule.instruction}`
      : '';
    if (nextLeafSignature !== syncedLeafSignature) {
      syncedLeafSignature = nextLeafSignature;
      editTitle = selectedEditableLeafModule?.title ?? '';
      editInstruction = selectedEditableLeafModule?.instruction ?? '';
      editError = '';
      editSuccess = '';
    }
  }
</script>

{#if showModuleSection}
  <article class="panel admin-bar-panel">
    {#if showHeading}
      <div class="panel-header">
        <div><h3>{isAdmin ? 'Modules' : 'Pending modules'}</h3></div>
      </div>
    {/if}

    {#if editError}
      <div class="banner error">{editError}</div>
    {/if}
    {#if editSuccess}
      <div class="banner success">{editSuccess}</div>
    {/if}

    <div class="admin-bar-form module-bar-form">
      <div class="admin-wide-field">
        <h4>{isAdmin ? 'Selected leaf module' : 'Selected editable pending leaf'}</h4>
        {#if selectedEditableLeafModule}
          <p class="muted-copy">
            Current path: <code>{selectedEditableLeafModule.full_slug}</code>
          </p>
        {:else}
          <p class="muted-copy">
            {isAdmin
              ? 'Select a leaf module from the menu before renaming it.'
              : 'Select one of your own pending leaf modules from the menu before renaming it.'}
          </p>
        {/if}
      </div>

      <label class="field">
        <span>Module title</span>
        <input type="text" bind:value={editTitle} disabled={!selectedEditableLeafModule || editSaving || isDemo} />
      </label>

      <label class="field admin-wide-field">
        <span>Instruction</span>
        <textarea rows="4" bind:value={editInstruction} disabled={!selectedEditableLeafModule || editSaving || isDemo}></textarea>
      </label>

      <div class="admin-action-slot">
        <button class="primary-button" type="button" disabled={!selectedEditableLeafModule || editSaving || isDemo} on:click={() => void handleUpdateModule()}>
          {editSaving ? 'Saving...' : 'Save Module'}
        </button>
      </div>
    </div>

    {#if createError}
      <div class="banner error">{createError}</div>
    {/if}
    {#if createSuccess}
      <div class="banner success">{createSuccess}</div>
    {/if}

    <div class="admin-bar-form module-bar-form">
      <div class="admin-wide-field">
        <h4>{isAdmin ? 'Create module' : 'Create pending leaf module'}</h4>
      </div>
      <label class="field">
        <span>Module path</span>
        <input type="text" bind:value={createTitle} placeholder="norwegian/vocabulary/nouns_to_english" disabled={isDemo} />
      </label>
      <label class="field">
        <span>Parent module</span>
        <select bind:value={createParentId} disabled={isDemo}>
          <option value="">Top level</option>
          {#each editableParentModules as module}
            <option value={module.id}>{'\u00A0'.repeat(module.depth * 2)}{module.full_slug}</option>
          {/each}
        </select>
      </label>
      <label class="field admin-wide-field">
        <span>Instruction</span>
        <textarea rows="4" bind:value={createInstruction} disabled={isDemo}></textarea>
      </label>
      <div class="admin-action-slot">
        <button class="primary-button" type="button" disabled={createSaving || isDemo} on:click={() => void handleCreateModule()}>
          {createSaving ? 'Creating...' : 'Create Module'}
        </button>
      </div>
    </div>
  </article>
{/if}

{#if showExportSection}
  <article class="panel admin-bar-panel">
    {#if showHeading}
      <div class="panel-header">
        <div><h3>Export</h3></div>
      </div>
    {/if}
    {#if exportError}
      <div class="banner error">{exportError}</div>
    {/if}
    {#if exportSuccess}
      <div class="banner success">{exportSuccess}</div>
    {/if}
    <div class="admin-bar-form import-bar-form">
      <div class="admin-status-slot">
        <p class="muted-copy">
          Download the full verified module tree as a zip archive with <code>module.yaml</code> files and one <code>questions.qml</code> file per verified leaf.
        </p>
      </div>
      <div class="admin-action-slot">
        <button class="primary-button" type="button" disabled={exportSaving || isDemo} on:click={() => void handleExportContent()}>
          {exportSaving ? 'Exporting...' : 'Export content'}
        </button>
      </div>
    </div>
  </article>
{/if}

{#if showImportSection}
  <article class="panel admin-bar-panel">
    {#if showHeading}
      <div class="panel-header">
        <div><h3>Import</h3></div>
      </div>
    {/if}
    <div class="admin-bar-form import-bar-form">
      <label class="field">
        <span>Import target</span>
        <select bind:value={importModuleId} disabled={flatModules.length === 0 || isDemo}>
          {#if flatModules.length === 0}
            <option value={null}>No modules available</option>
          {:else}
            {#each flatModules.filter((module) => module.isLeaf) as module}
              <option value={module.id}>{module.full_slug}</option>
            {/each}
          {/if}
        </select>
      </label>
      <div class="admin-status-slot">
        {#if selectedImportModule}
          <p class="muted-copy">
            {selectedImportModule.admin_verified ? 'Verified module' : 'Pending module'}: <code>{selectedImportModule.full_slug}</code>
          </p>
        {/if}
      </div>
      <div class="admin-action-slot">
        <button class="primary-button" type="button" disabled={!selectedImportModule?.isLeaf || isDemo} on:click={handleOpenImport}>
          Import QML
        </button>
      </div>
    </div>
  </article>
{/if}
