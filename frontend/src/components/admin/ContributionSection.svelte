<script lang="ts">
  export let title = '';
  export let count = 0;
  export let emptyMessage = '';
</script>

<section class="panel contribution-section">
  <div class="panel-header">
    <div><h3>{title}</h3></div>
  </div>
  {#if count === 0}
    <p class="muted-copy">{emptyMessage}</p>
  {:else}
    <div class="contribution-list">
      <slot />
    </div>
  {/if}
</section>
