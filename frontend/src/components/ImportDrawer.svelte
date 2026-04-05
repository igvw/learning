<script lang="ts">
  import type {
    ModuleNode,
    QuestionImportRowPayload,
    QuestionImportSession
  } from '../lib/types';

  export let open = false;
  export let moduleNode: ModuleNode | null = null;
  export let session: QuestionImportSession | null = null;
  export let busy = false;
  export let errorMessage = '';
  export let onClose: () => void = () => {};
  export let onStartImport: (csvText: string) => Promise<void> | void = () => {};
  export let onRevalidate: (rows: QuestionImportRowPayload[]) => Promise<void> | void = () => {};
  export let onDiscardRow: (rowNumber: number) => Promise<void> | void = () => {};
  export let onCommit: () => Promise<void> | void = () => {};

  let csvText = '';
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
    csvText = await file.text();
    input.value = '';
  }

  function buildRevalidatePayload(): QuestionImportRowPayload[] {
    if (!session) {
      return [];
    }
    return session.unresolved_rows.map((row) => ({
      row_number: row.row_number,
      csv_line: unresolvedDrafts[row.row_number] ?? row.csv_line
    }));
  }

  function updateCsvLine(rowNumber: number, value: string): void {
    unresolvedDrafts = {
      ...unresolvedDrafts,
      [rowNumber]: value
    };
  }

  async function handleRevalidate(): Promise<void> {
    await onRevalidate(buildRevalidatePayload());
  }

  $: marker = `${open}:${session?.session_id ?? 'new'}:${session?.unresolved_rows.map((row) => `${row.row_number}:${row.csv_line}`).join('|') ?? ''}`;
  $: if (marker !== localMarker && open) {
    localMarker = marker;
    unresolvedDrafts = Object.fromEntries((session?.unresolved_rows ?? []).map((row) => [row.row_number, row.csv_line]));
    if (!session) {
      csvText = '';
    }
  }
</script>

{#if open}
  <div class="drawer-backdrop" role="presentation" on:click={onClose}>
    <div class="drawer-panel-shell" role="presentation" on:click|stopPropagation>
      <aside class="drawer-panel import-drawer" aria-label="Question import">
        <div class="panel-header sticky">
          <div>
            <p class="eyebrow">CSV upload</p>
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

          {#if !session}
            <div class="panel import-start">
              <div class="subsection-header">
                <h3>Upload CSV</h3>
                <label class="secondary-button file-trigger">
                  <input type="file" accept=".csv,text/csv" on:change={handleFileChange} />
                  Choose file
                </label>
              </div>
              <label class="field">
                <span>CSV text</span>
                <textarea
                  class="csv-textarea"
                  rows="12"
                  bind:value={csvText}
                  placeholder={'prompt,answers\nWhich river runs through Cairo?,nile | the nile'}
                ></textarea>
              </label>
              <div class="drawer-actions">
                <button
                  class="primary-button"
                  type="button"
                  disabled={busy || !isLeaf(moduleNode) || !csvText.trim()}
                  on:click={() => void onStartImport(csvText)}
                >
                  {busy ? 'Validating...' : 'Start Import'}
                </button>
              </div>
            </div>
          {:else}
            <div class="panel import-session-panel">
              <div class="subsection-header">
                <div>
                  <p class="eyebrow">Session state</p>
                  <h3>{session.staged_valid_count} staged rows</h3>
                </div>
                <div class="import-session-meta">
                  <span>{session.unresolved_rows.length} unresolved</span>
                  <span>Expires {new Date(session.expires_at).toLocaleString()}</span>
                </div>
              </div>

              {#if session.report_text}
                <label class="field">
                  <span>Validation report</span>
                  <textarea class="csv-report" rows="8" readonly value={session.report_text}></textarea>
                </label>
              {/if}

              {#if session.unresolved_rows.length > 0}
                <div class="field">
                  <span>Unresolved CSV rows</span>
                  <div class="csv-editor">
                    <div class="csv-editor-row csv-editor-header">
                      <span class="csv-line-number header-cell"></span>
                      <div class="csv-line-input csv-header-text">prompt,answers</div>
                    </div>
                    {#each session.unresolved_rows as row (row.row_number)}
                      <div class="csv-editor-row">
                        <button
                          class="csv-line-number"
                          type="button"
                          aria-label={`Discard row ${row.row_number}`}
                          on:click={() => void onDiscardRow(row.row_number)}
                        >
                          <span class="csv-line-index">{row.row_number}</span>
                          <span class="csv-line-delete">x</span>
                        </button>
                        <div class="csv-line-body">
                          <input
                            class="csv-line-input"
                            type="text"
                            value={unresolvedDrafts[row.row_number] ?? row.csv_line}
                            on:input={(event) => updateCsvLine(row.row_number, (event.currentTarget as HTMLInputElement).value)}
                          />
                          <p class="csv-row-issues">{row.issues.join(' | ')}</p>
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {:else}
                <p class="muted-copy">No unresolved rows remain. Commit when you are ready.</p>
              {/if}

              <div class="drawer-actions">
                {#if session.unresolved_rows.length > 0}
                  <button class="secondary-button" type="button" disabled={busy} on:click={() => void handleRevalidate()}>
                    {busy ? 'Checking...' : 'Revalidate Rows'}
                  </button>
                {/if}
                <button class="primary-button" type="button" disabled={busy || !session.ready_to_commit} on:click={() => void onCommit()}>
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
