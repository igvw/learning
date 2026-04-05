<script lang="ts">
  import { tick } from 'svelte';
  import type { QuizItem, QuizSession } from '../lib/types';

  export let session: QuizSession | null = null;
  export let moduleLabel = 'Selected Module';
  export let moduleInstruction = '';
  export let selectedModuleIsLeaf = false;
  export let busyItemId: number | null = null;
  export let markingReviewQuestionId: number | null = null;
  export let errorMessage = '';
  export let onStartQuiz: () => Promise<void> | void = () => {};
  export let onMarkForRevision: (questionId: number) => Promise<void> | void = () => {};
  export let onSubmit: (itemId: number, answers: string[]) => Promise<void> = async () => {};

  let draftAnswers: Record<number, string[]> = {};
  let sessionMarker: number | null = null;
  let focusMarker = '';
  let completionActionButton: HTMLButtonElement | null = null;

  function slotCount(item: QuizItem): number {
    if (item.question_type === 'single_text') {
      return 1;
    }
    if (item.question_type === 'multi_text' || item.question_type === 'ordered_multi') {
      return item.type_config.expected_slots ?? item.type_config.slot_prompts?.length ?? 0;
    }
    return Math.max((item.type_config.segments?.length ?? 1) - 1, 0);
  }

  function renderedInlinePrompt(item: QuizItem): string {
    return (item.type_config.segments ?? []).join('[_]');
  }

  function shouldShowPromptHeading(item: QuizItem): boolean {
    if (item.question_type !== 'inline_cloze') {
      return true;
    }
    return item.prompt.trim() !== renderedInlinePrompt(item).trim();
  }

  function itemScorePossible(item: QuizItem): number {
    return item.score_possible ?? slotCount(item);
  }

  function itemScoreEarned(item: QuizItem): number {
    return item.score_earned ?? 0;
  }

  function displaySlotTotal(item: QuizItem): number {
    return slotCount(item);
  }

  function displaySlotEarned(item: QuizItem): number {
    if (!item.slot_results) {
      return 0;
    }
    return item.slot_results.filter((result) => result.is_correct).length;
  }

  function formatScore(value: number): string {
    return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(/\.0$/, '');
  }

  function buildDrafts(currentSession: QuizSession | null): Record<number, string[]> {
    if (!currentSession) {
      return {};
    }
    const result: Record<number, string[]> = {};
    for (const item of currentSession.items) {
      const count = slotCount(item);
      result[item.id] = item.submitted_answer ? [...item.submitted_answer] : Array.from({ length: count }, () => '');
    }
    return result;
  }

  function ensureDraft(item: QuizItem): string[] {
    if (!draftAnswers[item.id]) {
      draftAnswers = {
        ...draftAnswers,
        [item.id]: Array.from({ length: slotCount(item) }, () => '')
      };
    }
    return draftAnswers[item.id];
  }

  function updateAnswer(itemId: number, index: number, value: string): void {
    const answers = [...(draftAnswers[itemId] ?? [])];
    answers[index] = value;
    draftAnswers = { ...draftAnswers, [itemId]: answers };
  }

  async function focusActiveInput(): Promise<void> {
    await tick();
    const nextInput = document.querySelector<HTMLInputElement>('[data-active-input="true"]');
    nextInput?.focus();
    nextInput?.select();
  }

  async function focusCompletionAction(): Promise<void> {
    await tick();
    completionActionButton?.focus();
  }

  function handleSubmit(item: QuizItem): void {
    const answers = ensureDraft(item).map((value) => value.trimEnd());
    void onSubmit(item.id, answers);
  }

  async function focusSlotInput(itemId: number, slotIndex: number): Promise<void> {
    await tick();
    const nextInput = document.querySelector<HTMLInputElement>(
      `[data-question-id="${itemId}"][data-slot-index="${slotIndex}"]`
    );
    nextInput?.focus();
    nextInput?.select();
  }

  function slotState(item: QuizItem, slotIndex: number): 'correct' | 'incorrect' | '' {
    if (!item.submitted_answer) {
      return '';
    }
    const slotResult = item.slot_results?.find((result) => result.index === slotIndex);
    if (slotResult) {
      return slotResult.is_correct ? 'correct' : 'incorrect';
    }
    if (item.is_correct === true) {
      return 'correct';
    }
    if (item.is_correct === false && slotCount(item) === 1) {
      return 'incorrect';
    }
    return '';
  }

  function handleKeydown(event: KeyboardEvent, item: QuizItem, slotIndex: number): void {
    if (busyItemId === item.id || item.submitted_answer) {
      return;
    }
    if (event.key !== 'Enter' || event.shiftKey) {
      return;
    }

    event.preventDefault();
    if (item.question_type === 'single_text') {
      handleSubmit(item);
      return;
    }

    const lastSlotIndex = slotCount(item) - 1;
    if (slotIndex < lastSlotIndex) {
      void focusSlotInput(item.id, slotIndex + 1);
      return;
    }

    if (slotIndex === lastSlotIndex) {
      handleSubmit(item);
    }
  }

  $: if (session?.id !== sessionMarker) {
    sessionMarker = session?.id ?? null;
    draftAnswers = buildDrafts(session);
  }

  $: activeIndex = session ? session.items.findIndex((item) => item.submitted_answer === null) : -1;
  $: revealAll = activeIndex === -1;
  $: completedSession = Boolean(session && session.items.length > 0 && revealAll);
  $: completedCount = session ? session.items.filter((item) => item.submitted_answer !== null).length : 0;
  $: totalScoreEarned = session ? session.items.reduce((total, item) => total + itemScoreEarned(item), 0) : 0;
  $: totalScorePossible = session ? session.items.reduce((total, item) => total + itemScorePossible(item), 0) : 0;
  $: focusKey = `${session?.id ?? 'none'}:${activeIndex}`;
  $: if (focusKey !== focusMarker && activeIndex >= 0) {
    focusMarker = focusKey;
    void focusActiveInput();
  }
  $: completionFocusKey = completedSession ? `${session?.id ?? 'none'}:${completedCount}` : '';
  $: if (completionFocusKey && completionFocusKey !== focusMarker) {
    focusMarker = completionFocusKey;
    void focusCompletionAction();
  }
</script>

<section class="page quiz-page">
  <div class="page-intro">
    <div>
      <p class="eyebrow">Current module scope</p>
      <h2>{moduleLabel}</h2>
    </div>
    {#if !completedSession}
      <button class="primary-button" type="button" on:click={() => void onStartQuiz()}>
        Start Quiz
      </button>
    {/if}
  </div>

  {#if selectedModuleIsLeaf && moduleInstruction}
    <div class="panel instruction-panel">
      <p class="eyebrow">Instruction</p>
      <p>{moduleInstruction}</p>
    </div>
  {/if}

  {#if errorMessage}
    <div class="banner error">{errorMessage}</div>
  {/if}

  {#if !session}
    <div class="panel empty-state">
      <h3>Short bursts, no mouse required.</h3>
      <p>Start a ten-question quiz for the selected scope. Submitted cards stay on screen so the finished session becomes the review surface.</p>
      <p class="shortcut-hint">Press <kbd>Enter</kbd> to move through fields. On the last field, <kbd>Enter</kbd> submits the question.</p>
    </div>
  {:else if session.items.length === 0}
    <div class="panel empty-state">
      <h3>No questions in this scope yet.</h3>
      <p>Switch modules from the menu or create questions from the stats page.</p>
    </div>
  {:else}
    <div class="quiz-stack">
      {#each session.items as item, index (item.id)}
        {#if revealAll || index <= activeIndex}
          {@const answered = item.submitted_answer !== null}
          {@const currentAnswers = ensureDraft(item)}
          <article class="panel quiz-card" class:correct={item.is_correct === true} class:incorrect={item.is_correct === false}>
            <div class="quiz-card-header">
              <div class="quiz-card-header-left">
                <span class="question-pill">Question {index + 1}</span>
                {#if answered && displaySlotTotal(item) > 1}
                  <span class="question-pill score-pill">{displaySlotEarned(item)}/{displaySlotTotal(item)}</span>
                {/if}
              </div>
              {#if revealAll && answered}
                <button
                  class="ghost-button flag-button"
                  class:flagged={item.review_flag}
                  class:loading={markingReviewQuestionId === item.question_id}
                  type="button"
                  aria-label={
                    item.review_flag
                      ? 'Marked for revision'
                      : markingReviewQuestionId === item.question_id
                        ? 'Flagging revision'
                        : 'Flag for revision'
                  }
                  disabled={item.review_flag || markingReviewQuestionId === item.question_id}
                  on:click={() => void onMarkForRevision(item.question_id)}
                >
                  <svg class="flag-icon" viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M4 2v12" />
                    <path d="M5 2h7l-2 3 2 3H5z" />
                  </svg>
                </button>
              {/if}
            </div>

            <div class="quiz-card-body">
              {#if !selectedModuleIsLeaf && item.module_instruction}
                <p class="eyebrow quiz-item-instruction">{item.module_instruction}</p>
              {/if}

              {#if shouldShowPromptHeading(item)}
                <h3>{item.prompt}</h3>
              {/if}

              {#if item.question_type === 'single_text'}
                <input
                  type="text"
                  class="answer-input"
                  class:answer-correct={slotState(item, 0) === 'correct'}
                  class:answer-incorrect={slotState(item, 0) === 'incorrect'}
                  value={currentAnswers[0] ?? ''}
                  disabled={answered || busyItemId === item.id}
                  data-active-input={!answered && activeIndex === index ? 'true' : undefined}
                  data-question-id={item.id}
                  data-slot-index={0}
                  on:input={(event) => updateAnswer(item.id, 0, (event.currentTarget as HTMLInputElement).value)}
                  on:keydown={(event) => handleKeydown(event, item, 0)}
                />
              {:else if item.question_type === 'multi_text' || item.question_type === 'ordered_multi'}
                <div class="multi-slot-list">
                  {#each Array.from({ length: slotCount(item) }) as _, slotIndex}
                    <div class="slot-field">
                      <input
                        type="text"
                        class="answer-input"
                        class:answer-correct={slotState(item, slotIndex) === 'correct'}
                        class:answer-incorrect={slotState(item, slotIndex) === 'incorrect'}
                        aria-label={`Answer ${slotIndex + 1}`}
                        value={currentAnswers[slotIndex] ?? ''}
                        disabled={answered || busyItemId === item.id}
                        data-active-input={!answered && activeIndex === index && slotIndex === 0 ? 'true' : undefined}
                        data-question-id={item.id}
                        data-slot-index={slotIndex}
                        on:input={(event) => updateAnswer(item.id, slotIndex, (event.currentTarget as HTMLInputElement).value)}
                        on:keydown={(event) => handleKeydown(event, item, slotIndex)}
                      />
                    </div>
                  {/each}
                </div>
              {:else}
                <div class="inline-cloze">
                  {#each item.type_config.segments ?? [] as segment, segmentIndex}
                    <span class="cloze-segment">{segment}</span>
                    {#if segmentIndex < slotCount(item)}
                      <input
                        type="text"
                        class="answer-input inline"
                        class:answer-correct={slotState(item, segmentIndex) === 'correct'}
                        class:answer-incorrect={slotState(item, segmentIndex) === 'incorrect'}
                        value={currentAnswers[segmentIndex] ?? ''}
                        disabled={answered || busyItemId === item.id}
                        data-active-input={!answered && activeIndex === index && segmentIndex === 0 ? 'true' : undefined}
                        data-question-id={item.id}
                        data-slot-index={segmentIndex}
                        on:input={(event) => updateAnswer(item.id, segmentIndex, (event.currentTarget as HTMLInputElement).value)}
                        on:keydown={(event) => handleKeydown(event, item, segmentIndex)}
                      />
                    {/if}
                  {/each}
                </div>
              {/if}

              {#if !answered}
                <div class="quiz-card-actions">
                  <button
                    class="primary-button"
                    type="button"
                    disabled={busyItemId === item.id}
                    on:click={() => handleSubmit(item)}
                  >
                    {busyItemId === item.id ? 'Submitting...' : 'Submit'}
                  </button>
                </div>
              {/if}

              {#if answered && item.is_correct !== true}
                <div class="feedback-block">
                  {#if item.canonical_answers}
                    {#if item.question_type === 'single_text' && item.canonical_answers.length === 1}
                      <div class="answer-box plain-answer-box">
                        <p>{item.canonical_answers[0]}</p>
                      </div>
                    {:else}
                      <div class="answer-box">
                        <ul>
                          {#each item.canonical_answers as answer}
                            <li>{answer}</li>
                          {/each}
                        </ul>
                      </div>
                    {/if}
                  {/if}
                </div>
              {/if}
            </div>
          </article>
        {/if}
      {/each}
    </div>

    {#if completedSession}
      <div class="panel completion-panel">
        <p class="eyebrow">Session complete</p>
        <h3>{formatScore(totalScoreEarned)}/{formatScore(totalScorePossible)} points</h3>
        <p>{completedCount} submissions recorded. Mark any questions above for revision or start another quiz.</p>
        <div class="completion-actions">
          <button
            bind:this={completionActionButton}
            class="primary-button"
            type="button"
            on:click={() => void onStartQuiz()}
          >
            Start Another Quiz
          </button>
        </div>
      </div>
    {/if}
  {/if}
</section>
