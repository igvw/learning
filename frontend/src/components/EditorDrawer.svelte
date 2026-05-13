<script lang="ts">
  import { buildBundleEditorText, buildQmlLine, countBundlePromptValues, parseBundleEditorText, QmlError } from '../lib/qml';
  import { autoGrow } from '../lib/editor-autogrow';
  import {
    buildEditorState,
    buildQuestionPayload,
    buildStructuredDraft,
    defaultCreateModuleId,
    findModuleById,
    joinAnswerEditorText,
    parseEditorStateFromQml,
    promptPlaceholder,
    splitAnswerEditorText,
    type BundleVariantDraft,
    type EditorState,
    type InlineBlank,
    type MultiSlot
  } from '../lib/editor-draft';
  import type {
    AuthActor,
    ModuleNode,
    QuestionDraftPayload,
    QuestionRevisionProposal,
    QuestionRow,
    QuestionType
  } from '../lib/types';
  import BundleEditor from './editor/BundleEditor.svelte';
  import InlineClozeEditor from './editor/InlineClozeEditor.svelte';
  import MultiSlotEditor from './editor/MultiSlotEditor.svelte';
  import SingleTextEditor from './editor/SingleTextEditor.svelte';
  import EditorModulePicker from './EditorModulePicker.svelte';

  export let open = false;
  export let modules: ModuleNode[] = [];
  export let defaultModuleId: number | null = null;
  export let editingQuestion: QuestionRow | null = null;
  export let mode: 'standard' | 'moderation' = 'standard';
  export let saving = false;
  export let deleting = false;
  export let withdrawingRevision = false;
  export let currentActor: AuthActor | null = null;
  export let revisionProposal: QuestionRevisionProposal | null = null;
  export let onClose: () => void = () => {};
  export let onSave: (payload: QuestionDraftPayload, resetStats: boolean) => Promise<void> = async () => {
    throw new Error('Question save handler is not configured.');
  };
  export let onDelete: (questionId: number) => Promise<void> = async () => {
    throw new Error('Question delete handler is not configured.');
  };
  export let onWithdrawRevision: (questionId: number) => Promise<void> = async () => {
    throw new Error('Revision withdrawal handler is not configured.');
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
  let bundleTemplate = '';
  let bundleVariants: BundleVariantDraft[] = [];
  let bundleQml = '';
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
      bundleTemplate,
      bundleVariants,
      bundleQml,
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
    bundleTemplate = nextState.bundleTemplate;
    bundleVariants = nextState.bundleVariants;
    bundleQml = nextState.bundleQml;
    qmlText = nextState.qmlText;
  }

  function resetFromQuestion(question: QuestionRow | null): void {
    applyEditorState(buildEditorState(question, modules, defaultModuleId));
    qmlError = '';
    formError = '';
  }

  function setQuestionType(type: QuestionType): void {
    questionType = type;
    qmlError = '';
    if (type === 'bundle') {
      prompt = '';
      singleAnswersText = '';
      multiSlots = [];
      inlineBlanks = [];
      inlineTail = '';
      bundleTemplate = bundleTemplate || '';
      bundleVariants = bundleVariants.length ? bundleVariants : [];
      bundleQml ||= '';
      return;
    }
    bundleTemplate = '';
    bundleVariants = [];
    bundleQml = '';
    if (type === 'single_text') {
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
    prompt = '';
    singleAnswersText = '';
    multiSlots = [];
    inlineBlanks = [];
    inlineTail = '';
    qmlText = '';
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

  function updateSingleAnswers(value: string): void {
    singleAnswersText = value;
    qmlText = buildDerivedQmlText();
  }

  function updateMultiSlotAnswers(index: number, value: string): void {
    multiSlots = multiSlots.map((slot, slotIndex) => (slotIndex === index ? { answersText: value } : slot));
    qmlText = buildDerivedQmlText();
  }

  function updateInlineBlankAnswers(index: number, value: string): void {
    inlineBlanks = inlineBlanks.map((blank, blankIndex) => (blankIndex === index ? { ...blank, answersText: value } : blank));
    qmlText = buildDerivedQmlText();
  }

  function validatePlainQml(value: string): void {
    const parsedState = parseEditorStateFromQml(value);
    if (parsedState.questionType === 'inline_cloze' || parsedState.questionType === 'bundle') {
      throw new QmlError('Use the inline cloze or bundle editor for that QML shape.');
    }
    prompt = parsedState.prompt;
    questionType = parsedState.questionType;
    singleAnswersText = parsedState.singleAnswersText;
    multiSlots = parsedState.multiSlots;
    inlineBlanks = [];
    inlineTail = '';
    bundleTemplate = '';
    bundleVariants = [];
    bundleQml = '';
  }

  function handlePlainQmlInput(value: string): void {
    qmlText = value;
    try {
      validatePlainQml(value);
      qmlError = '';
    } catch (error) {
      qmlError = error instanceof QmlError ? error.message : 'Invalid QML.';
    }
  }

  function handleInlineQmlInput(value: string): void {
    qmlText = value;
    try {
      const parsedState = parseEditorStateFromQml(value);
      if (parsedState.questionType !== 'inline_cloze') {
        throw new QmlError('Inline cloze QML needs one or more bracketed answer groups.');
      }
      prompt = parsedState.prompt;
      questionType = 'inline_cloze';
      inlineBlanks = parsedState.inlineBlanks;
      inlineTail = parsedState.inlineTail;
      qmlError = '';
    } catch (error) {
      qmlError = error instanceof QmlError ? error.message : 'Invalid inline cloze QML.';
    }
  }

  function applyBundleStateFromQml(value: string): void {
    const parsed = parseBundleEditorText(value);
    bundleTemplate = parsed.template;
    bundleVariants = parsed.variants.map((variant) => ({
      promptValues: [...variant.prompt_values],
      answersText: joinAnswerEditorText(variant.accepted_answers)
    }));
  }

  function handleBundleQmlInput(value: string): void {
    bundleQml = value;
    try {
      applyBundleStateFromQml(value);
      qmlError = '';
    } catch (error) {
      bundleTemplate = '';
      bundleVariants = [];
      qmlError = error instanceof QmlError ? error.message : 'Invalid bundle QML.';
    }
  }

  function syncBundleQmlFromStructured(nextVariants: BundleVariantDraft[]): void {
    bundleVariants = nextVariants;
    bundleQml = buildBundleEditorText(
      bundleTemplate,
      nextVariants.map((variant) => ({
        prompt_values: variant.promptValues,
        accepted_answers: splitAnswerEditorText(variant.answersText)
      }))
    );
    try {
      parseBundleEditorText(bundleQml);
      qmlError = '';
    } catch (error) {
      qmlError = error instanceof QmlError ? error.message : 'Invalid bundle QML.';
    }
  }

  function addBundleVariant(): void {
    if (!bundleTemplate) {
      return;
    }
    const duplicated = bundleVariants[bundleVariants.length - 1];
    const nextVariant =
      duplicated
        ? { promptValues: [...duplicated.promptValues], answersText: duplicated.answersText }
        : {
            promptValues: Array.from({ length: countBundlePromptValues(bundleTemplate) }, () => ''),
            answersText: 'answer'
          };
    syncBundleQmlFromStructured([...bundleVariants, nextVariant]);
  }

  function removeBundleVariant(index: number): void {
    if (bundleVariants.length <= 1) {
      return;
    }
    syncBundleQmlFromStructured(bundleVariants.filter((_, variantIndex) => variantIndex !== index));
  }

  function updateBundlePromptValue(variantIndex: number, promptIndex: number, value: string): void {
    syncBundleQmlFromStructured(
      bundleVariants.map((variant, currentVariantIndex) =>
        currentVariantIndex === variantIndex
          ? {
              ...variant,
              promptValues: variant.promptValues.map((promptValue, currentPromptIndex) =>
                currentPromptIndex === promptIndex ? value : promptValue
              )
            }
          : variant
      )
    );
  }

  function updateBundleAnswers(variantIndex: number, value: string): void {
    syncBundleQmlFromStructured(
      bundleVariants.map((variant, currentVariantIndex) =>
        currentVariantIndex === variantIndex ? { ...variant, answersText: value } : variant
      )
    );
  }

  function buildPayload(): QuestionDraftPayload {
    return buildQuestionPayload(currentState(), {
      selectedModuleIsLeaf
    });
  }

  function buildDerivedQmlText(): string {
    if (questionType === 'single_text') {
      if (!prompt.trim() && !singleAnswersText.trim()) {
        return '';
      }
    } else if (questionType === 'multi_text' || questionType === 'ordered_multi') {
      if (!prompt.trim() && multiSlots.every((slot) => !slot.answersText.trim())) {
        return '';
      }
    } else if (questionType === 'inline_cloze') {
      if (inlineBlanks.length === 0 && !inlineTail.trim()) {
        return '';
      }
    }
    return buildQmlLine(
      buildStructuredDraft({
        prompt,
        questionType,
        singleAnswersText,
        multiSlots,
        inlineBlanks,
        inlineTail,
        bundleQml
      })
    );
  }

  async function handleSave(): Promise<void> {
    formError = '';
    try {
      if (qmlError) {
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

  async function handleWithdrawRevision(): Promise<void> {
    if (!editingQuestion) {
      return;
    }
    if (typeof window !== 'undefined') {
      const confirmed = window.confirm('Remove this pending review item and return the original question to quiz rotation?');
      if (!confirmed) {
        return;
      }
    }

    formError = '';
    try {
      await onWithdrawRevision(editingQuestion.question_id);
    } catch (error) {
      formError = error instanceof Error ? error.message : 'Unable to remove this review item.';
    }
  }

  $: selectedModuleNode = findModuleById(modules, Number(moduleId));
  $: selectedModuleIsLeaf = selectedModuleNode?.children.length === 0;
  $: selectedModuleLabel = selectedModuleNode ? `.../${selectedModuleNode.title}` : 'Select leaf module';
  $: editorBusy = saving || deleting || withdrawingRevision;
  $: showDeleteAction = Boolean(editingQuestion) && mode !== 'moderation';
  $: showWithdrawAction = Boolean(editingQuestion && revisionProposal && revisionProposal.status === 'pending' && mode !== 'moderation');
  $: isAdmin = currentActor?.role === 'admin';
  $: isVerifiedNonAdminEdit = Boolean(editingQuestion && !isAdmin && editingQuestion.admin_verified);
  $: moduleSelectionLocked = mode === 'moderation' || isVerifiedNonAdminEdit;
  $: primaryActionLabel = saving
    ? mode === 'moderation'
      ? 'Approving...'
      : 'Saving...'
    : mode === 'moderation'
      ? 'Approve Revision'
      : editingQuestion
        ? 'Save Revision'
        : 'Create Question';
  $: deleteActionLabel = deleting
    ? isVerifiedNonAdminEdit
      ? 'Requesting...'
      : 'Deleting...'
    : isVerifiedNonAdminEdit
      ? 'Request Delete'
      : 'Delete Question';
  $: withdrawActionLabel = withdrawingRevision ? 'Removing...' : 'Remove from review';
  $: marker = `${open}:${editingQuestion?.question_id ?? 'new'}:${revisionProposal?.proposal_id ?? 'none'}:${defaultModuleId ?? 'none'}:${modules.map((module) => module.id).join(',')}`;
  $: if (open && marker !== localMarker) {
    localMarker = marker;
    resetFromQuestion(editingQuestion);
  }
  $: if (open && !editingQuestion && modules.length > 0) {
    const currentModuleNode = findModuleById(modules, Number(moduleId));
    if (currentModuleNode?.children.length !== 0) {
      const fallbackModuleId = defaultCreateModuleId(modules, Number(moduleId) || defaultModuleId);
      if (fallbackModuleId && fallbackModuleId !== Number(moduleId)) {
        moduleId = fallbackModuleId;
      }
    }
  }
  $: if (open && questionType !== 'bundle') {
    qmlText = buildDerivedQmlText();
  }
  $: if (open && questionType === 'inline_cloze') {
    if (!qmlText.trim()) {
      qmlError = '';
    } else {
      try {
        const parsedState = parseEditorStateFromQml(qmlText);
        if (parsedState.questionType !== 'inline_cloze') {
          throw new QmlError('Inline cloze QML needs one or more bracketed answer groups.');
        }
        qmlError = '';
      } catch (error) {
        qmlError = error instanceof QmlError ? error.message : 'Invalid inline cloze QML.';
      }
    }
  }
</script>

{#if open}
  <div class="drawer-backdrop" role="presentation" on:click={onClose}>
    <div class="drawer-panel-shell" role="presentation" on:click|stopPropagation>
      <aside class="drawer-panel" aria-label="Question editor">
        <div class="panel-header sticky">
          <div>
            <h2>{mode === 'moderation' ? 'Approve Revision' : editingQuestion ? 'Revise Question' : 'Create Question'}</h2>
          </div>
          <button type="button" class="ghost-button" on:click={onClose}>Close</button>
        </div>

        {#if formError}
          <div class="banner error">{formError}</div>
        {/if}

        {#if mode === 'moderation'}
          <div class="banner info">Saving here approves the edited revision. Module placement and order stay locked.</div>
        {:else if isVerifiedNonAdminEdit}
          <div class="banner info">This is a personal revision proposal. Module placement and order stay global until an admin approves it.</div>
        {/if}

        {#if showWithdrawAction}
          <div class="banner info">This question is in Review because of your pending proposal. Remove it from review to discard the proposal and return the original question to quiz rotation.</div>
        {/if}

        {#if qmlError && (questionType === 'bundle' || questionType === 'inline_cloze' || !editingQuestion)}
          <div class="banner error">{qmlError}</div>
        {/if}

        <div class="editor-layout">
          <div class="editor-form">
            <div class="editor-card">
              <div class="editor-top-row">
                <label class="field editor-field-compact">
                  <span id="editor-module-label">Module</span>
                  <EditorModulePicker
                    bind:value={moduleId}
                    modules={modules}
                    disabled={moduleSelectionLocked}
                    selectedLabel={selectedModuleLabel}
                    labelId="editor-module-label"
                  />
                </label>

                <label class="field editor-field-compact">
                  <span>Question type</span>
                  <select
                    class="editor-compact-select"
                    bind:value={questionType}
                    on:change={(event) => setQuestionType((event.currentTarget as HTMLSelectElement).value as QuestionType)}
                  >
                    <option value="single_text">Single text</option>
                    <option value="multi_text">Multi text (any order)</option>
                    <option value="ordered_multi">Ordered multi</option>
                    <option value="inline_cloze">Inline cloze</option>
                    <option value="bundle">Bundle</option>
                  </select>
                </label>
              </div>

              {#if !selectedModuleIsLeaf}
                <p class="muted-copy editor-inline-note">Select a leaf module before saving this question.</p>
              {/if}

              {#if questionType !== 'bundle' && questionType !== 'inline_cloze'}
                <label class="field editor-field-compact editor-prompt-row">
                  <span>Prompt</span>
                  <textarea
                    rows="1"
                    class="editor-auto-field"
                    use:autoGrow={{ maxMode: 'wide', value: prompt }}
                    bind:value={prompt}
                    placeholder={promptPlaceholder(questionType, Boolean(editingQuestion))}
                  ></textarea>
                </label>
              {/if}

              {#if editingQuestion && isAdmin}
                <label class="checkbox-field dense-checkbox-field">
                  <input type="checkbox" bind:checked={resetStats} />
                  <span>Reset stats for this revision</span>
                </label>
              {/if}

              {#if questionType === 'bundle'}
                <BundleEditor
                  {bundleQml}
                  {bundleTemplate}
                  variants={bundleVariants}
                  isEditing={Boolean(editingQuestion)}
                  onQmlChange={handleBundleQmlInput}
                  onAddVariant={addBundleVariant}
                  onRemoveVariant={removeBundleVariant}
                  onPromptValueChange={updateBundlePromptValue}
                  onAnswersChange={updateBundleAnswers}
                />
              {:else if questionType === 'single_text'}
                <SingleTextEditor
                  {questionType}
                  answersText={singleAnswersText}
                  isEditing={Boolean(editingQuestion)}
                  onAnswersChange={updateSingleAnswers}
                />
              {:else if questionType === 'multi_text' || questionType === 'ordered_multi'}
                <MultiSlotEditor
                  {questionType}
                  slots={multiSlots}
                  isEditing={Boolean(editingQuestion)}
                  onAddSlot={addMultiSlot}
                  onRemoveSlot={removeMultiSlot}
                  onSlotChange={updateMultiSlotAnswers}
                />
              {:else}
                <InlineClozeEditor
                  {qmlText}
                  blanks={inlineBlanks}
                  isEditing={Boolean(editingQuestion)}
                  onQmlChange={handleInlineQmlInput}
                  onBlankChange={updateInlineBlankAnswers}
                />
              {/if}

              {#if !editingQuestion && (questionType === 'single_text' || questionType === 'multi_text' || questionType === 'ordered_multi')}
                <label class="field">
                  <span>QML</span>
                  <textarea
                    rows="1"
                    class="editor-auto-field"
                    use:autoGrow={{ maxMode: 'wide', value: qmlText }}
                    bind:value={qmlText}
                    on:input={(event) => handlePlainQmlInput((event.currentTarget as HTMLTextAreaElement).value)}
                  ></textarea>
                </label>
              {/if}
            </div>

            <div class="drawer-actions">
              {#if showWithdrawAction}
                <button
                  class="ghost-button"
                  type="button"
                  disabled={editorBusy}
                  on:click={() => void handleWithdrawRevision()}
                >
                  {withdrawActionLabel}
                </button>
              {/if}
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
                disabled={editorBusy || !!qmlError || !selectedModuleIsLeaf}
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
