<script lang="ts">
  import { autoGrow } from '../../lib/editor-autogrow';
  import { multiSlotPlaceholder, type MultiSlot } from '../../lib/editor-draft';
  import type { QuestionType } from '../../lib/types';

  export let questionType: QuestionType = 'multi_text';
  export let slots: MultiSlot[] = [];
  export let isEditing = false;
  export let onAddSlot: () => void = () => {};
  export let onRemoveSlot: (index: number) => void = () => {};
  export let onSlotChange: (index: number, value: string) => void = () => {};
</script>

<div class="editor-answer-group">
  <div class="editor-row-toolbar">
    <h3>{questionType === 'multi_text' ? 'Answer slots' : 'Ordered slots'}</h3>
    <button type="button" class="editor-icon-button add" aria-label="Add answer slot" on:click={onAddSlot}>+</button>
  </div>

  <div class="editor-inline-list">
    {#each slots as slot, index (index)}
      <div class="editor-answer-row">
        <span class="editor-row-index">{index + 1}</span>
        <textarea
          rows="1"
          class="editor-auto-field"
          aria-label={`Slot ${index + 1} accepted answers`}
          use:autoGrow={{ value: slot.answersText }}
          value={slot.answersText}
          placeholder={multiSlotPlaceholder(questionType, index, isEditing)}
          on:input={(event) => onSlotChange(index, (event.currentTarget as HTMLTextAreaElement).value)}
        ></textarea>
        <button
          type="button"
          class="editor-icon-button remove"
          aria-label={`Remove slot ${index + 1}`}
          on:click={() => onRemoveSlot(index)}
        >
          ×
        </button>
      </div>
    {/each}
  </div>
</div>
