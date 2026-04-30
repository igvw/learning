<script lang="ts">
  import type { CreateModulePayload, ModuleNode, UpdateModulePayload } from '../../lib/types';
  import type { FlatModule } from '../../lib/module-tree';

  export let currentActorId: number | null = null;
  export let isAdmin = false;
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
  export let onDeleteModule: (moduleId: number) => Promise<void> = async () => {
    throw new Error('Module delete handler is not configured.');
  };
  export let onOpenImport: (moduleId: number) => void = () => {};
  export let onExportContent: () => Promise<void> = async () => {
    throw new Error('Content export handler is not configured.');
  };

  let createTitle = '';
  let createPathPickerOpen = false;
  let createPathShell: HTMLElement | null = null;
  let importModuleId: number | string | null = null;
  let createSaving = false;
  let createError = '';
  let createSuccess = '';
  let editTitle = '';
  let editSaving = false;
  let editError = '';
  let editSuccess = '';
  let deleteSaving = false;
  let deleteError = '';
  let deleteSuccess = '';
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
        parent_id: null,
        instruction: ''
      });
      createSuccess = `${created.admin_verified ? 'Module ready' : 'Pending module ready'}: ${created.full_slug}.`;
      createTitle = '';
      createPathPickerOpen = false;
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
        instruction: ''
      });
      editSuccess = `${updated.admin_verified ? 'Module ready' : 'Pending module updated'}: ${updated.full_slug}.`;
    } catch (error) {
      editError = error instanceof Error ? error.message : 'Unable to update this module.';
    } finally {
      editSaving = false;
    }
  }

  async function handleDeleteModule(): Promise<void> {
    deleteError = '';
    deleteSuccess = '';
    if (!selectedDeletableModule) {
      deleteError = 'Select a module before deleting it.';
      return;
    }
    const confirmed = window.confirm(
      `Delete ${selectedDeletableModule.full_slug} and its unattempted descendants? This cannot be undone.`
    );
    if (!confirmed) {
      return;
    }
    deleteSaving = true;
    try {
      const deletedPath = selectedDeletableModule.full_slug;
      await onDeleteModule(selectedDeletableModule.id);
      deleteSuccess = `Deleted module: ${deletedPath}.`;
      editTitle = '';
    } catch (error) {
      deleteError = error instanceof Error ? error.message : 'Unable to delete this module.';
    } finally {
      deleteSaving = false;
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

  function handleWindowPointerDown(event: PointerEvent): void {
    if (!createPathPickerOpen || !createPathShell) {
      return;
    }
    if (createPathShell.contains(event.target as Node)) {
      return;
    }
    createPathPickerOpen = false;
  }

  function selectPathSuggestion(path: string): void {
    createTitle = path;
    createPathPickerOpen = false;
  }

  function filteredPathSuggestions(modules: FlatModule[], query: string): FlatModule[] {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    if (!normalizedQuery) {
      return modules;
    }
    return modules.filter((module) => module.full_slug.toLocaleLowerCase().includes(normalizedQuery));
  }

  $: showModuleSection = mode === 'all' || mode === 'modules';
  $: showExportSection = isAdmin && (mode === 'all' || mode === 'export');
  $: showImportSection = isAdmin && (mode === 'all' || mode === 'import');
  $: selectedModule = flatModules.find((module) => module.id === selectedModuleId) ?? null;
  $: selectedDeletableModule = isAdmin ? selectedModule : null;
  $: pathSuggestions = filteredPathSuggestions(flatModules, createTitle);
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
      ? `${selectedEditableLeafModule.id}:${selectedEditableLeafModule.title}`
      : '';
    if (nextLeafSignature !== syncedLeafSignature) {
      syncedLeafSignature = nextLeafSignature;
      editTitle = selectedEditableLeafModule?.title ?? '';
      editError = '';
      editSuccess = '';
    }
  }
</script>

<svelte:window on:pointerdown|capture={handleWindowPointerDown} />

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
    {#if deleteError}
      <div class="banner error">{deleteError}</div>
    {/if}
    {#if deleteSuccess}
      <div class="banner success">{deleteSuccess}</div>
    {/if}

    <div class="admin-bar-form module-bar-form">
      <div class="admin-wide-field">
        <h4>{isAdmin ? 'Selected module' : 'Selected editable pending leaf'}</h4>
        {#if selectedModule}
          <p class="muted-copy">
            Current path: <code>{selectedModule.full_slug}</code>
          </p>
          {#if !selectedEditableLeafModule}
            <p class="muted-copy">Only leaf modules can be renamed.</p>
          {/if}
        {:else}
          <p class="muted-copy">
            {isAdmin
              ? 'Select a module from the menu before renaming or deleting it.'
              : 'Select one of your own pending leaf modules from the menu before renaming it.'}
          </p>
        {/if}
      </div>

      <label class="field">
        <span>Module title</span>
        <input type="text" bind:value={editTitle} disabled={!selectedEditableLeafModule || editSaving} />
      </label>

      <div class="admin-action-slot module-action-buttons">
        <button class="primary-button" type="button" disabled={!selectedEditableLeafModule || editSaving} on:click={() => void handleUpdateModule()}>
          {editSaving ? 'Saving...' : 'Save Module'}
        </button>
        {#if isAdmin}
          <button
            class="danger-button"
            type="button"
            disabled={!selectedDeletableModule || deleteSaving}
            on:click={() => void handleDeleteModule()}
          >
            {deleteSaving ? 'Deleting...' : 'Delete Module'}
          </button>
        {/if}
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
      <label class="field module-path-create-field" bind:this={createPathShell}>
        <span>Module path</span>
        <input
          type="text"
          bind:value={createTitle}
          placeholder="norwegian/vocabulary/nouns_to_english"
          autocomplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={createPathPickerOpen}
          aria-controls="module-path-suggestions"
          on:focus={() => {
            createPathPickerOpen = true;
          }}
          on:input={() => {
            createPathPickerOpen = true;
          }}
        />
        {#if createPathPickerOpen}
          <div class="module-path-suggestions" id="module-path-suggestions" role="listbox" aria-label="Existing module paths">
            {#if pathSuggestions.length === 0}
              <p class="muted-copy module-path-empty">No matching module paths yet.</p>
            {:else}
              {#each pathSuggestions as module (module.id)}
                <button
                  type="button"
                  class="module-path-suggestion"
                  role="option"
                  aria-selected={module.full_slug === createTitle}
                  on:mousedown|preventDefault={() => selectPathSuggestion(module.full_slug)}
                >
                  <span>{module.full_slug}</span>
                  {#if !module.admin_verified}
                    <span class="inline-status-chip">Pending</span>
                  {/if}
                </button>
              {/each}
            {/if}
          </div>
        {/if}
        <p class="muted-copy module-path-help">Use a slash-separated full path. Existing segments are reused automatically.</p>
      </label>
      <div class="admin-action-slot">
        <button class="primary-button" type="button" disabled={createSaving} on:click={() => void handleCreateModule()}>
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
        <button class="primary-button" type="button" disabled={exportSaving} on:click={() => void handleExportContent()}>
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
        <select bind:value={importModuleId} disabled={flatModules.length === 0}>
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
        <button class="primary-button" type="button" disabled={!selectedImportModule?.isLeaf} on:click={handleOpenImport}>
          Import QML
        </button>
      </div>
    </div>
  </article>
{/if}
