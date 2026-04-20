<script lang="ts">
  import { reviewBadge } from '../../lib/admin-page';
  import type { MyContributions, QuestionRevisionProposal } from '../../lib/types';
  import AdminSummaryCard from './AdminSummaryCard.svelte';
  import ModerationOverlay from './ModerationOverlay.svelte';
  import RevisionSnapshot from './RevisionSnapshot.svelte';

  export let contributions: MyContributions | null = null;

  let overlayOpen = false;
  let selectedRevision: QuestionRevisionProposal | null = null;

  $: moduleCount = contributions?.modules.length ?? 0;
  $: questionCount = contributions?.questions.length ?? 0;
  $: revisionCount = contributions?.revisions.length ?? 0;
  $: totalCount = moduleCount + questionCount + revisionCount;
  $: contributionDetail = `${moduleCount} modules · ${questionCount} uploads · ${revisionCount} revisions`;

  function closeOverlay(): void {
    overlayOpen = false;
    selectedRevision = null;
  }
</script>

<AdminSummaryCard
  title="My contributions"
  detail={contributionDetail}
  countLabel={String(totalCount)}
  wide={true}
  onClick={() => {
    overlayOpen = true;
  }}
/>

<ModerationOverlay
  open={overlayOpen}
  eyebrow=""
  title="My contributions"
  titleId="my-contributions-title"
  onClose={closeOverlay}
>
  {#if !contributions || totalCount === 0}
    <p class="muted-copy">No pending submissions yet.</p>
  {:else}
    <div class="moderation-overlay-stack">
      <section class="panel contribution-section">
        <div class="panel-header">
          <div><h3>Modules</h3></div>
        </div>
        {#if moduleCount === 0}
          <p class="muted-copy">No module submissions.</p>
        {:else}
          <div class="contribution-list">
            {#each contributions.modules as module (module.id)}
              <div class="dynamic-card compact-dynamic-card contribution-row">
                <strong>{module.full_slug}</strong>
                <p class="muted-copy">{reviewBadge(module.moderation_status, module.admin_verified)}</p>
                {#if module.admin_review_note}
                  <p class="muted-copy">{module.admin_review_note}</p>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </section>

      <section class="panel contribution-section">
        <div class="panel-header">
          <div><h3>Uploaded questions</h3></div>
        </div>
        {#if questionCount === 0}
          <p class="muted-copy">No uploaded questions.</p>
        {:else}
          <div class="contribution-list">
            {#each contributions.questions as question (question.question_id)}
              <div class="dynamic-card compact-dynamic-card contribution-row">
                <strong>{question.prompt}</strong>
                <p class="muted-copy">{question.module_full_slug}</p>
                <p class="muted-copy">{reviewBadge(question.moderation_status, question.admin_verified)}</p>
                {#if question.admin_review_note}
                  <p class="muted-copy">{question.admin_review_note}</p>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </section>

      <section class="panel contribution-section">
        <div class="panel-header">
          <div><h3>Revisions</h3></div>
        </div>
        {#if revisionCount === 0}
          <p class="muted-copy">No revisions.</p>
        {:else}
          <div class="contribution-list">
            {#each contributions.revisions as revision (revision.proposal_id)}
              <button
                type="button"
                class="dynamic-card compact-dynamic-card contribution-row contribution-revision-button"
                on:click={() => {
                  selectedRevision = revision;
                }}
              >
                <strong>{revision.module_full_slug}</strong>
                <p class="muted-copy">{reviewBadge(revision.status, false)}</p>
                {#if revision.admin_review_note}
                  <p class="muted-copy">{revision.admin_review_note}</p>
                {/if}
              </button>
            {/each}
          </div>
        {/if}
      </section>
    </div>
  {/if}
</ModerationOverlay>

<ModerationOverlay
  open={selectedRevision !== null}
  eyebrow=""
  title="Revision detail"
  titleId="contribution-revision-detail-title"
  onClose={() => {
    selectedRevision = null;
  }}
>
  {#if selectedRevision}
    <div class="moderation-overlay-stack">
      <div class="subsection-header contribution-revision-header">
        <div>
          <strong>{selectedRevision.module_full_slug}</strong>
          <p class="muted-copy">{reviewBadge(selectedRevision.status, false)}</p>
        </div>
      </div>
      <RevisionSnapshot proposal={selectedRevision} />
      {#if selectedRevision.admin_review_note}
        <div class="banner info">{selectedRevision.admin_review_note}</div>
      {/if}
    </div>
  {/if}
</ModerationOverlay>
