<script lang="ts">
  import type { ModuleNode } from '../lib/types';
  import ModuleTreeItem from './ModuleTreeItem.svelte';

  export let open = false;
  export let modules: ModuleNode[] = [];
  export let selectedModuleId: number | null = null;
  export let selectedModuleLabel = 'All Modules';
  export let onClose: () => void = () => {};
  export let onSelect: (moduleId: number | null, keepMenuOpen?: boolean) => Promise<void> | void = () => {};
</script>

{#if open}
  <div class="menu-backdrop" role="presentation" on:click={onClose}>
    <div class="menu-panel-shell" role="presentation" on:click|stopPropagation>
      <aside class="menu-panel" aria-label="Module selection">
        <div class="menu-panel-header">
          <div>
            <p class="eyebrow">Study scope</p>
            <h2>{selectedModuleLabel}</h2>
          </div>
          <button type="button" class="ghost-button" on:click={onClose}>Close</button>
        </div>

        <div class="module-tree">
          {#each modules as node (node.id)}
            <ModuleTreeItem node={node} selectedModuleId={selectedModuleId} onSelect={onSelect} />
          {/each}
        </div>
      </aside>
    </div>
  </div>
{/if}
