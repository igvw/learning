<script lang="ts">
  import type {
    ModuleNode,
    QuestionDraftPayload,
    QuestionRow,
    QuestionType
  } from '../lib/types';

  type FlatModule = { id: number; label: string };
  type MultiSlot = { answersText: string };
  type InlineBlank = { segmentBefore: string; answersText: string };

  export let open = false;
  export let modules: ModuleNode[] = [];
  export let editingQuestion: QuestionRow | null = null;
  export let saving = false;
  export let onClose: () => void = () => {};
  export let onSave: (payload: QuestionDraftPayload, resetStats: boolean) => Promise<void> = async () => {
    throw new Error('Question save handler is not configured.');
  };

  let prompt = '';
  let questionType: QuestionType = 'single_text';
  let rank = 1;
  let moduleId = 0;
  let resetStats = true;
  let singleAnswersText = '';
  let multiSlots: MultiSlot[] = [];
  let inlineBlanks: InlineBlank[] = [];
  let inlineTail = '';
  let formError = '';
  let localMarker = '';

  function flattenModules(nodes: ModuleNode[], depth = 0): FlatModule[] {
    return nodes.flatMap((node) => [
      { id: node.id, label: node.full_slug },
      ...flattenModules(node.children, depth + 1)
    ]);
  }

  function splitLines(value: string): string[] {
    return value
      .split('\n')
      .map((entry) => entry.trim())
      .filter(Boolean);
  }

  function defaultModuleId(): number {
    return flattenModules(modules)[0]?.id ?? 0;
  }

  function resetFromQuestion(question: QuestionRow | null): void {
    const defaultId = question?.module_id ?? defaultModuleId();
    moduleId = defaultId;
    prompt = question?.prompt ?? '';
    questionType = question?.question_type ?? 'single_text';
    rank = question?.rank ?? 1;
    resetStats = true;
    formError = '';

    if (questionType === 'single_text') {
      singleAnswersText = (question?.accepted_answers?.[0] ?? []).join('\n');
      multiSlots = [];
      inlineBlanks = [];
      inlineTail = '';
      return;
    }

    if (questionType === 'multi_text' || questionType === 'ordered_multi') {
      singleAnswersText = '';
      multiSlots =
        question?.accepted_answers.map((answers) => ({
          answersText: answers.join('\n')
        })) ?? [
          { answersText: '' },
          { answersText: '' }
        ];
      inlineBlanks = [];
      inlineTail = '';
      return;
    }

    singleAnswersText = '';
    multiSlots = [];
    inlineBlanks =
      question?.accepted_answers.map((answers, index) => ({
        segmentBefore: question.segments[index] ?? '',
        answersText: answers.join('\n')
      })) ?? [{ segmentBefore: '', answersText: '' }];
    inlineTail = question?.segments?.[question?.segments.length - 1] ?? '';
  }

  function setQuestionType(type: QuestionType): void {
    questionType = type;
    if (type === 'single_text') {
      singleAnswersText ||= '';
      multiSlots = [];
      inlineBlanks = [];
      inlineTail = '';
      return;
    }
    if (type === 'multi_text' || type === 'ordered_multi') {
      multiSlots = multiSlots.length ? multiSlots : [{ answersText: '' }, { answersText: '' }];
      singleAnswersText = '';
      inlineBlanks = [];
      inlineTail = '';
      return;
    }
    inlineBlanks = inlineBlanks.length ? inlineBlanks : [{ segmentBefore: '', answersText: '' }];
    inlineTail ||= '';
    singleAnswersText = '';
    multiSlots = [];
  }

  function addMultiSlot(): void {
    multiSlots = [...multiSlots, { answersText: '' }];
  }

  function removeMultiSlot(index: number): void {
    if (multiSlots.length <= 1) {
      return;
    }
    multiSlots = multiSlots.filter((_, slotIndex) => slotIndex !== index);
  }

  function addInlineBlank(): void {
    inlineBlanks = [...inlineBlanks, { segmentBefore: '', answersText: '' }];
  }

  function removeInlineBlank(index: number): void {
    if (inlineBlanks.length <= 1) {
      return;
    }
    inlineBlanks = inlineBlanks.filter((_, blankIndex) => blankIndex !== index);
  }

  function buildPayload(): QuestionDraftPayload {
    if (!moduleId) {
      throw new Error('Select a module before saving.');
    }
    if (!prompt.trim()) {
      throw new Error('Prompt is required.');
    }

    if (questionType === 'single_text') {
      const answers = splitLines(singleAnswersText);
      if (answers.length === 0) {
        throw new Error('Add at least one accepted answer.');
      }
      return {
        module_id: moduleId,
        prompt: prompt.trim(),
        question_type: questionType,
        rank: Number(rank),
        accepted_answers: [answers],
        slot_prompts: [],
        segments: []
      };
    }

    if (questionType === 'multi_text' || questionType === 'ordered_multi') {
      const acceptedAnswers = multiSlots.map((slot) => splitLines(slot.answersText));
      if (acceptedAnswers.some((answers) => answers.length === 0)) {
        throw new Error('Each multi-answer slot needs at least one accepted answer.');
      }
      return {
        module_id: moduleId,
        prompt: prompt.trim(),
        question_type: questionType,
        rank: Number(rank),
        accepted_answers: acceptedAnswers,
        slot_prompts: [],
        segments: []
      };
    }

    const acceptedAnswers = inlineBlanks.map((blank) => splitLines(blank.answersText));
    if (acceptedAnswers.some((answers) => answers.length === 0)) {
      throw new Error('Each blank needs at least one accepted answer.');
    }
    return {
      module_id: moduleId,
      prompt: prompt.trim(),
      question_type: questionType,
      rank: Number(rank),
      accepted_answers: acceptedAnswers,
      slot_prompts: [],
      segments: [...inlineBlanks.map((blank) => blank.segmentBefore), inlineTail]
    };
  }

  async function handleSave(): Promise<void> {
    formError = '';
    try {
      const payload = buildPayload();
      await onSave(payload, resetStats);
    } catch (error) {
      formError = error instanceof Error ? error.message : 'Unable to save this question.';
    }
  }

  function formatSubmittedAnswer(values: string[]): string {
    const cleaned = values.map((value) => value.trim()).filter(Boolean);
    return cleaned.length ? cleaned.join(' | ') : 'No answer recorded';
  }

  $: moduleOptions = flattenModules(modules);
  $: selectedModuleLabel = moduleOptions.find((option) => option.id === moduleId)?.label ?? '';
  $: marker = `${open}:${editingQuestion?.question_id ?? 'new'}`;
  $: if (marker !== localMarker && open) {
    localMarker = marker;
    resetFromQuestion(editingQuestion);
  }
</script>

{#if open}
  <div class="drawer-backdrop" role="presentation" on:click={onClose}>
    <div class="drawer-panel-shell" role="presentation" on:click|stopPropagation>
      <aside class="drawer-panel" aria-label="Question editor">
        <div class="panel-header sticky">
          <div>
            <p class="eyebrow">{editingQuestion ? 'Revision flow' : 'Create flow'}</p>
            <h2>{editingQuestion ? 'Revise Question' : 'Create Question'}</h2>
          </div>
          <button type="button" class="ghost-button" on:click={onClose}>Close</button>
        </div>

        {#if formError}
          <div class="banner error">{formError}</div>
        {/if}

        <div class="editor-layout">
          <div class="editor-form">
            {#if editingQuestion && selectedModuleLabel}
              <div class="dynamic-card">
                <p class="eyebrow">Module path</p>
                <p><code>{selectedModuleLabel}</code></p>
              </div>
            {/if}

            {#if editingQuestion && editingQuestion.recent_incorrect_answers.length > 0}
              <div class="dynamic-group">
                <div class="subsection-header">
                  <h3>Previously incorrect answers</h3>
                </div>
                {#each editingQuestion.recent_incorrect_answers as attempt, index (attempt.answered_at + index)}
                  <div class="dynamic-card">
                    <p class="muted-copy">{new Date(attempt.answered_at).toLocaleString()}</p>
                    <p>{formatSubmittedAnswer(attempt.submitted_answer)}</p>
                  </div>
                {/each}
              </div>
            {/if}

            <label class="field">
              <span>Module</span>
              <select bind:value={moduleId}>
                {#each moduleOptions as option (option.id)}
                  <option value={option.id}>{option.label}</option>
                {/each}
              </select>
            </label>

            <label class="field">
              <span>Prompt</span>
              <textarea rows="3" bind:value={prompt}></textarea>
            </label>

            <div class="field-grid">
              <label class="field">
                <span>Question type</span>
                <select bind:value={questionType} on:change={(event) => setQuestionType((event.currentTarget as HTMLSelectElement).value as QuestionType)}>
                  <option value="single_text">Single text</option>
                  <option value="multi_text">Multi text (any order)</option>
                  <option value="ordered_multi">Ordered multi</option>
                  <option value="inline_cloze">Inline cloze</option>
                </select>
              </label>

              <label class="field">
                <span>Rank</span>
                <input type="number" min="1" step="1" bind:value={rank} />
              </label>
            </div>

            {#if editingQuestion}
              <label class="checkbox-field">
                <input type="checkbox" bind:checked={resetStats} />
                <span>Reset stats for this revision</span>
              </label>
            {/if}

            {#if questionType === 'single_text'}
              <label class="field">
                <span>Accepted answers, one per line</span>
                <textarea rows="6" bind:value={singleAnswersText}></textarea>
              </label>
            {:else if questionType === 'multi_text' || questionType === 'ordered_multi'}
              <div class="dynamic-group">
                <div class="subsection-header">
                  <h3>Required answer slots</h3>
                  <button type="button" class="ghost-button" on:click={addMultiSlot}>Add slot</button>
                </div>
                {#each multiSlots as slot, index (index)}
                  <div class="dynamic-card">
                    <div class="subsection-header">
                      <strong>Slot {index + 1}</strong>
                      <button type="button" class="ghost-button" on:click={() => removeMultiSlot(index)}>Remove</button>
                    </div>
                    <label class="field">
                      <span>Accepted answers, one per line</span>
                      <textarea rows="4" bind:value={slot.answersText}></textarea>
                    </label>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="dynamic-group">
                <div class="subsection-header">
                  <h3>Inline blanks</h3>
                  <button type="button" class="ghost-button" on:click={addInlineBlank}>Add blank</button>
                </div>
                {#each inlineBlanks as blank, index (index)}
                  <div class="dynamic-card">
                    <div class="subsection-header">
                      <strong>Blank {index + 1}</strong>
                      <button type="button" class="ghost-button" on:click={() => removeInlineBlank(index)}>Remove</button>
                    </div>
                    <label class="field">
                      <span>Text before blank {index + 1}</span>
                      <input type="text" bind:value={blank.segmentBefore} />
                    </label>
                    <label class="field">
                      <span>Accepted answers, one per line</span>
                      <textarea rows="4" bind:value={blank.answersText}></textarea>
                    </label>
                  </div>
                {/each}
                <label class="field">
                  <span>Final trailing text</span>
                  <input type="text" bind:value={inlineTail} />
                </label>
              </div>
            {/if}

            <div class="drawer-actions">
              <button class="primary-button" type="button" disabled={saving} on:click={() => void handleSave()}>
                {saving ? 'Saving...' : editingQuestion ? 'Save Revision' : 'Create Question'}
              </button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
{/if}
