<script lang="ts">
  import type { ModuleNode } from '../lib/types';

  export let node: ModuleNode;
  export let depth = 0;
  export let selectedModuleId: number | null = null;
  export let onSelect: (moduleId: number, keepMenuOpen?: boolean) => Promise<void> | void = () => {};

  let expanded = false;

  function branchContainsSelected(currentNode: ModuleNode, candidateId: number | null): boolean {
    if (candidateId === null) {
      return false;
    }
    if (currentNode.id === candidateId) {
      return true;
    }
    return currentNode.children.some((child) => branchContainsSelected(child, candidateId));
  }

  function handleNodeClick(): void {
    if (node.children.length > 0) {
      expanded = true;
      void onSelect(node.id, true);
      return;
    }
    void onSelect(node.id, false);
  }

  $: if (depth === 0 && selectedModuleId !== null && !branchContainsSelected(node, selectedModuleId)) {
    expanded = false;
  }
  $: branchOpen = expanded || branchContainsSelected(node, selectedModuleId);
</script>

<div class="module-branch" role="presentation">
  <button
    type="button"
    class="module-node"
    class:selected={selectedModuleId === node.id}
    style={`padding-left: ${1 + depth * 1.05}rem;`}
    aria-expanded={node.children.length > 0 ? branchOpen : undefined}
    on:click={handleNodeClick}
  >
    <span class="module-title">{node.title}</span>
    <span class="module-path">{node.full_slug}</span>
  </button>

  {#if node.children.length > 0 && branchOpen}
    <div class="module-children">
      {#each node.children as child (child.id)}
        <svelte:self
          node={child}
          depth={depth + 1}
          selectedModuleId={selectedModuleId}
          onSelect={onSelect}
        />
      {/each}
    </div>
  {/if}
</div>
