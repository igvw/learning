<script lang="ts">
  import { autoGrow } from '../../lib/editor-autogrow';
  import { singleAnswerPlaceholder } from '../../lib/editor-draft';
  import type { QuestionType } from '../../lib/types';

  export let questionType: QuestionType = 'single_text';
  export let answersText = '';
  export let isEditing = false;
  export let onAnswersChange: (value: string) => void = () => {};
</script>

<div class="field editor-field-compact">
  <label class="field">
    <span>Accepted answers</span>
    <textarea
      rows="1"
      class="editor-auto-field"
      aria-describedby="single-answer-help"
      use:autoGrow={{ value: answersText }}
      value={answersText}
      placeholder={singleAnswerPlaceholder(questionType, isEditing)}
      on:input={(event) => onAnswersChange((event.currentTarget as HTMLTextAreaElement).value)}
    ></textarea>
  </label>
  <p class="editor-field-help" id="single-answer-help">Use <code>|</code> for alternatives. Answers are case-insensitive.</p>
</div>
