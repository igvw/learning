<script lang="ts">
  import { autoGrow } from '../../lib/editor-autogrow';
  import { inlineQmlPlaceholder, type InlineBlank } from '../../lib/editor-draft';

  export let qmlText = '';
  export let blanks: InlineBlank[] = [];
  export let isEditing = false;
  export let onQmlChange: (value: string) => void = () => {};
  export let onBlankChange: (index: number, value: string) => void = () => {};
</script>

<label class="field">
  <span>QML</span>
  <textarea
    rows="1"
    class="editor-auto-field"
    use:autoGrow={{ maxMode: 'wide', value: qmlText }}
    value={qmlText}
    placeholder={inlineQmlPlaceholder(isEditing)}
    on:input={(event) => onQmlChange((event.currentTarget as HTMLTextAreaElement).value)}
  ></textarea>
</label>

{#if blanks.length > 0}
  <div class="editor-answer-group">
    <div class="editor-row-toolbar">
      <h3>Answer groups</h3>
    </div>

    <div class="editor-inline-list">
      {#each blanks as blank, index (index)}
        <div class="editor-answer-row">
          <span class="editor-row-index">{index + 1}</span>
          <textarea
            rows="1"
            class="editor-auto-field"
            aria-label={`Blank ${index + 1} accepted answers`}
            use:autoGrow={{ value: blank.answersText }}
            value={blank.answersText}
            placeholder={index === 0 ? 'heart' : index === 1 ? 'blood' : `answer ${index + 1}`}
            on:input={(event) => onBlankChange(index, (event.currentTarget as HTMLTextAreaElement).value)}
          ></textarea>
        </div>
      {/each}
    </div>
  </div>
{/if}
