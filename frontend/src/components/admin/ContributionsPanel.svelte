<script lang="ts">
  import { reviewBadge } from '../../lib/admin-page';
  import type { MyContributions } from '../../lib/types';

  export let contributions: MyContributions | null = null;
</script>

{#if contributions}
  <article class="panel admin-bar-panel">
    <div class="panel-header">
      <div><h3>My contributions</h3></div>
    </div>
    {#if contributions.modules.length === 0 && contributions.questions.length === 0 && contributions.revisions.length === 0}
      <p class="muted-copy">No pending submissions yet.</p>
    {/if}
    {#each contributions.modules as module (module.id)}
      <div class="dynamic-card compact-dynamic-card">
        <strong>{module.full_slug}</strong>
        <p class="muted-copy">{reviewBadge(module.moderation_status, module.admin_verified)}</p>
        {#if module.admin_review_note}
          <p class="muted-copy">{module.admin_review_note}</p>
        {/if}
      </div>
    {/each}
    {#each contributions.questions as question (question.question_id)}
      <div class="dynamic-card compact-dynamic-card">
        <strong>{question.prompt}</strong>
        <p class="muted-copy">{question.module_full_slug} · {reviewBadge(question.moderation_status, question.admin_verified)}</p>
        {#if question.admin_review_note}
          <p class="muted-copy">{question.admin_review_note}</p>
        {/if}
      </div>
    {/each}
    {#each contributions.revisions as revision (revision.proposal_id)}
      <div class="dynamic-card compact-dynamic-card">
        <strong>{revision.current_prompt}</strong>
        <p class="muted-copy">{revision.status}{revision.delete_requested ? ' · delete request' : ''}</p>
        {#if revision.admin_review_note}
          <p class="muted-copy">{revision.admin_review_note}</p>
        {/if}
      </div>
    {/each}
  </article>
{/if}
