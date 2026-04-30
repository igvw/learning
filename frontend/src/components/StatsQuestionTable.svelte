<script lang="ts">
  import type { QuestionRow } from '../lib/types';
  import { formatBucketLabel, formatLastSeen } from '../lib/stats/format';
  import {
    sortDefinitions as defaultSortDefinitions,
    sortQuestions,
    type SortDefinition,
    type SortDirection,
    type SortKey
  } from '../lib/stats/table';

  export let questions: QuestionRow[] = [];
  export let definitions: SortDefinition[] = defaultSortDefinitions;
  export let sortKey: SortKey | null = null;
  export let sortDirection: SortDirection = 'asc';
  export let onSort: (key: SortKey) => void = () => {};
  export let onOpenEdit: (question: QuestionRow) => void = () => {};

  function sortIndicator(candidateKey: SortKey): string {
    if (sortKey !== candidateKey) {
      return '';
    }
    return sortDirection === 'asc' ? ' ↑' : ' ↓';
  }

  $: sortedQuestions = sortQuestions(questions, sortKey, sortDirection);
</script>

<div class="table-shell">
  <table>
    <thead>
      <tr>
        {#each definitions as definition (definition.key)}
          <th>
            <button
              class="table-sort-button"
              type="button"
              on:click={() => onSort(definition.key)}
            >
              {definition.label}{sortIndicator(definition.key)}
            </button>
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each sortedQuestions as question (question.question_id)}
        <tr
          class:flagged-review={question.review_flag}
          class:hot0-row={!question.review_flag && question.schedule.bucket === 'hot0'}
          class:hot1-row={!question.review_flag && (question.schedule.bucket === 'hot1' || question.schedule.bucket === 'hot1_sit_out')}
          on:click={() => onOpenEdit(question)}
        >
          {#each definitions as definition (definition.key)}
            {#if definition.key === 'rank'}
              <td>{question.rank}</td>
            {:else if definition.key === 'prompt'}
              <td>
                <div class="question-cell">
                  <span>{question.prompt_preview}</span>
                  {#if !question.admin_verified}
                    <span class="inline-status-chip">Unverified</span>
                  {/if}
                </div>
              </td>
            {:else if definition.key === 'bucket'}
              <td>{formatBucketLabel(question)}</td>
            {:else if definition.key === 'last_seen'}
              <td>{formatLastSeen(question.last_asked_at)}</td>
            {:else if definition.key === 'attempts'}
              <td>{question.attempts}</td>
            {:else if definition.key === 'correct_percentage'}
              <td>{Math.round(question.correct_percentage * 100)}%</td>
            {/if}
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>
