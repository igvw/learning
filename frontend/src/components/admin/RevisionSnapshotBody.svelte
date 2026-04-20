<script lang="ts">
  import { questionTypeLabel, revisionChangedFields } from '../../lib/revision-review';
  import type { QuestionRevisionProposal } from '../../lib/types';

  type SnapshotSide = 'current' | 'proposed';

  export let proposal: QuestionRevisionProposal;

  const snapshotSides: SnapshotSide[] = ['current', 'proposed'];

  function fieldChanged(field: 'question_type' | 'prompt' | 'answers' | 'segments'): boolean {
    return revisionChangedFields(proposal).includes(field);
  }

  function questionTypeFor(side: SnapshotSide): string {
    return side === 'current' ? proposal.current_question_type : proposal.proposed_question_type;
  }

  function promptFor(side: SnapshotSide): string {
    return side === 'current' ? proposal.current_prompt : proposal.proposed_prompt;
  }

  function acceptedAnswersFor(side: SnapshotSide): string[][] {
    return side === 'current' ? proposal.current_accepted_answers : proposal.proposed_accepted_answers;
  }

  function segmentsFor(side: SnapshotSide): string[] {
    return side === 'current' ? proposal.current_segments : proposal.proposed_segments;
  }

  function answerChipTone(side: SnapshotSide): 'old' | 'new' {
    return side === 'current' ? 'old' : 'new';
  }

  function sideLabel(side: SnapshotSide): string {
    return side === 'current' ? 'Current' : 'Proposed';
  }
</script>

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
    {#each snapshotSides as side (side)}
      {@const acceptedAnswers = acceptedAnswersFor(side)}
      {@const segments = segmentsFor(side)}
      <div class={`revision-snapshot-panel ${side}`}>
        <span class="revision-snapshot-side-label">{sideLabel(side)}</span>
        <div class="revision-snapshot-main">
          <span class={`revision-type-pill ${fieldChanged('question_type') ? 'changed' : ''}`}>
            {questionTypeLabel(questionTypeFor(side))}
          </span>
          <p class={`revision-prompt ${fieldChanged('prompt') ? 'changed' : ''}`}>
            {promptFor(side)}
          </p>
        </div>

        <div class={`revision-answer-groups ${fieldChanged('answers') ? 'changed' : ''}`}>
          {#each acceptedAnswers as group, groupIndex}
            <div class="answer-chip-row">
              {#if acceptedAnswers.length > 1}
                <span class="answer-block-label">Answer {groupIndex + 1}</span>
              {/if}
              {#each group as answer (`${side}:${proposal.proposal_id}:${groupIndex}:${answer}`)}
                <span class={`answer-block-chip revision-answer-chip ${answerChipTone(side)}`}>{answer}</span>
              {/each}
            </div>
          {/each}
        </div>

        {#if segments.length > 0}
          <div class={`revision-segment-list ${fieldChanged('segments') ? 'changed' : ''}`}>
            {#each segments as segment (`${side}-segment:${proposal.proposal_id}:${segment}`)}
              <code class="revision-segment-code">{segment}</code>
            {/each}
          </div>
        {/if}
      </div>
    {/each}
  </div>
{/if}
