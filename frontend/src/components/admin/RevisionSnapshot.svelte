<script lang="ts">
  import { questionTypeLabel, revisionChangedFields } from '../../lib/admin-page';
  import type { QuestionRevisionProposal } from '../../lib/types';

  export let proposal: QuestionRevisionProposal;
  export let interactive = false;
  export let disabled = false;
  export let ariaLabel = '';
  export let onClick: (() => void) | null = null;

  function fieldChanged(field: 'question_type' | 'prompt' | 'answers' | 'segments'): boolean {
    return revisionChangedFields(proposal).includes(field);
  }

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
    {#if proposal.delete_requested}
      <div class="revision-snapshot-panel current delete-only">
        <div class="revision-snapshot-main">
          <span class={`revision-type-pill ${fieldChanged('question_type') ? 'changed' : ''}`}>
            {questionTypeLabel(proposal.current_question_type)}
          </span>
          <p class={`revision-prompt ${fieldChanged('prompt') ? 'changed' : ''}`}>
            {proposal.current_prompt}
          </p>
        </div>

        <div class={`revision-answer-groups ${fieldChanged('answers') ? 'changed' : ''}`}>
          {#each proposal.current_accepted_answers as group, groupIndex}
            <div class="answer-chip-row">
              {#if proposal.current_accepted_answers.length > 1}
                <span class="answer-block-label">Answer {groupIndex + 1}</span>
              {/if}
              {#each group as answer (`delete:${proposal.proposal_id}:${groupIndex}:${answer}`)}
                <span class="answer-block-chip revision-answer-chip old">{answer}</span>
              {/each}
            </div>
          {/each}
        </div>

        {#if proposal.current_segments.length > 0}
          <div class={`revision-segment-list ${fieldChanged('segments') ? 'changed' : ''}`}>
            {#each proposal.current_segments as segment (`delete-segment:${proposal.proposal_id}:${segment}`)}
              <code class="revision-segment-code">{segment}</code>
            {/each}
          </div>
        {/if}
      </div>
    {:else}
      <div class="revision-snapshot-grid">
        <div class="revision-snapshot-panel current">
          <span class="revision-snapshot-side-label">Current</span>
          <div class="revision-snapshot-main">
            <span class={`revision-type-pill ${fieldChanged('question_type') ? 'changed' : ''}`}>
              {questionTypeLabel(proposal.current_question_type)}
            </span>
            <p class={`revision-prompt ${fieldChanged('prompt') ? 'changed' : ''}`}>
              {proposal.current_prompt}
            </p>
          </div>

          <div class={`revision-answer-groups ${fieldChanged('answers') ? 'changed' : ''}`}>
            {#each proposal.current_accepted_answers as group, groupIndex}
              <div class="answer-chip-row">
                {#if proposal.current_accepted_answers.length > 1}
                  <span class="answer-block-label">Answer {groupIndex + 1}</span>
                {/if}
                {#each group as answer (`old:${proposal.proposal_id}:${groupIndex}:${answer}`)}
                  <span class="answer-block-chip revision-answer-chip old">{answer}</span>
                {/each}
              </div>
            {/each}
          </div>

          {#if proposal.current_segments.length > 0}
            <div class={`revision-segment-list ${fieldChanged('segments') ? 'changed' : ''}`}>
              {#each proposal.current_segments as segment (`old-segment:${proposal.proposal_id}:${segment}`)}
                <code class="revision-segment-code">{segment}</code>
              {/each}
            </div>
          {/if}
        </div>

        <div class="revision-snapshot-panel proposed">
          <span class="revision-snapshot-side-label">Proposed</span>
          <div class="revision-snapshot-main">
            <span class={`revision-type-pill ${fieldChanged('question_type') ? 'changed' : ''}`}>
              {questionTypeLabel(proposal.proposed_question_type)}
            </span>
            <p class={`revision-prompt ${fieldChanged('prompt') ? 'changed' : ''}`}>
              {proposal.proposed_prompt}
            </p>
          </div>

          <div class={`revision-answer-groups ${fieldChanged('answers') ? 'changed' : ''}`}>
            {#each proposal.proposed_accepted_answers as group, groupIndex}
              <div class="answer-chip-row">
                {#if proposal.proposed_accepted_answers.length > 1}
                  <span class="answer-block-label">Answer {groupIndex + 1}</span>
                {/if}
                {#each group as answer (`new:${proposal.proposal_id}:${groupIndex}:${answer}`)}
                  <span class="answer-block-chip revision-answer-chip new">{answer}</span>
                {/each}
              </div>
            {/each}
          </div>

          {#if proposal.proposed_segments.length > 0}
            <div class={`revision-segment-list ${fieldChanged('segments') ? 'changed' : ''}`}>
              {#each proposal.proposed_segments as segment (`new-segment:${proposal.proposal_id}:${segment}`)}
                <code class="revision-segment-code">{segment}</code>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </button>
{:else}
  <div class="revision-snapshot-static">
    {#if proposal.delete_requested}
      <div class="revision-snapshot-panel current delete-only">
        <div class="revision-snapshot-main">
          <span class={`revision-type-pill ${fieldChanged('question_type') ? 'changed' : ''}`}>
            {questionTypeLabel(proposal.current_question_type)}
          </span>
          <p class={`revision-prompt ${fieldChanged('prompt') ? 'changed' : ''}`}>
            {proposal.current_prompt}
          </p>
        </div>

        <div class={`revision-answer-groups ${fieldChanged('answers') ? 'changed' : ''}`}>
          {#each proposal.current_accepted_answers as group, groupIndex}
            <div class="answer-chip-row">
              {#if proposal.current_accepted_answers.length > 1}
                <span class="answer-block-label">Answer {groupIndex + 1}</span>
              {/if}
              {#each group as answer (`delete:${proposal.proposal_id}:${groupIndex}:${answer}`)}
                <span class="answer-block-chip revision-answer-chip old">{answer}</span>
              {/each}
            </div>
          {/each}
        </div>

        {#if proposal.current_segments.length > 0}
          <div class={`revision-segment-list ${fieldChanged('segments') ? 'changed' : ''}`}>
            {#each proposal.current_segments as segment (`delete-segment:${proposal.proposal_id}:${segment}`)}
              <code class="revision-segment-code">{segment}</code>
            {/each}
          </div>
        {/if}
      </div>
    {:else}
      <div class="revision-snapshot-grid">
        <div class="revision-snapshot-panel current">
          <span class="revision-snapshot-side-label">Current</span>
          <div class="revision-snapshot-main">
            <span class={`revision-type-pill ${fieldChanged('question_type') ? 'changed' : ''}`}>
              {questionTypeLabel(proposal.current_question_type)}
            </span>
            <p class={`revision-prompt ${fieldChanged('prompt') ? 'changed' : ''}`}>
              {proposal.current_prompt}
            </p>
          </div>

          <div class={`revision-answer-groups ${fieldChanged('answers') ? 'changed' : ''}`}>
            {#each proposal.current_accepted_answers as group, groupIndex}
              <div class="answer-chip-row">
                {#if proposal.current_accepted_answers.length > 1}
                  <span class="answer-block-label">Answer {groupIndex + 1}</span>
                {/if}
                {#each group as answer (`old:${proposal.proposal_id}:${groupIndex}:${answer}`)}
                  <span class="answer-block-chip revision-answer-chip old">{answer}</span>
                {/each}
              </div>
            {/each}
          </div>

          {#if proposal.current_segments.length > 0}
            <div class={`revision-segment-list ${fieldChanged('segments') ? 'changed' : ''}`}>
              {#each proposal.current_segments as segment (`old-segment:${proposal.proposal_id}:${segment}`)}
                <code class="revision-segment-code">{segment}</code>
              {/each}
            </div>
          {/if}
        </div>

        <div class="revision-snapshot-panel proposed">
          <span class="revision-snapshot-side-label">Proposed</span>
          <div class="revision-snapshot-main">
            <span class={`revision-type-pill ${fieldChanged('question_type') ? 'changed' : ''}`}>
              {questionTypeLabel(proposal.proposed_question_type)}
            </span>
            <p class={`revision-prompt ${fieldChanged('prompt') ? 'changed' : ''}`}>
              {proposal.proposed_prompt}
            </p>
          </div>

          <div class={`revision-answer-groups ${fieldChanged('answers') ? 'changed' : ''}`}>
            {#each proposal.proposed_accepted_answers as group, groupIndex}
              <div class="answer-chip-row">
                {#if proposal.proposed_accepted_answers.length > 1}
                  <span class="answer-block-label">Answer {groupIndex + 1}</span>
                {/if}
                {#each group as answer (`new:${proposal.proposal_id}:${groupIndex}:${answer}`)}
                  <span class="answer-block-chip revision-answer-chip new">{answer}</span>
                {/each}
              </div>
            {/each}
          </div>

          {#if proposal.proposed_segments.length > 0}
            <div class={`revision-segment-list ${fieldChanged('segments') ? 'changed' : ''}`}>
              {#each proposal.proposed_segments as segment (`new-segment:${proposal.proposal_id}:${segment}`)}
                <code class="revision-segment-code">{segment}</code>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
{/if}
