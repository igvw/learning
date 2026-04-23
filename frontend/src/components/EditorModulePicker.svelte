<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { ModuleNode } from '../lib/types';
  import EditorModuleTreeNode from './EditorModuleTreeNode.svelte';

  export let modules: ModuleNode[] = [];
  export let value = 0;
  export let disabled = false;
  export let selectedLabel = 'Select leaf module';
  export let labelId = '';

  const dispatch = createEventDispatcher<{ change: number }>();
  let open = false;
  let shell: HTMLDivElement | null = null;

  function toggleOpen(): void {
    if (disabled) {
      return;
    }
    open = !open;
  }

  function close(): void {
    open = false;
  }

  function handleSelectLeaf(moduleId: number): void {
    value = moduleId;
    dispatch('change', moduleId);
    open = false;
  }

  function handleWindowPointerDown(event: PointerEvent): void {
    if (!open || !shell) {
      return;
    }
    if (shell.contains(event.target as Node)) {
      return;
    }
    close();
  }

  function handleWindowKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      close();
    }
  }
</script>

<svelte:window on:pointerdown|capture={handleWindowPointerDown} on:keydown={handleWindowKeydown} />

<div class="editor-module-picker" bind:this={shell}>
  <button
    type="button"
    class="editor-module-trigger"
    aria-haspopup="dialog"
    aria-expanded={open}
    aria-labelledby={labelId || undefined}
    disabled={disabled}
    on:click={toggleOpen}
  >
    <span class="editor-module-trigger-label">{selectedLabel}</span>
    <span class="editor-module-trigger-caret" aria-hidden="true">{open ? '▴' : '▾'}</span>
  </button>

  {#if open}
    <div class="editor-module-popover" role="dialog" aria-label="Module selection tree">
      <div class="editor-module-tree">
        {#each modules as node (node.id)}
          <EditorModuleTreeNode node={node} selectedModuleId={value || null} onSelectLeaf={handleSelectLeaf} />
        {/each}
      </div>
    </div>
  {/if}
</div>
