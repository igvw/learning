<script lang="ts">
  import { buildQmlLine, parseQmlLine, QmlError } from '../lib/qml';
  import type {
    ModuleNode,
    PriorityMode,
    QuestionDraftPayload,
    QuestionRow,
    QuestionType
  } from '../lib/types';

  type FlatModule = { id: number; label: string; isLeaf: boolean };
  type MultiSlot = { answersText: string };
  type InlineBlank = { segmentBefore: string; answersText: string };

  export let open = false;
  export let modules: ModuleNode[] = [];
  export let defaultModuleId: number | null = null;
  export let editingQuestion: QuestionRow | null = null;
  export let saving = false;
  export let onClose: () => void = () => {};
  export let onSave: (payload: QuestionDraftPayload, resetStats: boolean) => Promise<void> = async () => {
    throw new Error('Question save handler is not configured.');
  };

  let prompt = '';
  let questionType: QuestionType = 'single_text';
  let rank = 1;
  let priorityMode: PriorityMode = 'mid';
  let moduleId: number | string = 0;
  let resetStats = true;
  let singleAnswersText = '';
  let multiSlots: MultiSlot[] = [];
  let inlineBlanks: InlineBlank[] = [];
  let inlineTail = '';
  let qmlText = '';
  let qmlError = '';
  let formError = '';
  let localMarker = '';

  function flattenModules(nodes: ModuleNode[]): FlatModule[] {
    return nodes.flatMap((node) => [
      { id: node.id, label: node.full_slug, isLeaf: node.children.length === 0 },
      ...flattenModules(node.children)
    ]);
  }

  function splitLines(value: string): string[] {
    return value
      .split('\n')
      .map((entry) => entry.trim())
      .filter(Boolean);
  }

  function defaultCreateModuleId(): number {
    const options = flattenModules(modules);
    if (defaultModuleId !== null && options.some((option) => option.id === defaultModuleId)) {
      return defaultModuleId;
    }
    return options[0]?.id ?? 0;
  }

  function structuredDraft() {
    if (questionType === 'single_text' || questionType === 'computed_text') {
      return {
        prompt: prompt.trim(),
        question_type: questionType,
        accepted_answers: [splitLines(singleAnswersText)],
        segments: []
      };
    }
    if (questionType === 'multi_text' || questionType === 'ordered_multi') {
      return {
        prompt: prompt.trim(),
        question_type: questionType,
        accepted_answers: multiSlots.map((slot) => splitLines(slot.answersText)),
        segments: []
      };
    }
    return {
      prompt: prompt.trim(),
      question_type: questionType,
      accepted_answers: inlineBlanks.map((blank) => splitLines(blank.answersText)),
      segments: [...inlineBlanks.map((blank) => blank.segmentBefore), inlineTail]
    };
  }

  function syncQmlFromStructured(): void {
    if (editingQuestion) {
      return;
    }
    qmlText = buildQmlLine(structuredDraft());
  }

  function applyParsedQml(value: string): void {
    const parsed = parseQmlLine(value);
    prompt = parsed.prompt;
    questionType = parsed.question_type;
    if (parsed.question_type === 'single_text' || parsed.question_type === 'computed_text') {
      singleAnswersText = (parsed.accepted_answers[0] ?? []).join('\n');
      multiSlots = [];
      inlineBlanks = [];
      inlineTail = '';
      return;
    }
    if (parsed.question_type === 'multi_text' || parsed.question_type === 'ordered_multi') {
      singleAnswersText = '';
      multiSlots = parsed.accepted_answers.map((answers) => ({ answersText: answers.join('\n') }));
      inlineBlanks = [];
      inlineTail = '';
      return;
    }
    singleAnswersText = '';
    multiSlots = [];
    inlineBlanks = parsed.accepted_answers.map((answers, index) => ({
      segmentBefore: parsed.segments[index] ?? '',
      answersText: answers.join('\n')
    }));
    inlineTail = parsed.segments[parsed.segments.length - 1] ?? '';
  }

  function resetFromQuestion(question: QuestionRow | null): void {
    moduleId = question?.module_id ?? defaultCreateModuleId();
    prompt = question?.prompt ?? '';
    questionType = question?.question_type ?? 'single_text';
    rank = question?.rank ?? 1;
    priorityMode = 'mid';
    resetStats = true;
    qmlError = '';
    formError = '';

    if (questionType === 'single_text' || questionType === 'computed_text') {
      singleAnswersText = (question?.accepted_answers?.[0] ?? []).join('\n');
      multiSlots = [];
      inlineBlanks = [];
      inlineTail = '';
    } else if (questionType === 'multi_text' || questionType === 'ordered_multi') {
      singleAnswersText = '';
      multiSlots =
        question?.accepted_answers.map((answers) => ({ answersText: answers.join('\n') })) ?? [
          { answersText: '' },
          { answersText: '' }
        ];
      inlineBlanks = [];
      inlineTail = '';
    } else {
      singleAnswersText = '';
      multiSlots = [];
      inlineBlanks =
        question?.accepted_answers.map((answers, index) => ({
          segmentBefore: question.segments[index] ?? '',
          answersText: answers.join('\n')
        })) ?? [{ segmentBefore: '', answersText: '' }];
      inlineTail = question?.segments?.[question.segments.length - 1] ?? '';
    }

    qmlText = buildQmlLine(structuredDraft());
  }

  function setQuestionType(type: QuestionType): void {
    questionType = type;
    if (type === 'single_text' || type === 'computed_text') {
      multiSlots = [];
      inlineBlanks = [];
      inlineTail = '';
      singleAnswersText ||= '';
      return;
    }
    if (type === 'multi_text' || type === 'ordered_multi') {
      singleAnswersText = '';
      multiSlots = multiSlots.length ? multiSlots : [{ answersText: '' }, { answersText: '' }];
      inlineBlanks = [];
      inlineTail = '';
      return;
    }
    singleAnswersText = '';
    multiSlots = [];
    inlineBlanks = inlineBlanks.length ? inlineBlanks : [{ segmentBefore: '', answersText: '' }];
    inlineTail ||= '';
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

  function createPlaceholder(value: string): string | undefined {
    return editingQuestion ? undefined : value;
  }

  function promptPlaceholder(type: QuestionType): string | undefined {
    switch (type) {
      case 'single_text':
        return createPlaceholder('What is the capital of Norway?');
      case 'multi_text':
        return createPlaceholder('Name the two rivers that meet at Khartoum.');
      case 'ordered_multi':
        return createPlaceholder('Name the stages in order.');
      case 'computed_text':
        return createPlaceholder(
          'Patient needs $m=[1-10]*100$ mg of trycoxigan. The solution has $v=[1-10]*10$ mg/ml. How much solution is needed?'
        );
      case 'inline_cloze':
        return createPlaceholder('The [Amazon | Amazon River] flows through South America.');
    }
  }

  function singleAnswerPlaceholder(type: QuestionType): string | undefined {
    if (type === 'computed_text') {
      return createPlaceholder('$m/v$ ml');
    }
    return createPlaceholder('oslo');
  }

  function multiSlotPlaceholder(type: QuestionType, index: number): string | undefined {
    if (editingQuestion) {
      return undefined;
    }
    if (type === 'multi_text') {
      return index === 0 ? 'white nile' : index === 1 ? 'blue nile' : `answer ${index + 1}`;
    }
    return index === 0 ? 'stage one' : index === 1 ? 'stage two' : `stage ${index + 1}`;
  }

  function inlineSegmentPlaceholder(index: number): string | undefined {
    return editingQuestion
      ? undefined
      : index === 0
        ? 'The derivative of '
        : ' is ';
  }

  function inlineBlankPlaceholder(index: number): string | undefined {
    return editingQuestion ? undefined : index === 0 ? 'x^2' : '2x';
  }

  function inlineTailPlaceholder(): string | undefined {
    return editingQuestion ? undefined : '.';
  }

  function buildPayload(): QuestionDraftPayload {
    const normalizedModuleId = Number(moduleId);
    if (!normalizedModuleId) {
      throw new Error('Select a module before saving.');
    }
    if (!selectedModuleIsLeaf) {
      throw new Error('Questions can only be created in leaf modules.');
    }
    const draft = structuredDraft();
    if (!draft.prompt) {
      throw new Error('Prompt is required.');
    }
    if (draft.accepted_answers.some((answers) => answers.length === 0)) {
      throw new Error('Every answer slot needs at least one accepted answer.');
    }
    return {
      module_id: normalizedModuleId,
      prompt: draft.prompt,
      question_type: draft.question_type,
      rank,
      priority_mode: editingQuestion ? null : priorityMode,
      accepted_answers: draft.accepted_answers,
      segments: draft.segments
    };
  }

  async function handleSave(): Promise<void> {
    formError = '';
    try {
      if (!editingQuestion && qmlError) {
        throw new Error('Fix the QML error before saving.');
      }
      await onSave(buildPayload(), resetStats);
    } catch (error) {
      formError = error instanceof Error ? error.message : 'Unable to save this question.';
    }
  }

  function handleQmlInput(value: string): void {
    qmlText = value;
    try {
      applyParsedQml(value);
      qmlError = '';
    } catch (error) {
      qmlError = error instanceof QmlError ? error.message : 'Invalid QML.';
    }
  }

  $: moduleOptions = flattenModules(modules);
  $: selectedModuleOption = moduleOptions.find((option) => option.id === Number(moduleId)) ?? null;
  $: selectedModuleIsLeaf = selectedModuleOption?.isLeaf ?? false;
  $: marker = `${open}:${editingQuestion?.question_id ?? 'new'}:${defaultModuleId ?? 'none'}:${moduleOptions.map((option) => option.id).join(',')}`;
  $: if (open && marker !== localMarker) {
    localMarker = marker;
    resetFromQuestion(editingQuestion);
  }
  $: if (open && !editingQuestion) {
    syncQmlFromStructured();
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

        {#if !editingQuestion && qmlError}
          <div class="banner error">{qmlError}</div>
        {/if}

        <div class="editor-layout">
          <div class="editor-form">
            <div class="editor-card">
              <div class="editor-card-grid">
                <label class="field editor-field-wide">
                  <span>Module</span>
                  <select bind:value={moduleId}>
                    {#each moduleOptions as option (option.id)}
                      <option value={option.id}>{option.label}</option>
                    {/each}
                  </select>
                </label>

                {#if !selectedModuleIsLeaf}
                  <p class="muted-copy editor-inline-note">Select a leaf module before saving this question.</p>
                {/if}

                {#if editingQuestion}
                  <label class="field">
                    <span>Question type</span>
                    <select
                      bind:value={questionType}
                      on:change={(event) => setQuestionType((event.currentTarget as HTMLSelectElement).value as QuestionType)}
                    >
                      <option value="single_text">Single text</option>
                      <option value="computed_text">Computed text</option>
                      <option value="multi_text">Multi text (any order)</option>
                      <option value="ordered_multi">Ordered multi</option>
                      <option value="inline_cloze">Inline cloze</option>
                    </select>
                  </label>

                  <label class="field editor-field-small">
                    <span>Rank</span>
                    <input type="number" min="1" step="1" bind:value={rank} />
                  </label>
                {:else}
                  <label class="field">
                    <span>Question type</span>
                    <select
                      bind:value={questionType}
                      on:change={(event) => setQuestionType((event.currentTarget as HTMLSelectElement).value as QuestionType)}
                    >
                      <option value="single_text">Single text</option>
                      <option value="computed_text">Computed text</option>
                      <option value="multi_text">Multi text (any order)</option>
                      <option value="ordered_multi">Ordered multi</option>
                      <option value="inline_cloze">Inline cloze</option>
                    </select>
                  </label>

                  <label class="field editor-field-small">
                    <span>Priority</span>
                    <select bind:value={priorityMode}>
                      <option value="high">High</option>
                      <option value="mid">Mid</option>
                      <option value="low">Low</option>
                    </select>
                  </label>
                {/if}

                <label class="field editor-field-prompt editor-field-wide">
                  <span>Prompt</span>
                  <textarea rows="3" bind:value={prompt} placeholder={promptPlaceholder(questionType)}></textarea>
                </label>
              </div>

              {#if editingQuestion}
                <label class="checkbox-field dense-checkbox-field">
                  <input type="checkbox" bind:checked={resetStats} />
                  <span>Reset stats for this revision</span>
                </label>
              {/if}

              {#if questionType === 'single_text' || questionType === 'computed_text'}
                <label class="field">
                  <span>{questionType === 'computed_text' ? 'Answer expression or accepted answers, one per line' : 'Accepted answers, one per line'}</span>
                  <textarea rows="5" bind:value={singleAnswersText} placeholder={singleAnswerPlaceholder(questionType)}></textarea>
                </label>
              {:else if questionType === 'multi_text' || questionType === 'ordered_multi'}
                <div class="dynamic-group compact-dynamic-group">
                  <div class="subsection-header">
                    <h3>Answer slots</h3>
                    <button type="button" class="ghost-button" on:click={addMultiSlot}>Add slot</button>
                  </div>
                  {#each multiSlots as slot, index (index)}
                    <div class="dynamic-card compact-dynamic-card">
                      <div class="subsection-header">
                        <strong>Slot {index + 1}</strong>
                        <button type="button" class="ghost-button" on:click={() => removeMultiSlot(index)}>Remove</button>
                      </div>
                      <label class="field">
                        <span>Accepted answers, one per line</span>
                        <textarea rows="3" bind:value={slot.answersText} placeholder={multiSlotPlaceholder(questionType, index)}></textarea>
                      </label>
                    </div>
                  {/each}
                </div>
              {:else}
                <div class="dynamic-group compact-dynamic-group">
                  <div class="subsection-header">
                    <h3>Inline blanks</h3>
                    <button type="button" class="ghost-button" on:click={addInlineBlank}>Add blank</button>
                  </div>
                  {#each inlineBlanks as blank, index (index)}
                    <div class="dynamic-card compact-dynamic-card">
                      <div class="subsection-header">
                        <strong>Blank {index + 1}</strong>
                        <button type="button" class="ghost-button" on:click={() => removeInlineBlank(index)}>Remove</button>
                      </div>
                      <div class="editor-card-grid">
                        <label class="field">
                          <span>Text before blank {index + 1}</span>
                          <input type="text" bind:value={blank.segmentBefore} placeholder={inlineSegmentPlaceholder(index)} />
                        </label>
                        <label class="field editor-field-wide">
                          <span>Accepted answers, one per line</span>
                          <textarea rows="3" bind:value={blank.answersText} placeholder={inlineBlankPlaceholder(index)}></textarea>
                        </label>
                      </div>
                    </div>
                  {/each}
                  <label class="field">
                    <span>Final trailing text</span>
                    <input type="text" bind:value={inlineTail} placeholder={inlineTailPlaceholder()} />
                  </label>
                </div>
              {/if}

              {#if !editingQuestion}
                <label class="field">
                  <span>QML</span>
                  <textarea rows="4" bind:value={qmlText} on:input={(event) => handleQmlInput((event.currentTarget as HTMLTextAreaElement).value)}></textarea>
                </label>
              {/if}
            </div>

            <div class="drawer-actions">
              <button
                class="primary-button"
                type="button"
                disabled={saving || (!editingQuestion && (!!qmlError || !selectedModuleIsLeaf))}
                on:click={() => void handleSave()}
              >
                {saving ? 'Saving...' : editingQuestion ? 'Save Revision' : 'Create Question'}
              </button>
            </div>

            {#if editingQuestion && editingQuestion.recent_incorrect_answers.length > 0}
              <div class="editor-card">
                <div class="subsection-header">
                  <h3>Previously incorrect answers</h3>
                </div>
                <div class="table-shell dense-table-shell">
                  <table class="dense-table">
                    <thead>
                      <tr>
                        <th>Answer</th>
                        <th>Count</th>
                        <th>Latest</th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each editingQuestion.recent_incorrect_answers as attempt (attempt.answer_text)}
                        <tr>
                          <td>{attempt.answer_text}</td>
                          <td>{attempt.count}</td>
                          <td>{new Date(attempt.latest_answered_at).toLocaleString()}</td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              </div>
            {/if}
          </div>
        </div>
      </aside>
    </div>
  </div>
{/if}
