<script lang="ts">
  import { autoGrow } from '../../lib/editor-autogrow';
  import { bundleQmlPlaceholder, type BundleVariantDraft } from '../../lib/editor-draft';

  export let bundleQml = '';
  export let bundleTemplate = '';
  export let variants: BundleVariantDraft[] = [];
  export let isEditing = false;
  export let onQmlChange: (value: string) => void = () => {};
  export let onAddVariant: () => void = () => {};
  export let onRemoveVariant: (index: number) => void = () => {};
  export let onPromptValueChange: (variantIndex: number, promptIndex: number, value: string) => void = () => {};
  export let onAnswersChange: (variantIndex: number, value: string) => void = () => {};
</script>

<label class="field">
  <span>Bundle QML</span>
  <textarea
    rows="1"
    class="editor-auto-field"
    use:autoGrow={{ maxMode: 'wide', value: bundleQml }}
    value={bundleQml}
    placeholder={bundleQmlPlaceholder(isEditing)}
    on:input={(event) => onQmlChange((event.currentTarget as HTMLTextAreaElement).value)}
  ></textarea>
</label>

{#if bundleTemplate && variants.length > 0}
  <div class="editor-answer-group">
    <div class="editor-row-toolbar">
      <h3>Bundle rows</h3>
      <button type="button" class="editor-icon-button add" aria-label="Add bundle row" on:click={onAddVariant}>+</button>
    </div>

    <div class="editor-inline-list">
      {#each variants as variant, variantIndex (variantIndex)}
        <div class="editor-answer-row bundle-row">
          <span class="editor-row-index">{variantIndex + 1}</span>
          {#each variant.promptValues as promptValue, promptIndex (promptIndex)}
            <textarea
              rows="1"
              class="editor-auto-field"
              aria-label={`Bundle row ${variantIndex + 1} parameter ${promptIndex + 1}`}
              use:autoGrow={{ value: promptValue }}
              value={promptValue}
              on:input={(event) =>
                onPromptValueChange(
                  variantIndex,
                  promptIndex,
                  (event.currentTarget as HTMLTextAreaElement).value
                )}
            ></textarea>
          {/each}
          <textarea
            rows="1"
            class="editor-auto-field"
            aria-label={`Bundle row ${variantIndex + 1} accepted answers`}
            use:autoGrow={{ value: variant.answersText }}
            value={variant.answersText}
            on:input={(event) => onAnswersChange(variantIndex, (event.currentTarget as HTMLTextAreaElement).value)}
          ></textarea>
          <button
            type="button"
            class="editor-icon-button remove"
            aria-label={`Remove bundle row ${variantIndex + 1}`}
            on:click={() => onRemoveVariant(variantIndex)}
          >
            ×
          </button>
        </div>
      {/each}
    </div>
  </div>
{/if}
