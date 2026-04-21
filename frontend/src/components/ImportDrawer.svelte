<script lang="ts">
  import {
    answerChoiceSourceClass,
    answerChoiceSourceLabel,
    answerChoicesByBlock,
    answerSelectedInQmlLine,
    effectiveImportRowsFromResult,
    parsePendingImportRows,
    reviewRowsForPendingRows,
    toggleAnswerInQmlLine,
    type AnswerChoice
  } from '../lib/import-review';
  import { cloneImportRows, currentImportRowValue } from '../lib/import-rows';
  import type { ModuleNode, QuestionImportResult, QuestionImportReviewRow, QuestionImportRowPayload } from '../lib/types';

  export let open = false;
  export let moduleNode: ModuleNode | null = null;
  export let result: QuestionImportResult | null = null;
  export let busy = false;
  export let errorMessage = '';
  export let draftText = '';
  export let draftRows: QuestionImportRowPayload[] = [];
  export let saveStatusMessageOverride = '';
  export let saveStatusToneOverride: 'error' | 'info' | '' = '';
  export let saveProgressTotal = 0;
  export let saveProgressCompleted = 0;
  export let onClose: () => void = () => {};
  export let onDraftChange: (qmlText: string, rows: QuestionImportRowPayload[]) => void = () => {};
  export let onStartImport: (qmlText: string) => Promise<void> | void = () => {};
  export let onCommit: (rows: QuestionImportRowPayload[]) => Promise<void> | void = () => {};

  let qmlText = '';
  let pendingRows: QuestionImportRowPayload[] = [];
  let localMarker = '';
  let publishMarker = '';
  let saveAttempted = false;

  function requestClose(): void {
    if (busy) {
      return;
    }
    onClose();
  }

  function isLeaf(node: ModuleNode | null): boolean {
    return Boolean(node && node.children.length === 0);
  }

  async function handleFileChange(event: Event): Promise<void> {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    qmlText = await file.text();
    input.value = '';
  }

  function updateQmlLine(rowNumber: number, value: string): void {
    saveAttempted = false;
    pendingRows = pendingRows.map((row) => (row.row_number === rowNumber ? { ...row, qml_line: value } : row));
  }

  async function handleStartValidate(): Promise<void> {
    saveAttempted = false;
    pendingRows = parsePendingImportRows(qmlText);
    await onStartImport(qmlText);
  }

  async function handleDiscardRow(rowNumber: number): Promise<void> {
    saveAttempted = false;
    pendingRows = pendingRows.filter((row) => row.row_number !== rowNumber);
  }

  async function handleSave(): Promise<void> {
    saveAttempted = true;
    await onCommit(pendingRows);
  }

  function currentRowValue(rowNumber: number, fallback: string): string {
    return currentImportRowValue(pendingRows, rowNumber, fallback);
  }

  function answerSelected(row: QuestionImportReviewRow, choice: AnswerChoice): boolean {
    return answerSelectedInQmlLine(currentRowValue(row.row_number, row.qml_line), choice.blockIndex, choice.text);
  }

  function handleToggleAnswer(row: QuestionImportReviewRow, choice: AnswerChoice): void {
    if (!row.editable || busy) {
      return;
    }
    updateQmlLine(
      row.row_number,
      toggleAnswerInQmlLine(currentRowValue(row.row_number, row.qml_line), choice.blockIndex, choice.text)
    );
  }

  $: marker =
    result
      ? `${open}:${moduleNode?.id ?? 'none'}:${result.rows.map((row) => `${row.row_number}:${row.qml_line}`).join('|')}:${result.review_rows
          .map((row) => `${row.row_number}:${row.status}:${row.qml_line}`)
          .join('|')}:${result.valid_row_count}:${result.exact_duplicate_count}`
      : `${open}:${moduleNode?.id ?? 'none'}:${draftText}:${draftRows.map((row) => `${row.row_number}:${row.qml_line}`).join('|')}`;
  $: if (marker !== localMarker && open) {
    localMarker = marker;
    if (!result) {
      qmlText = draftText;
      pendingRows = cloneImportRows(draftRows).sort((left, right) => left.row_number - right.row_number);
      if (!draftText.trim() && draftRows.length === 0) {
        saveAttempted = false;
      }
    } else {
      qmlText = draftText;
      pendingRows =
        draftRows.length > 0
          ? cloneImportRows(draftRows).sort((left, right) => left.row_number - right.row_number)
          : effectiveImportRowsFromResult(result);
    }
  } else if (!open && localMarker) {
    localMarker = '';
    publishMarker = '';
    qmlText = '';
    pendingRows = [];
    saveAttempted = false;
  }
  $: displayReviewRows = reviewRowsForPendingRows(result, pendingRows);
  $: draftStateMarker = `${open}:${qmlText}:${pendingRows.map((row) => `${row.row_number}:${row.qml_line}`).join('|')}`;
  $: if (open && draftStateMarker !== publishMarker) {
    publishMarker = draftStateMarker;
    onDraftChange(
      qmlText,
      pendingRows.map((row) => ({
        row_number: row.row_number,
        qml_line: row.qml_line
      }))
    );
  }
  $: saveStatusMessage = (() => {
    if (saveStatusMessageOverride) {
      return saveStatusMessageOverride;
    }
    if (!saveAttempted || errorMessage || !result) {
      return '';
    }
    if (displayReviewRows.some((row) => row.blocking)) {
      return 'Fix the highlighted rows before saving.';
    }
    if (result.valid_row_count === 0 && result.exact_duplicate_count > 0 && displayReviewRows.length === 0) {
      return 'Nothing new to save.';
    }
    if (result.valid_row_count === 0) {
      return 'No importable rows remain.';
    }
    return '';
  })();
  $: saveStatusTone = (() => {
    if (saveStatusMessageOverride) {
      return saveStatusToneOverride;
    }
    return saveStatusMessage === 'Nothing new to save.' ? 'info' : saveStatusMessage ? 'error' : '';
  })();
  $: saveProgressRatio = saveProgressTotal > 0 ? Math.min(1, saveProgressCompleted / saveProgressTotal) : 0;
  $: saveButtonLabel = busy && saveProgressTotal > 0 ? `Saving ${saveProgressCompleted}/${saveProgressTotal}` : busy ? 'Saving...' : 'Save';
</script>

{#if open}
  <div class="drawer-backdrop" role="presentation" on:click={requestClose}>
    <div class="drawer-panel-shell import-drawer-shell" role="presentation" on:click|stopPropagation>
      <aside class="drawer-panel import-drawer" aria-label="Question import">
        <div class="panel-header sticky">
          <div>
            <p class="eyebrow">QML import</p>
            <h2>Import Questions</h2>
          </div>
          <button type="button" class="ghost-button" disabled={busy} on:click={requestClose}>Close</button>
        </div>

        {#if errorMessage}
          <div class="banner error">{errorMessage}</div>
        {/if}

        <div class="import-panel">
          <div class="import-summary panel">
            <div class="import-summary-head">
              <p class="eyebrow">Target module</p>
              <h3>{moduleNode?.title ?? 'No module selected'}</h3>
              {#if moduleNode?.full_slug}
                <p class="module-path"><code>{moduleNode.full_slug}</code></p>
              {/if}
              {#if moduleNode && !moduleNode.admin_verified}
                <p class="muted-copy import-summary-note">Pending module</p>
              {/if}
            </div>
            {#if moduleNode?.instruction}
              <p class="muted-copy import-summary-copy">{moduleNode.instruction}</p>
            {/if}
            {#if !isLeaf(moduleNode)}
              <p class="muted-copy import-summary-note">Select a leaf module before importing questions.</p>
            {/if}
          </div>

          {#if !result}
            <div class="panel import-start">
              <div class="subsection-header">
                <h3>Import QML</h3>
                <label class="secondary-button file-trigger">
                  <input type="file" accept=".qml,.dsl,.txt,text/plain" on:change={handleFileChange} />
                  Choose file
                </label>
              </div>
              <label class="field">
                <span>QML text</span>
                <textarea
                  class="qml-textarea"
                  rows="12"
                  bind:value={qmlText}
                  placeholder={'Which river runs through Cairo? [nile | the nile]\n\nName the two rivers that meet in Khartoum. {white nile, blue nile}'}
                ></textarea>
              </label>
              <div class="drawer-actions">
                <button
                  class="primary-button"
                  type="button"
                  disabled={busy || !isLeaf(moduleNode) || !qmlText.trim()}
                  on:click={() => void handleStartValidate()}
                >
                  {busy ? 'Validating...' : 'Start Import'}
                </button>
              </div>
            </div>
          {:else}
            <div class="panel import-session-panel">
              <div class="subsection-header import-review-header">
                <div>
                  <p class="eyebrow">Import summary</p>
                  <h3>{result.valid_row_count} rows ready</h3>
                </div>
                <div class="import-session-meta">
                  <span>{displayReviewRows.length} review rows</span>
                  <span>{result.exact_duplicate_count} exact duplicates omitted</span>
                </div>
              </div>

              {#if displayReviewRows.length > 0}
                <div class="field">
                  <span>Review rows</span>
                  <div class="table-shell import-review-shell">
                    <table class="dense-table import-review-table">
                      <colgroup>
                        <col class="import-review-col-line" />
                        <col class="import-review-col-qml" />
                        <col class="import-review-col-answers" />
                      </colgroup>
                      <thead>
                        <tr>
                          <th>Line</th>
                          <th>QML</th>
                          <th>Answers</th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each displayReviewRows as row (row.row_number)}
                          {@const blockChoicesList = answerChoicesByBlock(row, currentRowValue(row.row_number, row.qml_line))}
                          <tr class:review-row-blocking={row.blocking}>
                            <td>
                              <div
                                class={`import-review-line status-${row.status}`}
                                title={row.status_text}
                                aria-label={row.status_text}
                              >
                                {row.row_number}
                              </div>
                            </td>
                            <td>
                              <div class="import-review-cell import-review-qml-cell">
                                <div class="import-review-qml-field">
                                  {#if row.editable}
                                    <input
                                      class="qml-line-input"
                                      type="text"
                                      value={currentRowValue(row.row_number, row.qml_line)}
                                      disabled={busy}
                                      on:input={(event) => updateQmlLine(row.row_number, (event.currentTarget as HTMLInputElement).value)}
                                    />
                                  {:else}
                                    <code class="qml-line-preview qml-line-preview-compact">{row.qml_line}</code>
                                  {/if}
                                </div>
                                <button
                                  class="import-remove-button"
                                  type="button"
                                  disabled={busy}
                                  aria-label={`Remove row ${row.row_number}`}
                                  on:click={() => void handleDiscardRow(row.row_number)}
                                >
                                  ×
                                </button>
                              </div>
                            </td>
                            <td>
                              <div class="import-review-cell">
                                {#if blockChoicesList.length > 0}
                                  <div class="answer-block-stack">
                                    {#each blockChoicesList as blockChoices, blockIndex}
                                      <div class="answer-block-group">
                                        {#if blockChoicesList.length > 1}
                                          <p class="answer-block-label">Answer {blockIndex + 1}</p>
                                        {/if}
                                        {#if blockChoices.length > 0}
                                          <div class="answer-chip-row">
                                            {#each blockChoices as choice (choice.key)}
                                              <button
                                                class={`answer-block-chip answer-choice-button ${answerChoiceSourceClass(choice)}`}
                                                class:selected-answer-choice={answerSelected(row, choice)}
                                                type="button"
                                                disabled={!row.editable || busy}
                                                title={answerChoiceSourceLabel(choice)}
                                                aria-label={`Toggle ${answerChoiceSourceLabel(choice).toLowerCase()} ${choice.text} in QML row ${row.row_number}`}
                                                on:click={() => handleToggleAnswer(row, choice)}
                                              >
                                                {choice.text}
                                              </button>
                                            {/each}
                                          </div>
                                        {:else}
                                          <p class="muted-copy">No answers for this field yet.</p>
                                        {/if}
                                      </div>
                                    {/each}
                                  </div>
                                {:else}
                                  <p class="muted-copy">No answers parsed yet.</p>
                                {/if}
                              </div>
                            </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                </div>
              {:else}
                <p class="muted-copy">No review rows remain. Save when you are ready.</p>
              {/if}

              <div class="drawer-actions">
                {#if saveStatusMessage}
                  <p class={`import-save-status ${saveStatusTone}`}>{saveStatusMessage}</p>
                {/if}
                <button
                  class="primary-button"
                  class:button-with-progress={busy}
                  type="button"
                  disabled={busy || !isLeaf(moduleNode) || pendingRows.length === 0}
                  on:click={() => void handleSave()}
                >
                  {#if busy}
                    <span class="button-progress-ring" style={`--progress-ratio: ${saveProgressRatio};`} aria-hidden="true"></span>
                  {/if}
                  {saveButtonLabel}
                </button>
              </div>
            </div>
          {/if}
        </div>
      </aside>
    </div>
  </div>
{/if}
