<script lang="ts">
  import StatsQuestionTable from './StatsQuestionTable.svelte';
  import type { QuestionRow } from '../lib/types';
  import {
    sortDefinitions,
    type SortDirection,
    type SortKey
  } from '../lib/stats/table';

  export let open = false;
  export let questions: QuestionRow[] = [];
  export let emptyMessage = 'No questions in this scope.';
  export let sortKey: SortKey | null = null;
  export let sortDirection: SortDirection = 'asc';
  export let onSort: (key: SortKey) => void = () => {};
  export let onOpenEdit: (question: QuestionRow) => void = () => {};
  export let onClose: () => void = () => {};

  function handleWindowKeydown(event: KeyboardEvent): void {
    if (open && event.key === 'Escape') {
      onClose();
    }
  }

  function handleOpenEdit(question: QuestionRow): void {
    onOpenEdit(question);
    onClose();
  }
</script>

<svelte:window on:keydown={handleWindowKeydown} />

{#if open}
  <div class="modal-backdrop stats-all-questions-backdrop" role="presentation" on:click={onClose}>
    <div class="modal-shell stats-all-questions-shell" role="presentation" on:click|stopPropagation>
      <div class="panel modal-panel stats-all-questions-panel" role="dialog" aria-modal="true" aria-labelledby="all-questions-title">
        <div class="panel-header sticky stats-all-questions-header">
          <div>
            <h2 id="all-questions-title">All questions</h2>
          </div>
          <button type="button" class="ghost-button" on:click={onClose}>Close</button>
        </div>

        {#if questions.length === 0}
          <p class="muted-copy">{emptyMessage}</p>
        {:else}
          <StatsQuestionTable
            questions={questions}
            definitions={sortDefinitions}
            sortKey={sortKey}
            sortDirection={sortDirection}
            onSort={onSort}
            onOpenEdit={handleOpenEdit}
          />
        {/if}
      </div>
    </div>
  </div>
{/if}
