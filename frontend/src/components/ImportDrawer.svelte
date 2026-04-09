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
  let unresolvedDrafts: Record<number, string> = {};
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
    unresolvedDrafts = {
      ...unresolvedDrafts,
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
    const nextDrafts = { ...unresolvedDrafts };
    delete nextDrafts[rowNumber];
    unresolvedDrafts = nextDrafts;
    await onRevalidate(pendingRows);
  }

  async function handleRevalidate(): Promise<void> {
    await onRevalidate(pendingRows);
  }

  $: marker = `${open}:${result?.unresolved_rows.map((row) => `${row.row_number}:${row.qml_line}`).join('|') ?? 'new'}`;
  $: if (marker !== localMarker && open) {
    localMarker = marker;
    unresolvedDrafts = Object.fromEntries((result?.unresolved_rows ?? []).map((row) => [row.row_number, row.qml_line]));
    if (!result) {
      qmlText = '';
      pendingRows = [];
    } else if (pendingRows.length === 0) {
      pendingRows = [
        ...result.skipped_rows.map((row) => ({
          row_number: row.row_number,
          qml_line: row.qml_line
        })),
        ...result.unresolved_rows.map((row) => ({
          row_number: row.row_number,
          qml_line: row.qml_line
        }))
      ].sort((left, right) => left.row_number - right.row_number);
    }
  }
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
                            value={unresolvedDrafts[row.row_number] ?? row.qml_line}
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

              <div class="drawer-actions">
                {#if result.unresolved_rows.length > 0}
                  <button class="secondary-button" type="button" disabled={busy} on:click={() => void handleRevalidate()}>
                    {busy ? 'Checking...' : 'Revalidate Rows'}
                  </button>
                {/if}
                <button class="primary-button" type="button" disabled={busy || !result.ready_to_commit} on:click={() => void onCommit(pendingRows)}>
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
