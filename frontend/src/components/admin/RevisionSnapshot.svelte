<script lang="ts">
  import type { QuestionRevisionProposal } from '../../lib/types';
  import RevisionSnapshotBody from './RevisionSnapshotBody.svelte';

  export let proposal: QuestionRevisionProposal;
  export let interactive = false;
  export let disabled = false;
  export let ariaLabel = '';
  export let onClick: (() => void) | null = null;

  function handleClick(): void {
    if (interactive && !disabled) {
      onClick?.();
    }
  }
</script>

{#if interactive}
  <button
    type="button"
    class="revision-snapshot-button"
    aria-label={ariaLabel}
    disabled={disabled}
    on:click={handleClick}
  >
    <RevisionSnapshotBody {proposal} />
  </button>
{:else}
  <div class="revision-snapshot-static">
    <RevisionSnapshotBody {proposal} />
  </div>
{/if}
