<script lang="ts">
  import { reviewBadge } from '../../lib/moderation-display';
  import type { MyContributions } from '../../lib/types';
  import AdminSummaryCard from './AdminSummaryCard.svelte';
  import ContributionSection from './ContributionSection.svelte';
  import ModerationOverlay from './ModerationOverlay.svelte';

  export let contributions: MyContributions | null = null;

  let overlayOpen = false;

  $: moduleCount = contributions?.modules.length ?? 0;
  $: questionCount = contributions?.questions.length ?? 0;
  $: totalCount = moduleCount + questionCount;
  $: contributionDetail = `${moduleCount} modules · ${questionCount} uploads`;

  function closeOverlay(): void {
    overlayOpen = false;
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
      <ContributionSection title="Modules" count={moduleCount} emptyMessage="No module submissions.">
        {#each contributions.modules as module (module.id)}
          <div class="dynamic-card compact-dynamic-card contribution-row">
            <strong>{module.full_slug}</strong>
            <p class="muted-copy">{reviewBadge(module.moderation_status, module.admin_verified)}</p>
            {#if module.admin_review_note}
              <p class="muted-copy">{module.admin_review_note}</p>
            {/if}
          </div>
        {/each}
      </ContributionSection>

      <ContributionSection title="Uploaded questions" count={questionCount} emptyMessage="No uploaded questions.">
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
      </ContributionSection>
    </div>
  {/if}
</ModerationOverlay>
