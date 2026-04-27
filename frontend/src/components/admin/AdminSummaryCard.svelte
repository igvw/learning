<script lang="ts">
  export let title = '';
  export let detail = '';
  export let countLabel = '';
  export let wide = false;
  export let onClick: () => void = () => {};
</script>

<button
  type="button"
  class={`dynamic-card admin-summary-card ${wide ? 'wide' : ''}`}
  aria-haspopup="dialog"
  on:click={onClick}
>
  <div class="admin-summary-card-copy">
    <strong>{title}</strong>
    {#if detail}
      <span class="muted-copy">{detail}</span>
    {/if}
  </div>
  {#if countLabel}
    <span class="moderation-summary-count admin-summary-count">{countLabel}</span>
  {/if}
</button>
