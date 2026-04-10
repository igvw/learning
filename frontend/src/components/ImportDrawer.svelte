<script lang="ts">
  import type {
    ModuleNode,
    QuestionImportResult,
    QuestionImportRowPayload,
  } from '../lib/types';

  export let open = false;
  export let moduleNode: ModuleNode | null = null;
  export let result: QuestionImportResult | null = null;
  export let busy = false;
  export let errorMessage = '';
  export let onClose: () => void = () => {};
  export let onStartImport: (qmlText: string) => Promise<void> | void = () => {};
  export let onRevalidate: (rows: QuestionImportRowPayload[]) => Promise<void> | void = () => {};
  export let onCommit: (rows: QuestionImportRowPayload[]) => Promise<void> | void = () => {};

  let qmlText = '';
  let pendingRows: QuestionImportRowPayload[] = [];
  let rowDrafts: Record<number, string> = {};
  let localMarker = '';

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

  function parsePendingRows(value: string): QuestionImportRowPayload[] {
    return value
      .split(/\r?\n/)
      .map((qmlLine, index) => ({ row_number: index + 1, qml_line: qmlLine }))
      .filter((row) => row.qml_line.trim());
  }

  function updateQmlLine(rowNumber: number, value: string): void {
    rowDrafts = {
      ...rowDrafts,
      [rowNumber]: value
    };
    pendingRows = pendingRows.map((row) => (row.row_number === rowNumber ? { ...row, qml_line: value } : row));
  }

  async function handleStartValidate(): Promise<void> {
    pendingRows = parsePendingRows(qmlText);
    await onStartImport(qmlText);
  }

  async function handleDiscardRow(rowNumber: number): Promise<void> {
    pendingRows = pendingRows.filter((row) => row.row_number !== rowNumber);
    const nextDrafts = { ...rowDrafts };
    delete nextDrafts[rowNumber];
    rowDrafts = nextDrafts;
    await onRevalidate(pendingRows);
  }

  async function handleRevalidate(): Promise<void> {
    await onRevalidate(pendingRows);
  }

  function isEditableRelocationRow(row: QuestionImportResult['relocation_rows'][number]): boolean {
    return row.requires_edit || row.status === 'merge';
  }

  function currentRowValue(rowNumber: number, fallback: string): string {
    return rowDrafts[rowNumber] ?? fallback;
  }

  function sameRows(left: QuestionImportRowPayload[], right: QuestionImportRowPayload[]): boolean {
    if (left.length !== right.length) {
      return false;
    }
    return left.every((row, index) => row.row_number === right[index].row_number && row.qml_line === right[index].qml_line);
  }

  $: marker =
    `${open}:${result?.rows.map((row) => `${row.row_number}:${row.qml_line}`).join('|') ?? 'new'}:${result?.relocation_rows
      .map((row) => `${row.row_number}:${row.status}`)
      .join('|') ?? 'none'}`;
  $: if (marker !== localMarker && open) {
    localMarker = marker;
    if (!result) {
      qmlText = '';
      pendingRows = [];
      rowDrafts = {};
    } else if (pendingRows.length === 0) {
      pendingRows = [...result.rows].sort((left, right) => left.row_number - right.row_number);
    }
    rowDrafts = Object.fromEntries(
      [
        ...(result?.unresolved_rows ?? []),
        ...(result?.relocation_rows ?? [])
      ].map((row) => [row.row_number, row.qml_line])
    );
  }
  $: hasPendingEdits = Boolean(result && !sameRows(pendingRows, result.rows));
  $: showRevalidateButton =
    Boolean(result) &&
    (result.unresolved_rows.length > 0 || result.relocation_rows.some((row) => isEditableRelocationRow(row)) || hasPendingEdits);
</script>

{#if open}
  <div class="drawer-backdrop" role="presentation" on:click={onClose}>
    <div class="drawer-panel-shell" role="presentation" on:click|stopPropagation>
      <aside class="drawer-panel import-drawer" aria-label="Question import">
        <div class="panel-header sticky">
          <div>
            <p class="eyebrow">QML import</p>
            <h2>Import Questions</h2>
          </div>
          <button type="button" class="ghost-button" on:click={onClose}>Close</button>
        </div>

        {#if errorMessage}
          <div class="banner error">{errorMessage}</div>
        {/if}

        <div class="import-panel">
          <div class="import-summary panel">
            <p class="eyebrow">Target module</p>
            <h3>{moduleNode?.title ?? 'No module selected'}</h3>
            {#if moduleNode?.instruction}
              <p class="muted-copy">{moduleNode.instruction}</p>
            {/if}
            {#if !isLeaf(moduleNode)}
              <p class="muted-copy">Select a leaf module before importing questions.</p>
            {/if}
          </div>

          {#if !result}
            <div class="panel import-start">
              <div class="subsection-header">
                <h3>Import QML</h3>
                <label class="secondary-button file-trigger">
                  <input type="file" accept=".dsl,.txt,text/plain" on:change={handleFileChange} />
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
              <div class="subsection-header">
                <div>
                  <p class="eyebrow">Validation state</p>
                  <h3>{result.valid_row_count} valid rows</h3>
                </div>
                <div class="import-session-meta">
                  <span>{result.unresolved_rows.length} unresolved</span>
                  <span>{result.skipped_duplicate_count} skipped</span>
                </div>
              </div>

              {#if result.report_text}
                <label class="field">
                  <span>Validation report</span>
                  <textarea class="qml-report" rows="8" readonly value={result.report_text}></textarea>
                </label>
              {/if}

              {#if result.unresolved_rows.length > 0}
                <div class="field">
                  <span>Unresolved QML lines</span>
                  <div class="qml-editor">
                    {#each result.unresolved_rows as row (row.row_number)}
                      <div class="qml-editor-row">
                        <button
                          class="qml-line-number"
                          type="button"
                          aria-label={`Discard row ${row.row_number}`}
                          on:click={() => void handleDiscardRow(row.row_number)}
                        >
                          <span class="qml-line-index">{row.row_number}</span>
                          <span class="qml-line-delete">x</span>
                        </button>
                        <div class="qml-line-body">
                          <input
                            class="qml-line-input"
                            type="text"
                            value={currentRowValue(row.row_number, row.qml_line)}
                            on:input={(event) => updateQmlLine(row.row_number, (event.currentTarget as HTMLInputElement).value)}
                          />
                          <p class="qml-row-issues">{row.issues.join(' | ')}</p>
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {:else}
                <p class="muted-copy">No unresolved rows remain. Commit when you are ready.</p>
              {/if}

              {#if result.relocation_rows.length > 0}
                <div class="field relocation-field">
                  <span>Relocations and merge review</span>
                  <div class="relocation-list">
                    {#each result.relocation_rows as row (row.row_number)}
                      <section class="relocation-card">
                        <div class="relocation-header">
                          <div>
                            <p class="eyebrow">Row {row.row_number}</p>
                            <h4>{row.status === 'move' ? 'Pure move' : row.status === 'revise' ? 'Move and revise' : 'Merge duplicates'}</h4>
                          </div>
                          <span class={`relocation-badge status-${row.status}`}>
                            {row.status === 'move' ? 'Move' : row.status === 'revise' ? 'Revise' : 'Merge'}
                          </span>
                        </div>

                        <div class="relocation-columns">
                          <div class="relocation-column">
                            <p class="muted-copy">Existing question{row.matched_questions.length === 1 ? '' : 's'}</p>
                            {#each row.matched_questions as matched (matched.question_id)}
                              <article class="relocation-detail-card">
                                <p class="muted-copy"><code>{matched.module_full_slug}</code></p>
                                <code class="qml-line-preview">{matched.qml_line}</code>
                                <div class="answer-block-list">
                                  {#each matched.answer_blocks as block}
                                    <span class="answer-block-chip">{block}</span>
                                  {/each}
                                </div>
                              </article>
                            {/each}
                          </div>

                          <div class="relocation-column">
                            <p class="muted-copy">Imported / final target in <code>{row.target_module_full_slug}</code></p>
                            {#if isEditableRelocationRow(row)}
                              <input
                                class="qml-line-input"
                                type="text"
                                value={currentRowValue(row.row_number, row.qml_line)}
                                on:input={(event) => updateQmlLine(row.row_number, (event.currentTarget as HTMLInputElement).value)}
                              />
                            {:else}
                              <code class="qml-line-preview">{row.qml_line}</code>
                            {/if}
                            <div class="answer-block-list">
                              {#each row.imported_answer_blocks as block}
                                <span class="answer-block-chip new">{block}</span>
                              {/each}
                            </div>
                            {#if row.ready_without_edit}
                              <p class="muted-copy">Reported for visibility only. No edit is required.</p>
                            {:else if isEditableRelocationRow(row)}
                              <p class="muted-copy">Edit the final QML here if you want to refine the imported answer block before commit.</p>
                            {/if}
                          </div>
                        </div>
                      </section>
                    {/each}
                  </div>
                </div>
              {/if}

              <div class="drawer-actions">
                {#if showRevalidateButton}
                  <button class="secondary-button" type="button" disabled={busy} on:click={() => void handleRevalidate()}>
                    {busy ? 'Checking...' : 'Revalidate Rows'}
                  </button>
                {/if}
                <button class="primary-button" type="button" disabled={busy || !result.ready_to_commit || hasPendingEdits} on:click={() => void onCommit(pendingRows)}>
                  {busy ? 'Saving...' : 'Commit Import'}
                </button>
              </div>
            </div>
          {/if}
        </div>
      </aside>
    </div>
  </div>
{/if}
