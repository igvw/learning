<script lang="ts">
  import type { ModuleNode } from '../lib/types';

  export let node: ModuleNode;
  export let depth = 0;
  export let selectedModuleId: number | null = null;
  export let onSelectLeaf: (moduleId: number) => void = () => {};

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

  function handleClick(): void {
    if (node.children.length > 0) {
      expanded = !branchOpen;
      return;
    }
    onSelectLeaf(node.id);
  }

  $: if (depth === 0 && selectedModuleId !== null && !branchContainsSelected(node, selectedModuleId)) {
    expanded = false;
  }
  $: branchOpen = expanded || branchContainsSelected(node, selectedModuleId);
</script>

<div class="editor-module-branch" role="presentation">
  <button
    type="button"
    class="editor-module-node"
    class:selected={selectedModuleId === node.id}
    class:branch={node.children.length > 0}
    style={`padding-left: ${0.9 + depth * 1.05}rem;`}
    aria-expanded={node.children.length > 0 ? branchOpen : undefined}
    on:click={handleClick}
  >
    <span class="editor-module-node-main">
      {#if node.children.length > 0}
        <span class="editor-module-caret" aria-hidden="true">{branchOpen ? '−' : '+'}</span>
      {/if}
      <span class="module-title">{node.title}</span>
    </span>
    {#if !node.admin_verified}
      <span class="inline-status-chip">Pending</span>
    {/if}
  </button>

  {#if node.children.length > 0 && branchOpen}
    <div class="editor-module-children">
      {#each node.children as child (child.id)}
        <svelte:self
          node={child}
          depth={depth + 1}
          selectedModuleId={selectedModuleId}
          onSelectLeaf={onSelectLeaf}
        />
      {/each}
    </div>
  {/if}
</div>
