<script lang="ts">
  export let open = false;
  export let eyebrow = 'Moderation';
  export let title = 'Moderation';
  export let titleId = 'moderation-overlay-title';
  export let copy = '';
  export let onClose: () => void = () => {};

  function handleWindowKeydown(event: KeyboardEvent): void {
    if (open && event.key === 'Escape') {
      onClose();
    }
  }
</script>

<svelte:window on:keydown={handleWindowKeydown} />

{#if open}
  <div class="modal-backdrop moderation-overlay-backdrop" role="presentation" on:click={onClose}>
    <div class="modal-shell moderation-overlay-shell" role="presentation" on:click|stopPropagation>
      <div class="panel modal-panel moderation-overlay-panel" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div class="panel-header sticky moderation-overlay-header">
          <div>
            <p class="eyebrow">{eyebrow}</p>
            <h2 id={titleId}>{title}</h2>
          </div>
          <button type="button" class="ghost-button" on:click={onClose}>Close</button>
        </div>

        {#if copy}
          <p class="muted-copy moderation-overlay-copy">{copy}</p>
        {/if}

        <slot />
      </div>
    </div>
  </div>
{/if}
