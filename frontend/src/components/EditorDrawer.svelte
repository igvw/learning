<script lang="ts">
  import { buildQmlLine, QmlError } from '../lib/qml';
  import {
    buildEditorState,
    buildQuestionPayload,
    buildStructuredDraft,
    flattenModules,
    inlineBlankPlaceholder,
    inlineSegmentPlaceholder,
    inlineTailPlaceholder,
    multiSlotPlaceholder,
    parseEditorStateFromQml,
    promptPlaceholder,
    singleAnswerPlaceholder,
    type EditorState,
    type InlineBlank,
    type MultiSlot
  } from '../lib/editor-draft';
  import type {
    AuthActor,
    ModuleNode,
    QuestionDraftPayload,
    QuestionRow,
    QuestionType
  } from '../lib/types';

  export let open = false;
  export let modules: ModuleNode[] = [];
  export let defaultModuleId: number | null = null;
  export let editingQuestion: QuestionRow | null = null;
  export let saving = false;
  export let deleting = false;
  export let currentActor: AuthActor | null = null;
  export let onClose: () => void = () => {};
  export let onSave: (payload: QuestionDraftPayload, resetStats: boolean) => Promise<void> = async () => {
    throw new Error('Question save handler is not configured.');
  };
  export let onDelete: (questionId: number) => Promise<void> = async () => {
    throw new Error('Question delete handler is not configured.');
  };

  let prompt = '';
  let questionType: QuestionType = 'single_text';
  let rank = 1;
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

  function currentState(): EditorState {
    return {
      moduleId: Number(moduleId),
      prompt,
      questionType,
      rank,
      resetStats,
      singleAnswersText,
      multiSlots,
      inlineBlanks,
      inlineTail,
      qmlText
    };
  }

  function applyEditorState(nextState: EditorState): void {
    moduleId = nextState.moduleId;
    prompt = nextState.prompt;
    questionType = nextState.questionType;
    rank = nextState.rank;
    resetStats = nextState.resetStats;
    singleAnswersText = nextState.singleAnswersText;
    multiSlots = nextState.multiSlots;
    inlineBlanks = nextState.inlineBlanks;
    inlineTail = nextState.inlineTail;
    qmlText = nextState.qmlText;
  }

  function resetFromQuestion(question: QuestionRow | null): void {
    applyEditorState(buildEditorState(question, modules, defaultModuleId));
    qmlError = '';
    formError = '';
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

  function buildPayload(): QuestionDraftPayload {
    return buildQuestionPayload(currentState(), {
      selectedModuleIsLeaf
    });
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

  async function handleDelete(): Promise<void> {
    if (!editingQuestion) {
      return;
    }
    if (typeof window !== 'undefined') {
      const confirmed = window.confirm(
        isVerifiedNonAdminEdit
          ? 'Request deletion for this verified question?'
          : 'Delete this question and its progress history?'
      );
      if (!confirmed) {
        return;
      }
    }

    formError = '';
    try {
      await onDelete(editingQuestion.question_id);
    } catch (error) {
      formError = error instanceof Error ? error.message : 'Unable to delete this question.';
    }
  }

  function handleQmlInput(value: string): void {
    qmlText = value;
    try {
      const parsedState = parseEditorStateFromQml(value);
      prompt = parsedState.prompt;
      questionType = parsedState.questionType;
      singleAnswersText = parsedState.singleAnswersText;
      multiSlots = parsedState.multiSlots;
      inlineBlanks = parsedState.inlineBlanks;
      inlineTail = parsedState.inlineTail;
      qmlError = '';
    } catch (error) {
      qmlError = error instanceof QmlError ? error.message : 'Invalid QML.';
    }
  }

  $: moduleOptions = flattenModules(modules);
  $: selectedModuleOption = moduleOptions.find((option) => option.id === Number(moduleId)) ?? null;
  $: selectedModuleIsLeaf = selectedModuleOption?.isLeaf ?? false;
  $: editorBusy = saving || deleting;
  $: showDeleteAction = Boolean(editingQuestion);
  $: isAdmin = currentActor?.role === 'admin';
  $: isVerifiedNonAdminEdit = Boolean(editingQuestion && !isAdmin && editingQuestion.admin_verified);
  $: moduleSelectionLocked = isVerifiedNonAdminEdit;
  $: primaryActionLabel = saving ? 'Saving...' : editingQuestion ? 'Save Revision' : 'Create Question';
  $: deleteActionLabel = deleting
    ? isVerifiedNonAdminEdit
      ? 'Requesting...'
      : 'Deleting...'
    : isVerifiedNonAdminEdit
      ? 'Request Delete'
      : 'Delete Question';
  $: marker = `${open}:${editingQuestion?.question_id ?? 'new'}:${defaultModuleId ?? 'none'}:${moduleOptions.map((option) => option.id).join(',')}`;
  $: if (open && marker !== localMarker) {
    localMarker = marker;
    resetFromQuestion(editingQuestion);
  }
  $: if (open && !editingQuestion) {
    qmlText = buildQmlLine(
      buildStructuredDraft({
        prompt,
        questionType,
        singleAnswersText,
        multiSlots,
        inlineBlanks,
        inlineTail
      })
    );
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

        {#if isVerifiedNonAdminEdit}
          <div class="banner info">This is a personal revision proposal. Module placement and order stay global until an admin approves it.</div>
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
                  <select bind:value={moduleId} disabled={moduleSelectionLocked}>
                    {#each moduleOptions as option (option.id)}
                      <option value={option.id}>{option.label}</option>
                    {/each}
                  </select>
                </label>

                {#if !selectedModuleIsLeaf}
                  <p class="muted-copy editor-inline-note">Select a leaf module before saving this question.</p>
                {/if}

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

                <label class="field editor-field-prompt editor-field-wide">
                  <span>Prompt</span>
                  <textarea rows="3" bind:value={prompt} placeholder={promptPlaceholder(questionType, Boolean(editingQuestion))}></textarea>
                </label>
              </div>

              {#if editingQuestion && isAdmin}
                <label class="checkbox-field dense-checkbox-field">
                  <input type="checkbox" bind:checked={resetStats} />
                  <span>Reset stats for this revision</span>
                </label>
              {/if}

              {#if questionType === 'single_text' || questionType === 'computed_text'}
                <label class="field">
                  <span>{questionType === 'computed_text' ? 'Answer expression or accepted answers, one per line' : 'Accepted answers, one per line'}</span>
                  <textarea rows="5" bind:value={singleAnswersText} placeholder={singleAnswerPlaceholder(questionType, Boolean(editingQuestion))}></textarea>
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
                        <textarea rows="3" bind:value={slot.answersText} placeholder={multiSlotPlaceholder(questionType, index, Boolean(editingQuestion))}></textarea>
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
                          <input type="text" bind:value={blank.segmentBefore} placeholder={inlineSegmentPlaceholder(index, Boolean(editingQuestion))} />
                        </label>
                        <label class="field editor-field-wide">
                          <span>Accepted answers, one per line</span>
                          <textarea rows="3" bind:value={blank.answersText} placeholder={inlineBlankPlaceholder(index, Boolean(editingQuestion))}></textarea>
                        </label>
                      </div>
                    </div>
                  {/each}
                  <label class="field">
                    <span>Final trailing text</span>
                    <input type="text" bind:value={inlineTail} placeholder={inlineTailPlaceholder(Boolean(editingQuestion))} />
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
              {#if showDeleteAction}
                <button
                  class="danger-button"
                  type="button"
                  disabled={editorBusy}
                  on:click={() => void handleDelete()}
                >
                  {deleteActionLabel}
                </button>
              {/if}
              <button
                class="primary-button"
                type="button"
                disabled={editorBusy || (!editingQuestion && (!!qmlError || !selectedModuleIsLeaf))}
                on:click={() => void handleSave()}
              >
                {primaryActionLabel}
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
