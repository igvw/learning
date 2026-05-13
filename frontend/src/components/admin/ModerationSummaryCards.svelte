<script lang="ts">
  export let pendingModulesCount = 0;
  export let rejectedModulesCount = 0;
  export let pendingQuestionsCount = 0;
  export let onOpen: (kind: 'modules' | 'questions') => void = () => {};

  $: moduleModerationCount = pendingModulesCount + rejectedModulesCount;
  $: totalModerationCount = moduleModerationCount + pendingQuestionsCount;
</script>

<article class="panel admin-bar-panel">
  <div class="panel-header">
    <div>
      <h3>Moderation queue</h3>
      <p class="muted-copy">Open one category at a time so the admin page stays focused.</p>
    </div>
  </div>

  {#if totalModerationCount === 0}
    <p class="muted-copy">No moderation items right now.</p>
  {/if}

  <div class="moderation-summary-grid">
    <button
      type="button"
      class="dynamic-card moderation-summary-card"
      aria-haspopup="dialog"
      on:click={() => onOpen('modules')}
    >
      <strong>Modules</strong>
      <span class="moderation-summary-count">{moduleModerationCount}</span>
    </button>

    <button
      type="button"
      class="dynamic-card moderation-summary-card"
      aria-haspopup="dialog"
      on:click={() => onOpen('questions')}
    >
      <strong>Uploads</strong>
      <span class="moderation-summary-count">{pendingQuestionsCount}</span>
    </button>
  </div>
</article>
